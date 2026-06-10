# MVP Launch Issues - Foodie Robot Backend

## CRITICAL (Must Fix Before Launch)

1. **Exposed Secrets in .env** - `.env` - All API keys, database credentials, and secrets are exposed. Rotate ALL keys immediately.

2. **DEBUG=True** - `.env:3` - Must be `False` in production.

3. **Weak SECRET_KEY** - `.env:2` - `jhskdkjdkjsdqw` is guessable. Generate 50+ char random key.

4. **Test Endpoints in Production** - `api/views/whatsapp_webhook.py:172-230` - Remove `/whatsapp-test` and `/whatsapp-test-template` endpoints.

5. **Hardcoded Test Phone Number** - `api/views/whatsapp_webhook.py:179,195` - Remove hardcoded `2349077745730`.

6. **Windows-Specific Paths** - `foodie_robot/settings.py:67-68` - GDAL/GEOS paths won't work on Linux servers.

7. **Wildcard ALLOWED_HOSTS** - `foodie_robot/settings.py:32-34` - Remove `.ngrok-free.app` and dev IPs.

---

## HIGH Priority

8. **Print Statements Instead of Logging** - Multiple files (`whatsapp_webhook.py`, `payment_webhook.py`, `orchestrator.py`) - Replace with proper logging.

9. **Bare Exception Handling** - `api/views/whatsapp_webhook.py:112`, `payment_webhook.py:168`, `orchestrator.py:164` - Catch specific exceptions.

10. **Missing .get() Error Handling** - `whatsapp_webhook.py:179,195`, `tool_handlers/meal.py:90` - Use try/except or `.filter().first()`.

11. **Broken upload_public_key Endpoint** - `api/views/whatsapp_flow_webhook.py:110-138` - Returns early, never executes upload logic.

12. **Invalid OpenAI Model Name** - `api/services/ai/orchestrator.py:14` - `gpt-5-nano` doesn't exist.

13. **No OpenAI API Timeout** - `orchestrator.py`, `meal_analyzer.py`, `meal_embedding.py` - Calls can hang indefinitely.

14. **Flow Token Parsing Unsafe** - `api/utils/nfm_reply.py:11` - No validation before `split('--')`.

---

## MEDIUM Priority

15. **Database Cache Instead of Redis** - `foodie_robot/settings.py:145-154` - Switch to Redis (already have REDIS_URL).

16. **No Database Connection Pooling** - `foodie_robot/settings.py:124-141` - Add pool settings for production.

17. **Rate Limiting Not Atomic** - `api/utils/rate_limit.py:76-113` - Non-atomic fallback allows bypass under load.

18. **Unclear Payment Validation** - `api/views/payment_webhook.py:97-116` - Double-save logic, unclear business rules.

19. **Silent Flow Screen Failures** - `api/models/message.py:170-171` - Returns None without logging.

20. **Hardcoded Payment Settings** - `api/models/settings.py:20-24` - Phone numbers and amounts hardcoded.

---

## LOW Priority

21. **TODO Comments Left in Code** - `api/views/whatsapp_webhook.py:191,199,221` - Clean up before launch.

22. **User Model Nullable Unique Fields** - `api/models/user.py` - `email`/`username` allow NULL but are unique.

23. **CORS Configuration** - `foodie_robot/settings.py:211-224` - Verify ALLOWED_HOST env var is set.

---

## Quick Wins Checklist

- [ ] Rotate all API keys (OpenAI, WhatsApp, Vendy, Cloudinary)
- [ ] Set `DEBUG=False`
- [ ] Generate strong `SECRET_KEY`
- [ ] Delete test endpoints
- [ ] Remove hardcoded phone numbers
- [ ] Update `ALLOWED_HOSTS` for production domain only
- [ ] Replace `print()` with `logging`
