"""
Test script for rate limiting functionality.

Run with: python test_rate_limit.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodie_robot.settings')
django.setup()

from api.utils.rate_limit import check_rate_limit, RateLimitExceeded, get_rate_limit_status
import time


def test_rate_limiting():
    """Test rate limiting with a sample phone number."""
    print("=" * 60)
    print("Rate Limiting Test")
    print("=" * 60)
    print()

    test_phone = "+2348099999999"  # Test phone number
    max_requests = 5  # Lower limit for testing
    window_seconds = 10  # Shorter window for testing

    print(f"Testing with phone: {test_phone}")
    print(f"Limit: {max_requests} requests per {window_seconds} seconds")
    print()

    # Test normal requests
    print("Testing normal requests...")
    success_count = 0
    for i in range(max_requests + 3):
        try:
            is_allowed, remaining, reset_in = check_rate_limit(
                user_identifier=test_phone,
                max_requests=max_requests,
                window_seconds=window_seconds
            )
            success_count += 1
            print(f"✓ Request {i + 1}: Success - {remaining} remaining, resets in {reset_in}s")
        except RateLimitExceeded as e:
            print(f"✗ Request {i + 1}: Rate limited - {e}")

    print()
    print(f"Total successful requests: {success_count}/{max_requests + 3}")
    print()

    # Check status
    print("Checking rate limit status...")
    status = get_rate_limit_status(test_phone)
    print(f"Current count: {status['count']}")
    print(f"Reset in: {status['reset_in']} seconds")
    print()

    # Wait for reset
    if status['reset_in'] > 0:
        print(f"Waiting {status['reset_in']} seconds for rate limit to reset...")
        time.sleep(status['reset_in'] + 1)
        print("✓ Rate limit reset!")
        print()

        # Try again after reset
        print("Testing after reset...")
        try:
            is_allowed, remaining, reset_in = check_rate_limit(
                user_identifier=test_phone,
                max_requests=max_requests,
                window_seconds=window_seconds
            )
            print(f"✓ Request successful after reset - {remaining} remaining")
        except RateLimitExceeded as e:
            print(f"✗ Request failed: {e}")

    print()
    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)


def test_multiple_users():
    """Test rate limiting with multiple users."""
    print()
    print("=" * 60)
    print("Multiple Users Test")
    print("=" * 60)
    print()

    users = ["+2348011111111", "+2348022222222", "+2348033333333"]
    max_requests = 3
    window_seconds = 10

    print(f"Testing {len(users)} users with limit: {max_requests} per {window_seconds}s")
    print()

    for user in users:
        print(f"Testing user: {user}")
        for i in range(max_requests + 1):
            try:
                is_allowed, remaining, reset_in = check_rate_limit(
                    user_identifier=user,
                    max_requests=max_requests,
                    window_seconds=window_seconds
                )
                print(f"  ✓ Request {i + 1}: {remaining} remaining")
            except RateLimitExceeded as e:
                print(f"  ✗ Request {i + 1}: Rate limited")
        print()

    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    print()
    print("Starting rate limiting tests...")
    print()

    # Test 1: Basic rate limiting
    test_rate_limiting()

    # Test 2: Multiple users
    test_multiple_users()

    print()
    print("All tests completed!")
