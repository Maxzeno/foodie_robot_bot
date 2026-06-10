# MVP Code Review - Critical Issues

## CRITICAL (Must Fix Before Production)

### 1. Test Endpoints Exposed in Production
**File:** `api/views/whatsapp_webhook.py:167-218`
```
/webhook/whatsapp-test - Hardcoded phone number, no auth
/webhook/test-temp-recommendation - Hardcoded user lookup
/webhook/test-temp-time - Debug endpoint
```
**Risk:** Security vulnerability - anyone can trigger bot actions
**Fix:** Remove or protect with authentication before deploy

### 2. Missing Return Statement in Withdrawal
**File:** `api/services/ai/tool_handlers/withdraw.py:98-100`
```python
except:
    Message.bot_message("Failed to place withdrawal...", user=user)
    # Missing: return False
```
**Risk:** Function returns None instead of False on error
**Fix:** Add `return False` after error message

### 3. WhatsApp Flow Webhook Missing Signature Verification
**File:** `api/views/whatsapp_flow_webhook.py:65-108`
**Risk:** No authentication on `/webhook/whatsapp-flow` endpoint - anyone can send encrypted payloads
**Fix:** Add signature verification like the main webhook

### 4. Upload Public Key Endpoint Has No Auth
**File:** `api/views/whatsapp_flow_webhook.py:110-133`
**Risk:** `/webhook/upload-public-key` is unprotected - could be abused
**Fix:** Add admin authentication or remove from production routes

---

## HIGH (Should Fix)

### 5. Exception Swallowing
**Files:** Multiple tool handlers
```python
except Exception as e:
    print(f"Error: {e}")  # Only prints, no logging
```
**Risk:** Errors are silently swallowed, hard to debug in production
**Fix:** Use `logger.exception()` instead of `print()`

### 6. Broad Exception Handling in Orchestrator
**File:** `api/services/ai/orchestrator.py:160-165`
```python
except Exception as e:
    print(f"Error executing tool {function_name}: {e}")
    # No re-raise or user feedback
```
**Risk:** Tool failures are silently ignored, user gets no response
**Fix:** Handle gracefully and notify user of errors

### 7. Print Statements Instead of Logging
**Files:** Throughout codebase (payment_webhook.py, orchestrator.py, tool_handlers/*)
**Risk:** Console output only - no log persistence in production
**Fix:** Replace `print()` with `logger.info()` or `logger.error()`

### 8. Race Condition in Unique Code Generation
**File:** `api/utils/generate.py:4-12`
```python
while model.objects.filter(**filter_kwargs).exists():
    unique_code = get_random_string(...)
```
**Risk:** Two concurrent requests could generate same code before save
**Fix:** Use database-level unique constraint (already present) + retry on IntegrityError

---

## MEDIUM (Recommended)

### 9. Hardcoded Flow IDs
**Files:** Multiple (whatsapp_webhook.py, tool_handlers/*)
```python
flow_id="1822264872503617"  # Hardcoded WhatsApp Flow IDs
```
**Risk:** Harder to change, environment-specific
**Fix:** Move to environment variables or AppSettings

### 10. Missing Transaction Atomicity in NFM Handler
**File:** `api/utils/nfm_reply.py:8-24`
**Risk:** Multiple operations without transaction wrapping
**Fix:** Wrap in `@transaction.atomic` or `with transaction.atomic()`

### 11. No Input Validation on Flow Token Split
**File:** `api/utils/nfm_reply.py:11`
```python
screen_name = flow_token.split('--')[1]
```
**Risk:** IndexError if malformed token
**Fix:** Add validation/try-except

### 12. Order Payment Amount Validation
**File:** `api/views/payment_webhook.py:97-108`
```python
if request_amount < expected_amount:
    order.paid = False  # Still saves partial payment
```
**Risk:** Partial payments are saved but order marked unpaid - potential confusion
**Fix:** Consider not saving partial payments or clear handling

---

## LOW (Nice to Have)

### 13. Missing Model Indexes
**Files:** Order, Message models
**Note:** Consider indexes on frequently filtered fields like `user`, `status`, `created_at`

### 14. Decimal Precision
**File:** `api/models/order.py:52-55`
```python
total_price = models.DecimalField(max_digits=12, decimal_places=2)
```
**Note:** 8 digits supports up to 9,999,999,999.99 - verify this is sufficient for your currency

### 15. No Rate Limiting on Payment Webhook
**File:** `api/views/payment_webhook.py`
**Note:** WhatsApp webhook has rate limiting, payment webhook doesn't

### 16. TODO Comments in Code
**Files:** Multiple
**Note:** Review and either implement or remove TODOs before production

---

## Configuration Checklist

### settings.py Verification
- [ ] `DEBUG = False` in production
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] `SECRET_KEY` is unique and secure
- [ ] Database credentials secured
- [ ] API keys not in version control

### Security Headers (Add if not present)
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SECURE_HSTS_SECONDS = 31536000`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 4     |
| High     | 4     |
| Medium   | 4     |
| Low      | 4     |

**Recommendation:** Fix all Critical issues and High #5-7 before MVP launch. The test endpoints (#1) are the highest priority as they expose functionality without authentication.
