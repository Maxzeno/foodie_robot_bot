"""
Resilience patterns for AI service:
- Retry logic with exponential backoff
- Circuit breaker pattern
- Rate limiting
- Error handling
"""
import time
import logging
from functools import wraps
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.

    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing if service recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Unique identifier for this circuit
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again (OPEN -> HALF_OPEN)
            success_threshold: Successes needed in HALF_OPEN to close circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        # Cache keys
        self.state_key = f"circuit_breaker:{name}:state"
        self.failure_count_key = f"circuit_breaker:{name}:failures"
        self.success_count_key = f"circuit_breaker:{name}:successes"
        self.last_failure_key = f"circuit_breaker:{name}:last_failure"

    def get_state(self) -> str:
        """Get current circuit state"""
        state = cache.get(self.state_key, self.CLOSED)

        # Check if we should transition from OPEN to HALF_OPEN
        if state == self.OPEN:
            last_failure = cache.get(self.last_failure_key)
            if last_failure:
                if time.time() - last_failure > self.timeout:
                    self._set_state(self.HALF_OPEN)
                    return self.HALF_OPEN

        return state

    def _set_state(self, state: str):
        """Set circuit state"""
        cache.set(self.state_key, state, timeout=3600)
        logger.info(f"Circuit breaker '{self.name}' state changed to: {state}")

    def record_success(self):
        """Record a successful call"""
        state = self.get_state()

        if state == self.HALF_OPEN:
            # Increment success count
            successes = cache.get(self.success_count_key, 0) + 1
            cache.set(self.success_count_key, successes, timeout=300)

            if successes >= self.success_threshold:
                # Close the circuit
                self._set_state(self.CLOSED)
                cache.delete(self.failure_count_key)
                cache.delete(self.success_count_key)
        elif state == self.CLOSED:
            # Reset failure count on success
            cache.delete(self.failure_count_key)

    def record_failure(self):
        """Record a failed call"""
        state = self.get_state()

        if state == self.HALF_OPEN:
            # Any failure in HALF_OPEN reopens circuit
            self._set_state(self.OPEN)
            cache.set(self.last_failure_key, time.time(), timeout=3600)
            cache.delete(self.success_count_key)
        elif state == self.CLOSED:
            # Increment failure count
            failures = cache.get(self.failure_count_key, 0) + 1
            cache.set(self.failure_count_key, failures, timeout=300)

            if failures >= self.failure_threshold:
                # Open the circuit
                self._set_state(self.OPEN)
                cache.set(self.last_failure_key, time.time(), timeout=3600)

    def is_open(self) -> bool:
        """Check if circuit is open"""
        return self.get_state() == self.OPEN

    def reset(self):
        """Manually reset circuit breaker"""
        self._set_state(self.CLOSED)
        cache.delete(self.failure_count_key)
        cache.delete(self.success_count_key)
        cache.delete(self.last_failure_key)


# Global circuit breaker for OpenAI API
openai_circuit_breaker = CircuitBreaker(
    name="openai_api",
    failure_threshold=5,
    timeout=60,
    success_threshold=2
)


def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """
    Decorator to apply circuit breaker pattern.

    Usage:
        @with_circuit_breaker(openai_circuit_breaker)
        def make_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if circuit_breaker.is_open():
                logger.warning(f"Circuit breaker '{circuit_breaker.name}' is OPEN, rejecting call")
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{circuit_breaker.name}' is open"
                )

            try:
                result = func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except Exception as e:
                circuit_breaker.record_failure()
                raise

        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retry with exponential backoff.

    Usage:
        @with_retry(max_attempts=3, backoff_factor=2.0)
        def make_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_attempts} attempts failed")

            raise last_exception

        return wrapper
    return decorator


class RateLimiter:
    """
    Rate limiter to prevent excessive API calls.
    """

    def __init__(self, name: str, max_calls: int, period: int):
        """
        Initialize rate limiter.

        Args:
            name: Unique identifier
            max_calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        self.name = name
        self.max_calls = max_calls
        self.period = period

    def is_allowed(self, key: str) -> bool:
        """
        Check if a call is allowed for the given key.

        Args:
            key: Unique key (e.g., user ID)

        Returns:
            True if allowed, False if rate limit exceeded
        """
        cache_key = f"rate_limit:{self.name}:{key}"
        calls = cache.get(cache_key, [])

        # Remove old calls outside the time window
        current_time = time.time()
        calls = [t for t in calls if current_time - t < self.period]

        if len(calls) >= self.max_calls:
            logger.warning(f"Rate limit exceeded for {key} on {self.name}")
            return False

        # Add current call
        calls.append(current_time)
        cache.set(cache_key, calls, timeout=self.period)

        return True

    def get_remaining(self, key: str) -> int:
        """Get remaining calls for key"""
        cache_key = f"rate_limit:{self.name}:{key}"
        calls = cache.get(cache_key, [])

        current_time = time.time()
        calls = [t for t in calls if current_time - t < self.period]

        return max(0, self.max_calls - len(calls))


# Global rate limiter for AI calls
ai_rate_limiter = RateLimiter(
    name="ai_orchestrator",
    max_calls=10,  # 10 calls
    period=60       # per minute
)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded"""
    pass


def handle_ai_errors(func: Callable) -> Callable:
    """
    Decorator for comprehensive AI error handling.

    Handles:
    - OpenAI API errors
    - Circuit breaker open
    - Rate limit exceeded
    - Generic exceptions
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CircuitBreakerOpenError as e:
            logger.error(f"Circuit breaker open: {e}")
            return {
                "success": False,
                "error": "Service temporarily unavailable. Please try again later.",
                "error_type": "circuit_breaker_open"
            }
        except RateLimitExceededError as e:
            logger.error(f"Rate limit exceeded: {e}")
            return {
                "success": False,
                "error": "Too many requests. Please wait a moment.",
                "error_type": "rate_limit_exceeded"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                "success": False,
                "error": "An error occurred. Please try again.",
                "error_type": "unexpected_error"
            }

    return wrapper
