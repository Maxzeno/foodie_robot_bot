# 🐛 MVP BUG REPORT - FoodieRobot Backend

**Generated:** 2025-12-21
**Status:** Pre-Launch Security & Bug Audit
**Total Issues Found:** 25

---

## ⚠️ CRITICAL BUGS (Must Fix Before Launch)

### 1. **BARE EXCEPT CLAUSE - Catches SystemExit**
**Location:** `api/views/whatsapp_webhook.py:56`
**Issue:** Bare `except:` catches all exceptions including SystemExit, KeyboardInterrupt
**Impact:** Silent failures, impossible debugging, security risk
**Fix:**
```python
# BEFORE
try:
    username = change["contacts"][0]['profile']['name']
except:  # ❌ BAD
    username = None

# AFTER
try:
    username = change["contacts"][0]['profile']['name']
except (KeyError, IndexError, TypeError):  # ✅ GOOD
    username = None
```

---

### 2. **RACE CONDITION - Referral Bonus Double Payment**
**Location:** `api/views/payment_webhook.py:135-147`
**Issue:** Multiple webhooks can credit referral bonus multiple times
**Impact:** 💰 Financial loss, balance manipulation
**Fix:**
```python
# Add flag to Order model
with transaction.atomic():
    order = Order.objects.select_for_update().get(id=order_id)
    if order.referral_bonus_credited:
        return  # Already processed
    # ... process bonus ...
    order.referral_bonus_credited = True
    order.save()
```

---

### 3. **MISSING STOCK DECREMENT**
**Location:** `api/services/ai/tool_handlers/order.py:251-269`
**Issue:** Orders created but `meal.remaining_stock` never decremented
**Impact:** Overbooking, inventory chaos, angry customers
**Fix:**
```python
with transaction.atomic():
    meal = Meal.objects.select_for_update().get(id=meal_id)
    if meal.remaining_stock < number_of_plates:
        raise ValueError("Insufficient stock")
    meal.remaining_stock -= number_of_plates
    meal.save(update_fields=['remaining_stock'])

    order = Order.objects.create(...)
```

---

### 4. **PASSWORD NOT HASHED - SECURITY BREACH**
**Location:** `api/models/user.py:63-85`
**Issue:** Password hashing logic broken - references non-existent `self._password`
**Impact:** 🚨 CRITICAL - Plaintext passwords in database
**Fix:**
```python
def save(self, *args, **kwargs):
    if self.pk is None:  # New user
        self.set_password(self.password)
    super().save(*args, **kwargs)
```

---

### 5. **WITHDRAWAL - No Limits or Validation**
**Location:** `api/services/ai/tool_handlers/withdraw.py:73-94`
**Issue:**
- Withdraws entire balance instantly (no daily limit)
- No pending withdrawal check (can create multiple)
- No bank account verification
**Impact:** Users drain funds, fraud risk
**Fix:**
```python
# Check pending withdrawals
pending = Withdrawal.objects.filter(
    user=user, status='pending'
).exists()
if pending:
    return False, "You have a pending withdrawal"

# Add daily limit check
today = timezone.now().date()
today_total = Withdrawal.objects.filter(
    user=user, created_at__date=today
).aggregate(Sum('amount'))['amount__sum'] or 0

if today_total + amount > DAILY_WITHDRAWAL_LIMIT:
    return False, "Daily limit exceeded"
```

---

## 🔴 HIGH SEVERITY BUGS

### 6. **Midnight Classified as "Evening"**
**Location:** `api/models/user.py:118-127`
**Issue:** Midnight-7:59 AM returns 'evening', sending wrong recommendations
**Impact:** Users get dinner recommendations at 3 AM
**Fix:**
```python
def get_time_period(self):
    hour = self.get_local_time().hour
    if 6 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 18:
        return 'afternoon'
    else:
        return 'evening'
```

---

### 7. **N+1 Query Problem - Meal Search**
**Location:** `api/services/ai/tool_handlers/meal_search.py:42-44`
**Issue:** Queries cuisines for each meal in loop
**Impact:** Slow performance, 5 meals = 5+ queries
**Fix:**
```python
meals = meals.prefetch_related('cuisine', 'fitness_goals', 'health_conditions')
```

---

### 8. **Partial Payment Saved Then Rejected**
**Location:** `api/views/payment_webhook.py:90-103`
**Issue:** Saves partial payment state, then returns 400 error
**Impact:** Orphaned order states, next attempt might succeed incorrectly
**Fix:**
```python
# Don't save until fully validated
if request_amount < expected_amount:
    return HttpResponse("Amount mismatch", status=400)
    # Don't save order here

# Only save after full validation
order.amount_paid = request_amount
order.paid = True
order.save()
```

---

### 9. **Missing Null Checks - City Currency**
**Location:** Multiple files
**Issue:** `user.city.currency.symbol` crashes if user has no city
**Impact:** 500 errors during checkout
**Fix:**
```python
# Always check
currency_symbol = "₦"  # Default
if user.city and user.city.currency:
    currency_symbol = user.city.currency.symbol
```

---

### 10. **Duplicate Recommendation Constraint Disabled**
**Location:** `api/models/recommendation.py:23-30`
**Issue:** Unique constraint commented out
**Impact:** Duplicate recommendations sent to users
**Fix:** Uncomment the constraint and add migration

---

## 🟡 MEDIUM SEVERITY BUGS

### 11. **Recommendation Streak Calculation Bug**
**Location:** `api/models/user.py:147-194`
**Issue:** Logic breaks streak incorrectly on first gap
**Impact:** Wrong streak counts, misleading metrics

---

### 12. **Delivery Address Not Validated Against City Boundary**
**Location:** `api/models/address.py:30-32`
**Issue:** User can set address outside service area
**Impact:** Orders fail at delivery time

---

### 13. **No Coordinate Validation in bot_message_location**
**Location:** `api/models/message.py:99-109`
**Issue:** Invalid lat/long sent to WhatsApp API
**Impact:** Message failures

---

### 14. **No Idempotency for Orders**
**Location:** `api/services/ai/tool_handlers/order.py`
**Issue:** Double-clicking creates duplicate orders
**Impact:** Accidental double orders
**Fix:** Add idempotency key check

---

### 15. **Meal Availability Uses Server Time Not User Time**
**Location:** `api/models/meal.py:433-455`
**Issue:** `datetime.now().time()` uses UTC not user timezone
**Impact:** Wrong meals shown (1 hour off for Lagos users)

---

### 16. **Transaction Atomic Decorator Wrong Order**
**Location:** `api/views/payment_webhook.py:21`
**Issue:** `@transaction.atomic` might not work with ninja router
**Fix:** Use context manager instead:
```python
def payment_webhook(request):
    with transaction.atomic():
        # ... all logic here ...
```

---

### 17. **Signal Handler Blocks on External API**
**Location:** `api/signals.py:74-193`
**Issue:** Meal save blocked by synchronous AI API call
**Impact:** Meal creation fails if AI API down
**Fix:** Move to background task

---

### 18. **Decimal Precision Not Enforced**
**Location:** `api/models/user_balance.py:54-70`
**Issue:** No rounding, floating point errors accumulate
**Impact:** Penny discrepancies
**Fix:**
```python
balance.amount = (balance.amount + Decimal(str(amount))).quantize(Decimal('0.01'))
```

---

### 19. **Restaurant Deletion Orphans Orders**
**Location:** `api/models/meal.py`
**Issue:** Restaurant cascade delete removes meals, orders become inconsistent
**Fix:** Change to `on_delete=models.PROTECT`

---

## 🟢 LOW SEVERITY / CODE QUALITY

### 20. **More Bare Except Clauses**
**Locations:**
- `api/admin/base.py:49, 233`
- `api/admin/location.py:157`

---

### 21. **Test Endpoints in Production**
**Location:** `api/views/whatsapp_webhook.py:192-254`
**Issue:** Test endpoints exposed
**Fix:** Remove before launch or move to separate router

---

### 22. **Sensitive Data in Logs**
**Multiple files:** `print(response.text)`, `print(request.body)`
**Issue:** Phone numbers, payment info in stdout
**Impact:** Compliance violation
**Fix:** Use proper logging with redaction

---

### 23. **Commented Out Code**
**Location:** `api/models/user.py:31`
**Issue:** Dead code creates confusion

---

### 24. **Silent Failure on Invalid Screen Name**
**Location:** `api/models/message.py:170`
**Issue:** Returns None instead of raising error
**Impact:** Poor debugging

---

### 25. **No Database Indexes**
**Multiple models**
**Issue:** Frequently filtered fields lack indexes
**Fix:** Add indexes:
```python
class Meta:
    indexes = [
        models.Index(fields=['user', 'created_at']),
        models.Index(fields=['paid', 'created_at']),
    ]
```

---

## 📋 PRE-LAUNCH CHECKLIST

### Must Fix (Critical):
- [ ] Fix password hashing (#4)
- [ ] Add stock decrement with atomic lock (#3)
- [ ] Fix referral race condition (#2)
- [ ] Replace all bare except clauses (#1)
- [ ] Add withdrawal limits (#5)

### Should Fix (High):
- [ ] Fix midnight time period bug (#6)
- [ ] Add prefetch_related for meals (#7)
- [ ] Fix partial payment handling (#8)
- [ ] Add null checks for city.currency (#9)
- [ ] Enable duplicate recommendation constraint (#10)

### Before Launch:
- [ ] Remove test endpoints (#21)
- [ ] Fix decimal precision (#18)
- [ ] Add idempotency tokens (#14)
- [ ] Move AI analysis to async task (#17)
- [ ] Add database indexes (#25)
- [ ] Remove debug print statements (#22)
- [ ] Add comprehensive error tracking (Sentry)

### Security:
- [ ] Verify all secrets in environment variables
- [ ] Test webhook signature validation
- [ ] Enable database backups
- [ ] Set up SSL/TLS for all endpoints
- [ ] Review CORS settings
- [ ] Test rate limiting

---

## 🚀 RECOMMENDED FIXES ORDER

1. **Day 1 (Critical Security):**
   - Password hashing
   - Withdrawal validation
   - Stock decrement

2. **Day 2 (Data Integrity):**
   - Referral race condition
   - Partial payment handling
   - Decimal precision

3. **Day 3 (UX & Performance):**
   - Midnight time period
   - N+1 queries
   - Null checks

4. **Day 4 (Code Quality):**
   - Replace bare excepts
   - Remove test endpoints
   - Clean up logging

5. **Day 5 (Testing & Deploy):**
   - Full integration testing
   - Load testing
   - Deploy to staging
   - MVP launch 🎉

---

**Report End** | Questions? Review code at the line numbers above.
