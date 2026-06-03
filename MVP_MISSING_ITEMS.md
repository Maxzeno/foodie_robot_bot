# MVP Missing Items & TODO List

## CRITICAL - Must Fix Before Launch

### 1. Withdrawal System (NOT IMPLEMENTED)
- `api/services/ai/tool_handlers/withdraw.py` - Returns "Not Implemented yet"
- No withdrawal methods (bank details, PayPal, crypto)
- Users cannot cash out referral earnings

### 2. Security Vulnerabilities
- **WhatsApp Webhook** (`api/views/whatsapp_webhook.py:23`) - No signature verification
- **Payment Webhook** (`api/views/payment_webhook.py:20`) - No Vendy hash validation
- Anyone can spoof messages/payments

### 3. Delivery Fee Calculation
- `api/services/ai/tool_handlers/order.py:135` - Hardcoded at 10.00
- Should calculate based on distance/zones

### 4. LLM Recommendation Bug
- `api/services/recommendation/meal_recommendation.py` - Using wrong OpenAI API
- `client.responses.create()` doesn't exist - will crash
- Should use `chat.completions.create()`

### 5. WhatsApp Flow Business Logic
- `api/views/whatsapp_flow_webhook.py:64` - Just placeholder
- `api/models/message.py:169` - bot_message_flow not implemented
- Flow features don't work end-to-end

### 6. Test Endpoint in Production
- `/webhook/test-temp` endpoint exposes testing functionality
- Hardcoded phone number: "2349077745730"
- Remove before deployment

### 7. Order Model Save Method
- `api/models/order.py:58` - TODO: calculate total price and delivery fee
- Could lead to inconsistent pricing

## HIGH PRIORITY - Should Fix Before Launch

### 8. Commented Out Critical Logic
- `api/services/recommendation/meal_recommendation.py:73` - Eligible meals filtering disabled
- `api/services/recommendation/meal_recommendation.py:74` - Recent recommendation exclusion disabled
- Users may get unsuitable recommendations

### 9. Zero Test Coverage
- `api/tests.py` - Empty file
- No unit, integration, or API tests
- Unknown reliability

### 10. Minimal Logging
- Using `print()` instead of logging module
- No structured logging for production monitoring
- Can't debug issues effectively

### 11. Missing Input Validation
- No validation on function parameters
- No decimal/type checks for financial data
- Could crash on malformed input

### 12. Transaction Safety
- No atomic transactions for critical operations
- Order creation + recommendations not transactional
- Payment processing missing idempotency

### 13. Meal Preference Tracking Bug
- Uses deprecated MealPreference model
- Should use Meal.prefer_*/dislike_* fields
- Preference tracking may fail

## MEDIUM PRIORITY - Nice to Have

### 14. Hardcoded Configuration
- Delivery fee, embedding dimensions, test phone numbers
- Should use environment variables or AppSettings
- Difficult to adjust per region

### 15. Vendy Payment Environment
- Hardcoded to production URL
- No staging/development switching
- Could mix test data with production

### 16. Error Handling Improvements
- Generic error messages ("Error...")
- No detailed error codes
- Difficult to debug

### 17. Missing API Features
- No rate limiting
- No API authentication beyond webhooks
- No health check endpoints

### 18. Multi-Language Support
- All text hardcoded in English
- No i18n/l10n infrastructure

### 19. Order Status Notifications
- Only payment confirmations implemented
- No delivery updates from backend
- No inactive user reminders

### 20. Database Optimization
- Missing indexes on common queries
- No unique constraints on Recommendation model
- Could have performance issues at scale

## TODO Comments in Code (15 total)

| File | Line | Issue |
|------|------|-------|
| orchestrator.py | 44 | Remove get_current_location tool to reduce tokens |
| orchestrator.py | 54 | Remove get_user_meal_preferences tool |
| orchestrator.py | 60 | Implement request_update_info, update_info tools |
| orchestrator.py | 77 | Potentially remove search_meals, get_nutritional_info |
| order.py | 135 | Calculate delivery fee based on distance |
| withdraw.py | 11 | Maybe use WhatsApp flow for withdrawals |
| meal_recommendation.py | 73-74 | Re-enable eligible meals filtering |
| message.py | 169, 173 | Implement bot_message_flow properly |
| order.py | 58 | Auto-calculate total price on save |
| withdrawal.py | 15 | Add withdrawal method fields |
| whatsapp_webhook.py | 23 | Add signature verification |
| whatsapp_flow_webhook.py | 64 | Implement flow business logic |
| payment_webhook.py | 20 | Add Vendy hash verification |

## Summary Stats

| Area | Completeness | Risk Level |
|------|-------------|-----------|
| Core Models | 95% | Low |
| WhatsApp Integration | 80% | Medium |
| AI/LLM Tools | 85% | Medium |
| Recommendations | 70% | **High** |
| Orders | 90% | Low |
| Referrals | 95% | Low |
| **Withdrawals** | **5%** | **CRITICAL** |
| **Payment Integration** | **70%** | **CRITICAL** |
| **Security** | **40%** | **CRITICAL** |
| **Testing** | **0%** | **High** |
| Logging | 30% | High |
| Error Handling | 50% | High |

## Quick Fix Checklist

- [ ] Implement withdrawal system with payment methods
- [ ] Add WhatsApp webhook signature verification
- [ ] Add Vendy payment webhook hash validation
- [ ] Fix delivery fee calculation (distance-based)
- [ ] Fix LLM recommendation API call
- [ ] Implement WhatsApp Flow business logic
- [ ] Remove test endpoint from production
- [ ] Fix order.save() to calculate pricing
- [ ] Re-enable meal eligibility filtering
- [ ] Re-enable recent recommendation exclusion
- [ ] Add basic test coverage for critical paths
- [ ] Replace print() with proper logging
- [ ] Add transaction boundaries for orders
- [ ] Add input validation on tool handlers
- [ ] Fix meal preference tracking model
- [ ] Add payment idempotency
- [ ] Move hardcoded values to settings
- [ ] Add API rate limiting
- [ ] Add health check endpoint
- [ ] Add database indexes for performance
