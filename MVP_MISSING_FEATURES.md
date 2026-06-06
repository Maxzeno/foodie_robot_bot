# Missing Features for MVP Launch

**Generated**: 2025-12-01
**Status**: Pre-Launch Review

---

## **🚨 CRITICAL - Must Fix Before Launch**

### 1. **Payment Webhook Security**
**File**: `api/views/payment_webhook.py:20-23`
**Status**: Currently commented out
**Risk**: Anyone can fake payment webhooks and mark orders as paid without actual payment

```python
# TODO: confirm request is from Vendy using the secret hash in the header
# if settings.VENDY_SECRET_HASH == None or settings.VENDY_SECRET_HASH != request.headers.get('secretHash'):
#     print("Invalid secret hash in webhook request")
#     return HttpResponse("Unauthorized", status=401)
```

**Action Required**:
- Uncomment and implement the secret hash validation
- Get VENDY_SECRET_HASH from Vendy documentation
- Add to environment variables
- Test with real webhooks

---

### 2. **Order Cancellation & Refunds**
**Status**: Missing entirely
**Impact**: Users can't cancel orders, no refund flow exists

**Features Needed**:
- Cancel order tool/handler for users
- Cancellation deadline (e.g., within 5 mins of placing order)
- Refund webhook/flow integration with Vendy payment gateway
- Admin cancellation capability
- Refund status tracking in Order model

**Implementation**:
- Add `cancelled` status to OrderStatus choices
- Create `cancel_order` tool handler
- Add `refund_requested`, `refund_completed` fields to Order model
- Integrate with Vendy refund API

---

### 3. **Restaurant/Kitchen Order Notification System**
**Status**: Missing
**Impact**: Restaurants don't know when orders come in

**Features Needed**:
- Notify restaurant when order is paid (email/SMS/WhatsApp)
- Order acceptance/rejection by restaurant
- Kitchen display system or notification channel
- Restaurant dashboard for active orders

**Implementation**:
- Add email/phone to Restaurant model (already exists)
- Send notification in payment webhook after order.paid = True
- Consider: WhatsApp Business API for restaurants
- Consider: Simple web dashboard for restaurants

---

### 4. **Delivery/Dispatch Management**
**Status**: Order status exists but no way to update it
**Impact**: Orders stay "pending" forever, users don't know order progress

**Features Needed**:
- Admin/restaurant panel to update order status
  - PENDING → DISPATCHED → ARRIVED → RECEIVED
- API endpoints for third-party delivery services
- Automatic status notifications to users when status changes
- Delivery tracking integration (optional)

**Current Status Flow**:
- Payment webhook sets order to `paid=True`
- Status remains `PENDING`
- No mechanism to move to DISPATCHED/ARRIVED/RECEIVED
- Review request sent on RECEIVED (signals.py:15-46)

**Implementation**:
- Create admin actions to update order status
- Add API endpoint: `POST /api/orders/{id}/status`
- Add webhook for delivery partners
- Send WhatsApp notification on each status change

---

### 5. **Withdrawal Processing & Approval**
**File**: `api/services/ai/tool_handlers/withdraw.py:65-100`
**Status**: Users can request, but no approval/processing flow

**Missing**:
- Admin approval interface for withdrawals
- Payment processing integration (bank transfer)
- Status update notifications to users
- Rejection reason handling

**Current Flow**:
- User requests withdrawal
- Balance immediately set to 0
- Withdrawal created with status="pending"
- No follow-up process

**Implementation**:
- Add admin actions: Approve/Reject withdrawal
- Integrate with payment processor for bank transfers
- Send notifications on approval/rejection
- Add rejection reason field
- Restore balance if rejected

---

## **⚠️ HIGH PRIORITY - Important for UX**

### 6. **Order Status Notifications**
**Current**: Users must manually check order status via tool
**Needed**: Proactive WhatsApp notifications when:
- Order is dispatched ("Your order is on the way!")
- Driver is nearby/arrived ("Your order has arrived!")
- Automated reminders if order delayed

**Implementation**:
- Add signal handler for Order status changes
- Send Message on each status transition
- Include estimated delivery time

---

### 7. **Error Handling in Order Flow**
**Issues Found**:
- `place_order_form` (order.py:103-113): Exception handling too generic
- No retry mechanism for failed WhatsApp flows
- No notification when payment link generation fails (order.py:230-235)

**Improvements Needed**:
```python
# Current:
except Exception as e:
    Message.bot_message(
        "Sorry, something went wrong while initiating your order. Please try again.",
        user=user
    )
    return False

# Better:
except WhatsAppFlowException as e:
    logger.error(f"WhatsApp flow failed for user {user.id}: {e}")
    # Retry logic or fallback
except ValidationError as e:
    # Specific error message
except Exception as e:
    logger.critical(f"Unexpected error in order placement: {e}")
    # Alert admin
```

---

### 8. **Meal Availability Management**
**Current**: Only boolean `available` field
**File**: `api/models/meal.py:160`

**Missing**:
- Time-based availability (e.g., breakfast only 6AM-11AM)
- Stock/quantity limits per day
- Out-of-stock notifications
- Auto-disable when restaurant closed

**Implementation**:
- Add `available_from_time` and `available_to_time` fields
- Add `daily_stock_limit` and `remaining_stock` fields
- Reset stock daily via cron job
- Check availability in place_order

---

### 9. **Delivery Time Estimates**
**Current**: Only delivery fee calculated
**File**: `api/services/ai/tool_handlers/order.py:207`

**Missing**:
- Estimated delivery time (e.g., "30-45 minutes")
- Restaurant preparation time
- Delivery windows
- Real-time tracking (advanced)

**Implementation**:
- Add `preparation_time_minutes` to Restaurant model
- Calculate: prep_time + delivery_distance/avg_speed
- Display in order confirmation
- Update estimate based on actual dispatch time

---

## **📋 MEDIUM PRIORITY - Nice to Have**

### 10. **Order Modification**
**Missing**:
- Change delivery address after ordering (before dispatch)
- Update quantity before payment
- Add/modify special instructions
- "Recreate order" with same items

**Current Workaround**: User must cancel and re-order

---

### 11. **Restaurant Business Hours**
**Current**: No time restrictions on ordering
**File**: `api/models/restaurant.py` (no hours field)

**Needed**:
- Operating hours per restaurant
- Days of operation
- Holiday/special hours
- Prevent orders outside business hours

**Implementation**:
- Add `opening_time`, `closing_time` to Restaurant
- Add `closed_days` array field
- Validate in place_order
- Show "Restaurant closed" message

---

### 12. **Delivery Zone Validation**
**Current**: Only checks city match (order.py:172-177)

**Could Add**:
- Specific delivery radius per restaurant (e.g., 5km)
- "Out of delivery area" warnings before order
- Premium delivery zones with higher fees
- Delivery zone visualization on map

---

### 13. **Multi-Currency Handling**
**Current**: Single currency per city
**File**: `api/models/order.py:44`

**Could Improve**:
- Currency conversion for cross-city orders
- Multiple payment methods (card, bank transfer, etc.)
- Support for multiple currencies in wallet

---

### 14. **Analytics & Monitoring**
**Missing**:
- Order completion rate tracking
- Popular meals dashboard
- Revenue reporting by city/restaurant
- Failed payment tracking
- User retention metrics
- Referral conversion rates

**Implementation**:
- Add analytics cron job
- Create admin dashboard views
- Export reports (CSV/PDF)
- Integration with analytics tools

---

## **🔒 SECURITY & COMPLIANCE**

### 15. **Data Privacy**
**Check Needed**:
- GDPR/data protection compliance
- User data deletion capability (right to be forgotten)
- Privacy policy integration
- Terms of service acceptance
- Cookie consent (if web version exists)

**Files to Review**:
- User model stores phone, location, preferences
- Message history stored indefinitely
- Order history with personal addresses

---

### 16. **Rate Limiting** ✅ IMPLEMENTED
**Status**: ✅ Completed
**Implementation**:
- Database-backed cache rate limiting
- 20 messages per minute per user
- Phone number-based identification
- User-friendly warning messages

**Files**:
- `api/utils/rate_limit.py` - Rate limiting utility
- `api/views/whatsapp_webhook.py:94-111` - Applied to webhook
- `foodie_robot/settings.py:142-153` - Cache configuration

**Additional Protections Needed**:
- IP-based rate limiting for additional security
- Different limits for premium users
- CAPTCHA for suspicious activity (future)
- Automatic blocking of abusive users (future)

---

### 17. **Payment Verification Edge Cases**
**File**: `api/views/payment_webhook.py`

**Issues**:
- Line 20: Secret hash validation disabled (CRITICAL)
- Line 67-73: What if payment is partial? Currently rejects
- Line 75-86: Price change between order and payment
- No handling for duplicate webhooks (idempotency)

**Improvements**:
- Enable secret hash validation
- Add idempotency key checking
- Handle partial payments better
- Add webhook retry handling

---

## **🛠️ OPERATIONAL**

### 18. **Restaurant Onboarding Flow**
**Current**: Admin panel only

**Could Add**:
- Restaurant self-service signup portal
- Menu upload interface (CSV/Excel)
- Photo upload for meals
- Payout management for restaurants
- Performance analytics for restaurants

---

### 19. **Customer Support Tools**
**Current**: Just contact button (support.py)
**File**: `api/services/ai/tool_handlers/support.py`

**Missing**:
- Ticket/case management system
- Order issue reporting ("Wrong item", "Cold food", etc.)
- Direct chat with support agent
- FAQ/Help center integration
- Support ticket status tracking

**Implementation**:
- Create Support Ticket model
- Link tickets to orders
- Admin interface for support agents
- Auto-categorize issues

---

### 20. **Testing & Staging**
**Found**: Test endpoints in production code
**File**: `api/views/whatsapp_webhook.py:161-202`

**Action Required**:
- Remove test endpoints before production (marked TODO)
- Lines 161-175: test-temp endpoint
- Lines 178-202: test-message-temp endpoint
- Line 142-159: whatsapp-test endpoint
- Or protect with authentication/environment checks

---

## **⚡ Quick Wins (Low Effort, High Impact)**

### 1. Enable Payment Webhook Security (5 minutes)
```python
# In payment_webhook.py line 20-23
if settings.VENDY_SECRET_HASH == None or settings.VENDY_SECRET_HASH != request.headers.get('secretHash'):
    print("Invalid secret hash in webhook request")
    return HttpResponse("Unauthorized", status=401)
```

### 2. Add Order Cancellation Window (2-3 hours)
- Add 5-minute cancellation window after order creation
- Create cancel_order tool handler
- Add cancellation policy to order confirmation

### 3. Restaurant Email Notifications (1 hour)
- Send email to restaurant when order is paid
- Include order details, customer info
- Add "View Order" link to admin

### 4. Admin Order Status Update UI (2-3 hours)
- Add dropdown in admin to change order status
- Auto-send WhatsApp notification on status change

### 5. Automated Order Status Messages (1 hour)
- Add signal handler for order status changes
- Send WhatsApp message with status updates
- Include tracking info when available

---

## **MVP Launch Checklist - Priority Order**

### Phase 1: Critical (Before Launch)
- [ ] **Fix payment webhook security** (5 mins)
- [ ] **Add order status update capability** (admin/restaurant)
- [ ] **Order cancellation flow** (user + time limit)
- [ ] **Restaurant order notifications** (email/WhatsApp)
- [ ] **Remove/protect test endpoints**

### Phase 2: High Priority (Week 1)
- [ ] **Withdrawal approval system**
- [ ] **Order status auto-notifications**
- [ ] **Delivery time estimates**
- [ ] **Error handling improvements**
- [ ] **Rate limiting**

### Phase 3: Medium Priority (Month 1)
- [ ] **Meal availability management**
- [ ] **Restaurant business hours**
- [ ] **Order modification**
- [ ] **Analytics dashboard**
- [ ] **Customer support ticketing**

### Phase 4: Nice to Have (Post-Launch)
- [ ] **Delivery zone validation**
- [ ] **Multi-currency support**
- [ ] **Restaurant self-service portal**
- [ ] **Advanced analytics**

---

## **Recommendations**

### Immediate Actions (Today):
1. Enable payment webhook security validation
2. Create admin interface for order status updates
3. Remove or protect test endpoints
4. Set up restaurant email notifications

### This Week:
1. Implement order cancellation with 5-min window
2. Add automated order status messages
3. Create withdrawal approval workflow
4. Improve error handling and logging

### Before Public Launch:
1. Security audit (payment flow, webhooks, user data)
2. Load testing (AI orchestrator, webhooks, database)
3. Data backup and recovery plan
4. Privacy policy and terms of service
5. Customer support process documented

---

## **Notes**

- Most critical issue is **payment webhook security** - this is a security vulnerability
- **Order lifecycle management** is incomplete - no way to move orders through states
- **Withdrawal system** creates money but never pays out
- Consider hiring a security consultant for payment flow review
- Test all WhatsApp flows thoroughly before launch
- Set up monitoring/alerting for failed payments

---

**Next Steps**: Review this document with the team and prioritize which features to implement before launch.
