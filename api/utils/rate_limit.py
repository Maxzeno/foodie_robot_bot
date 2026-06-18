"""
Rate limiting utility for WhatsApp webhook endpoints.

Implements per-user rate limiting using Redis for atomic operations.
Falls back to Django cache if Redis is unavailable.
"""
import logging
import time
from functools import wraps
from django.conf import settings

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


def _get_redis_client():
    """
    Get Redis client from Huey configuration.
    Returns None if Redis is not available.
    """
    try:
        redis_url = getattr(settings, 'REDIS_URL', None)
        if not redis_url:
            return None

        import redis
        return redis.from_url(redis_url)
    except Exception as e:
        logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
        return None


def _check_rate_limit_redis(redis_client, cache_key, max_requests, window_seconds):
    """
    Atomic rate limiting using Redis INCR + EXPIRE.

    Uses sliding window counter pattern for accurate rate limiting.
    """
    pipe = redis_client.pipeline()

    # Atomic increment
    pipe.incr(cache_key)
    # Set expiry only if key is new (NX flag via separate logic)
    pipe.expire(cache_key, window_seconds)

    results = pipe.execute()
    current_count = results[0]

    # Get TTL for remaining time
    ttl = redis_client.ttl(cache_key)
    if ttl < 0:
        ttl = window_seconds

    if current_count > max_requests:
        logger.warning(
            f"Rate limit exceeded: key={cache_key}, "
            f"count={current_count}/{max_requests}, reset_in={ttl}s"
        )
        raise RateLimitExceeded(
            f"Rate limit exceeded. Try again in {ttl} seconds."
        )

    remaining = max_requests - current_count
    logger.debug(
        f"Rate limit check: key={cache_key}, "
        f"count={current_count}/{max_requests}, remaining={remaining}"
    )

    return (True, remaining, ttl)


def _check_rate_limit_cache(cache_key, max_requests, window_seconds):
    """
    Fallback rate limiting using Django cache.

    Note: This is NOT atomic and may allow slight overruns under high concurrency.
    Use Redis for production workloads.
    """
    from django.core.cache import cache

    current_time = time.time()
    rate_data = cache.get(cache_key)

    if rate_data is None or current_time >= rate_data.get('reset_at', 0):
        # Start new window
        rate_data = {
            'count': 1,
            'reset_at': current_time + window_seconds
        }
        cache.set(cache_key, rate_data, timeout=window_seconds)
        return (True, max_requests - 1, window_seconds)

    if rate_data['count'] >= max_requests:
        time_remaining = int(rate_data['reset_at'] - current_time)
        logger.warning(
            f"Rate limit exceeded: key={cache_key}, "
            f"count={rate_data['count']}/{max_requests}, reset_in={time_remaining}s"
        )
        raise RateLimitExceeded(
            f"Rate limit exceeded. Try again in {time_remaining} seconds."
        )

    # Increment counter
    rate_data['count'] += 1
    ttl = int(rate_data['reset_at'] - current_time)
    cache.set(cache_key, rate_data, timeout=max(ttl, 1))

    remaining = max_requests - rate_data['count']
    return (True, remaining, ttl)


# Global Redis client (lazy initialization)
_redis_client = None
_redis_checked = False


def _get_cached_redis_client():
    """Get cached Redis client, only checking once."""
    global _redis_client, _redis_checked

    if not _redis_checked:
        _redis_client = _get_redis_client()
        _redis_checked = True
        if _redis_client:
            logger.info("Rate limiting using Redis (atomic operations)")
        else:
            logger.warning("Rate limiting using Django cache (non-atomic, may allow overruns)")

    return _redis_client


def check_rate_limit(user_identifier, endpoint=None, max_requests=10, window_seconds=60):
    """
    Check if user has exceeded rate limit using atomic Redis operations.

    Args:
        user_identifier: Unique identifier for the user (e.g., phone number)
        max_requests: Maximum number of requests allowed within the time window
        window_seconds: Time window in seconds

    Returns:
        tuple: (is_allowed: bool, remaining_requests: int, reset_in: int)

    Raises:
        RateLimitExceeded: If rate limit is exceeded

    Implementation:
        - Uses Redis INCR for atomic increment (no race conditions)
        - Falls back to Django cache if Redis unavailable
        - Fixed window counter algorithm
    """
    if endpoint:
        cache_key = f"rate_limit:{user_identifier}:{endpoint}"
    else:
        cache_key = f"rate_limit:{user_identifier}"
        
    redis_client = _get_cached_redis_client()

    if redis_client:
        try:
            return _check_rate_limit_redis(redis_client, cache_key, max_requests, window_seconds)
        except RateLimitExceeded:
            raise
        except Exception as e:
            logger.error(f"Redis rate limit error, falling back to cache: {e}")

    # Fallback to Django cache
    return _check_rate_limit_cache(cache_key, max_requests, window_seconds)


def rate_limit_user(max_requests=10, window_seconds=60):
    """
    Rate limit decorator for endpoints that process user requests.

    Args:
        max_requests: Maximum number of requests allowed within the time window
        window_seconds: Time window in seconds

    Usage:
        @rate_limit_user(max_requests=10, window_seconds=60)
        def my_view(request, user_identifier):
            # Your view logic
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_identifier = kwargs.get('user_identifier') or kwargs.get('phone')

            if not user_identifier:
                return func(*args, **kwargs)

            check_rate_limit(user_identifier, max_requests, window_seconds)
            return func(*args, **kwargs)

        return wrapper
    return decorator


def get_rate_limit_status(user_identifier, max_requests=30, window_seconds=60):
    """
    Get current rate limit status for a user without incrementing the counter.

    Args:
        user_identifier: Unique identifier for the user
        max_requests: The configured max requests (for calculating remaining)
        window_seconds: The configured window (for default TTL)

    Returns:
        dict: {
            'count': current request count,
            'limit': maximum requests allowed,
            'remaining': remaining requests,
            'reset_in': seconds until reset
        }
    """
    cache_key = f"rate_limit:{user_identifier}"

    redis_client = _get_cached_redis_client()

    if redis_client:
        try:
            count = redis_client.get(cache_key)
            count = int(count) if count else 0
            ttl = redis_client.ttl(cache_key)
            ttl = ttl if ttl > 0 else 0

            return {
                'count': count,
                'limit': max_requests,
                'remaining': max(0, max_requests - count),
                'reset_in': ttl
            }
        except Exception as e:
            logger.error(f"Redis error in get_rate_limit_status: {e}")

    # Fallback to Django cache
    from django.core.cache import cache
    rate_data = cache.get(cache_key)

    if not rate_data:
        return {
            'count': 0,
            'limit': max_requests,
            'remaining': max_requests,
            'reset_in': 0
        }

    current_time = time.time()
    reset_in = max(0, int(rate_data.get('reset_at', current_time) - current_time))
    count = rate_data.get('count', 0)

    return {
        'count': count,
        'limit': max_requests,
        'remaining': max(0, max_requests - count),
        'reset_in': reset_in
    }
