# Rate Limiting Setup Guide

## Overview

Rate limiting has been implemented to prevent spam and abuse on the WhatsApp webhook endpoint. Each user is limited to **20 messages per minute**.

---

## Configuration

### Cache Backend
The rate limiting uses Django's database cache backend:

```python
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'api_cache_table',
        'OPTIONS': {
            'MAX_ENTRIES': 10000,
            'CULL_FREQUENCY': 4,
        }
    }
}
```

### Rate Limits
- **Limit**: 20 requests per user
- **Window**: 60 seconds (1 minute)
- **Identifier**: User's phone number

---

## Setup Instructions

### 1. Create the Cache Table

Run this command to create the database cache table:

```bash
python manage.py createcachetable
```

This creates the `api_cache_table` table in your database.

### 2. Test Rate Limiting (Optional)

You can test the rate limiting with this Python script:

```python
from api.utils.rate_limit import check_rate_limit, RateLimitExceeded

# Test rate limiting
phone = "+2348012345678"

try:
    for i in range(25):  # Try 25 requests (limit is 20)
        is_allowed, remaining, reset_in = check_rate_limit(
            user_identifier=phone,
            max_requests=20,
            window_seconds=60
        )
        print(f"Request {i+1}: Allowed={is_allowed}, Remaining={remaining}, Reset in {reset_in}s")
except RateLimitExceeded as e:
    print(f"Rate limit exceeded: {e}")
```

---

## How It Works

### User Experience

1. **Normal Usage**: Users can send up to 20 messages per minute
2. **Rate Limit Exceeded**: When exceeded, users receive:
   - A message: "You're sending messages too quickly. Please wait a moment before trying again."
   - Their message is not processed
   - They must wait for the rate limit window to reset

### Technical Flow

```
Webhook Request
    ↓
Signature Verification
    ↓
Parse Message & Extract Phone
    ↓
Check Rate Limit (phone number)
    ↓
    ├─ ALLOWED → Process Message
    └─ BLOCKED → Send Warning & Return
```

### Cache Keys

Rate limit data is stored with keys like:
```
rate_limit:+2348012345678
```

Each key stores:
```python
{
    'count': 15,  # Current request count
    'reset_at': 1701234567.89  # Unix timestamp when counter resets
}
```

---

## Files Modified

### New Files
1. **`api/utils/rate_limit.py`** - Rate limiting utility functions
2. **`RATE_LIMITING_SETUP.md`** - This documentation

### Modified Files
1. **`foodie_robot/settings.py`**
   - Added `CACHES` configuration (lines 142-153)

2. **`api/views/whatsapp_webhook.py`**
   - Imported rate limit utilities (line 17)
   - Added rate limit check before processing messages (lines 94-111)

---

## Customization

### Adjust Rate Limits

Edit `api/views/whatsapp_webhook.py` line 96-99:

```python
check_rate_limit(
    user_identifier=phone,
    max_requests=30,  # Change this (e.g., 30 messages)
    window_seconds=120  # Change this (e.g., 2 minutes)
)
```

### Custom Warning Message

Edit line 107-109 in `whatsapp_webhook.py`:

```python
Message.bot_message(
    "Your custom warning message here.",
    user=user_obj
)
```

### Disable Rate Limiting (Not Recommended)

Comment out lines 94-111 in `whatsapp_webhook.py`:

```python
# # Rate limiting: 20 messages per minute per user
# try:
#     check_rate_limit(...)
# except RateLimitExceeded as e:
#     ...
```

---

## Monitoring

### Check Rate Limit Status

You can check a user's current rate limit status:

```python
from api.utils.rate_limit import get_rate_limit_status

status = get_rate_limit_status("+2348012345678")
print(f"Count: {status['count']}")
print(f"Reset in: {status['reset_in']} seconds")
```

### View Logs

Rate limiting events are logged to console:

```
Rate limit check: user=+2348012345678, count=15/20, remaining=5, reset_in=45s
```

```
Rate limit exceeded for user +2348012345678. Requests: 21/20. Reset in: 30s
```

---

## Production Considerations

### 1. Use Redis for Better Performance

For production, consider switching to Redis cache:

```python
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

Install Redis client:
```bash
pip install redis django-redis
```

### 2. Different Limits for Different User Types

```python
# Example: Premium users get higher limits
if user.is_premium:
    max_requests = 50
else:
    max_requests = 20

check_rate_limit(phone, max_requests=max_requests, window_seconds=60)
```

### 3. IP-Based Rate Limiting

Add IP-based rate limiting for additional protection:

```python
client_ip = request.META.get('REMOTE_ADDR')
check_rate_limit(f"ip:{client_ip}", max_requests=100, window_seconds=60)
```

### 4. Adjust Limits Based on Usage Patterns

Monitor your logs and adjust limits based on legitimate usage patterns:

- Peak hours: Increase limits temporarily
- Known spam numbers: Lower limits or block
- Business hours: Different limits than off-hours

---

## Troubleshooting

### Cache Table Not Found

**Error**: `Table 'api_cache_table' doesn't exist`

**Solution**:
```bash
python manage.py createcachetable
```

### Rate Limiting Not Working

1. Check cache is configured correctly in `settings.py`
2. Verify cache table exists: `python manage.py shell`
   ```python
   from django.core.cache import cache
   cache.set('test', 'value', 60)
   print(cache.get('test'))  # Should print 'value'
   ```

3. Check logs for rate limit messages

### Users Getting Rate Limited Too Quickly

1. Increase `max_requests` or `window_seconds`
2. Check for duplicate webhook deliveries from WhatsApp
3. Verify `found_msg` check is working (line 90-92)

---

## API Reference

### `check_rate_limit(user_identifier, max_requests, window_seconds)`

Check and increment rate limit for a user.

**Parameters:**
- `user_identifier` (str): Unique identifier (e.g., phone number)
- `max_requests` (int): Maximum requests allowed
- `window_seconds` (int): Time window in seconds

**Returns:**
- `tuple`: (is_allowed, remaining_requests, reset_in_seconds)

**Raises:**
- `RateLimitExceeded`: When limit is exceeded

### `get_rate_limit_status(user_identifier)`

Get current rate limit status without incrementing counter.

**Parameters:**
- `user_identifier` (str): Unique identifier

**Returns:**
- `dict`: {count, reset_at, reset_in}

---

## Security Notes

1. **Rate limiting is defense-in-depth** - Not the only security measure
2. **WhatsApp signature verification** is still the primary security control
3. **Rate limits prevent** spam, abuse, and excessive AI costs
4. **User experience** - Balance security with usability
5. **Monitor logs** - Watch for suspicious patterns

---

## Summary

✅ **Implemented**: Global rate limiting (20 msg/min per user)
✅ **Cached**: Database-backed cache (upgrade to Redis for production)
✅ **User Friendly**: Warning message sent when rate limited
✅ **Configurable**: Easy to adjust limits and behavior
✅ **Monitored**: Logging for debugging and monitoring

**Next Step**: Run `python manage.py createcachetable` to enable rate limiting.
