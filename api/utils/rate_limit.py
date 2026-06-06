"""
Rate limiting utility for WhatsApp webhook endpoints.

Implements per-user rate limiting to prevent spam and abuse.
"""
from django.core.cache import cache
from django.http import HttpResponse
from functools import wraps
import time


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass


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

    The decorated function should accept a user_identifier parameter (e.g., phone number).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user identifier from kwargs or args
            # Expect it to be passed as 'user_identifier' or 'phone'
            user_identifier = kwargs.get('user_identifier') or kwargs.get('phone')

            if not user_identifier:
                # If no user identifier provided, skip rate limiting
                return func(*args, **kwargs)

            # Create cache key
            cache_key = f"rate_limit:{user_identifier}"

            # Get current request data from cache
            rate_data = cache.get(cache_key, {'count': 0, 'reset_at': time.time() + window_seconds})

            current_time = time.time()

            # Check if window has expired
            if current_time >= rate_data['reset_at']:
                # Reset counter
                rate_data = {
                    'count': 1,
                    'reset_at': current_time + window_seconds
                }
            else:
                # Check if limit exceeded
                if rate_data['count'] >= max_requests:
                    time_remaining = int(rate_data['reset_at'] - current_time)
                    print(f"Rate limit exceeded for user {user_identifier}. "
                          f"Requests: {rate_data['count']}/{max_requests}. "
                          f"Reset in: {time_remaining}s")

                    raise RateLimitExceeded(
                        f"Rate limit exceeded. Try again in {time_remaining} seconds."
                    )

                # Increment counter
                rate_data['count'] += 1

            # Save updated rate data
            ttl = int(rate_data['reset_at'] - current_time)
            cache.set(cache_key, rate_data, timeout=max(ttl, 1))

            # Log rate limit info
            print(f"Rate limit check: user={user_identifier}, "
                  f"count={rate_data['count']}/{max_requests}, "
                  f"window={window_seconds}s")

            return func(*args, **kwargs)

        return wrapper
    return decorator


def check_rate_limit(user_identifier, max_requests=10, window_seconds=60):
    """
    Check if user has exceeded rate limit.

    Args:
        user_identifier: Unique identifier for the user (e.g., phone number)
        max_requests: Maximum number of requests allowed within the time window
        window_seconds: Time window in seconds

    Returns:
        tuple: (is_allowed: bool, remaining_requests: int, reset_in: int)

    Raises:
        RateLimitExceeded: If rate limit is exceeded
    """
    cache_key = f"rate_limit:{user_identifier}"

    # Get current request data from cache
    rate_data = cache.get(cache_key, {'count': 0, 'reset_at': time.time() + window_seconds})

    current_time = time.time()

    # Check if window has expired
    if current_time >= rate_data['reset_at']:
        # Reset counter
        rate_data = {
            'count': 1,
            'reset_at': current_time + window_seconds
        }
        cache.set(cache_key, rate_data, timeout=window_seconds)
        return (True, max_requests - 1, window_seconds)

    # Check if limit exceeded
    if rate_data['count'] >= max_requests:
        time_remaining = int(rate_data['reset_at'] - current_time)
        print(f"Rate limit exceeded for user {user_identifier}. "
              f"Requests: {rate_data['count']}/{max_requests}. "
              f"Reset in: {time_remaining}s")

        raise RateLimitExceeded(
            f"Rate limit exceeded. Try again in {time_remaining} seconds."
        )

    # Increment counter
    rate_data['count'] += 1
    ttl = int(rate_data['reset_at'] - current_time)
    cache.set(cache_key, rate_data, timeout=max(ttl, 1))

    remaining = max_requests - rate_data['count']
    reset_in = int(rate_data['reset_at'] - current_time)

    print(f"Rate limit check: user={user_identifier}, "
          f"count={rate_data['count']}/{max_requests}, "
          f"remaining={remaining}, "
          f"reset_in={reset_in}s")

    return (True, remaining, reset_in)


def get_rate_limit_status(user_identifier):
    """
    Get current rate limit status for a user without incrementing the counter.

    Args:
        user_identifier: Unique identifier for the user

    Returns:
        dict: {
            'count': current request count,
            'limit': maximum requests allowed,
            'reset_at': timestamp when counter resets,
            'reset_in': seconds until reset
        }
    """
    cache_key = f"rate_limit:{user_identifier}"
    rate_data = cache.get(cache_key)

    if not rate_data:
        return {
            'count': 0,
            'limit': 0,
            'reset_at': None,
            'reset_in': 0
        }

    current_time = time.time()
    reset_in = max(0, int(rate_data['reset_at'] - current_time))

    return {
        'count': rate_data['count'],
        'reset_at': rate_data['reset_at'],
        'reset_in': reset_in
    }
