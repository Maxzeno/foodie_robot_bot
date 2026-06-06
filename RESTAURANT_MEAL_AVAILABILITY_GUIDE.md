# Restaurant & Meal Availability System

## Overview

This document describes the comprehensive availability system implemented for restaurants and meals, including business hours, stock management, and time-based availability.

---

## Restaurant Fields

### New Fields Added to `Restaurant` Model

#### 1. **Business Hours**

**`open_time`** (TimeField)
- Default: `06:00`
- Restaurant opening time
- Example: `time(8, 0)` for 8:00 AM

**`close_time`** (TimeField)
- Default: `22:00`
- Restaurant closing time
- Example: `time(22, 30)` for 10:30 PM

**`available_days`** (ArrayField)
- Array of day names when restaurant is open
- Choices: monday, tuesday, wednesday, thursday, friday, saturday, sunday
- Empty array = open all days
- Example: `['monday', 'tuesday', 'wednesday', 'thursday', 'friday']` (weekdays only)

#### 2. **Status**

**`inactive`** (BooleanField)
- Default: `False`
- Set to `True` to disable restaurant and all its meals
- Useful for temporary closures, holidays, maintenance

### New Method: `is_open_now()`

```python
restaurant.is_open_now(current_time=None, current_day=None)
```

**Returns**: `bool` - True if restaurant is currently open

**Checks**:
1. Restaurant is not inactive
2. Current day is in available_days (if specified)
3. Current time is within open_time and close_time

**Usage Example**:
```python
from datetime import time

restaurant = Restaurant.objects.get(name="Joe's Pizza")

# Check if open now
if restaurant.is_open_now():
    print("Restaurant is open!")

# Check if open at specific time
if restaurant.is_open_now(current_time=time(14, 30)):  # 2:30 PM
    print("Open at 2:30 PM")
```

---

## Meal Fields

### New Fields Added to `Meal` Model

#### 1. **Time-Based Availability**

**`available_from_time`** (TimeField, nullable)
- Time when meal becomes available
- Example: `time(6, 0)` for breakfast starting at 6 AM
- `null` = no time restriction

**`available_to_time`** (TimeField, nullable)
- Time when meal stops being available
- Example: `time(11, 0)` for breakfast ending at 11 AM
- `null` = no time restriction

#### 2. **Stock Management**

**`daily_stock_limit`** (IntegerField, nullable)
- Maximum number of this meal that can be ordered per day
- `null` = unlimited stock
- Example: `50` = only 50 portions available per day

**`remaining_stock`** (IntegerField, nullable)
- Current remaining stock for today
- Auto-resets daily via cron job
- Decrements when orders are placed
- `null` = not initialized (treated as available)

### New Methods

#### 1. `is_available_at_time()`

```python
meal.is_available_at_time(check_time=None)
```

**Returns**: `bool` - True if meal is available at the given time

**Usage Example**:
```python
from datetime import time

breakfast = Meal.objects.get(name="Pancakes")
breakfast.available_from_time = time(6, 0)
breakfast.available_to_time = time(11, 0)

# Check if available now
if breakfast.is_available_at_time():
    print("Available now!")

# Check if available at 3 PM
if breakfast.is_available_at_time(time(15, 0)):
    print("Available at 3 PM")  # Won't print - breakfast ends at 11 AM
```

#### 2. `has_stock_available()`

```python
meal.has_stock_available()
```

**Returns**: `bool` - True if stock is available or unlimited

**Logic**:
- If `daily_stock_limit` is `None` → True (unlimited)
- If `remaining_stock` is `None` → True (not initialized yet)
- If `remaining_stock > 0` → True
- Otherwise → False

**Usage Example**:
```python
special = Meal.objects.get(name="Chef's Special")
special.daily_stock_limit = 20
special.remaining_stock = 5

if special.has_stock_available():
    print(f"{special.remaining_stock} portions remaining!")
```

#### 3. `is_fully_available()`

```python
meal.is_fully_available(check_time=None)
```

**Returns**: `bool` - True if meal is fully available for ordering

**Comprehensive Check**:
1. ✓ Meal `available` flag is True
2. ✓ Restaurant is not `inactive`
3. ✓ Restaurant is open (via `restaurant.is_open_now()`)
4. ✓ Meal is available at current time (via `is_available_at_time()`)
5. ✓ Meal has stock available (via `has_stock_available()`)

**Usage Example**:
```python
meal = Meal.objects.get(id=123)

# Single comprehensive check
if meal.is_fully_available():
    # Safe to show to user and accept orders
    print(f"{meal.name} is available for ordering!")
else:
    print(f"{meal.name} is not currently available")
```

---

## Integration with Recommendation System

### Automatic Filtering

Both recommendation services now automatically filter out unavailable meals:

**`MealRecommendationService._get_eligible_meals()`**
**`EmbeddingRecommendationService._get_eligible_meals()`**

**Filters Applied**:
1. ✓ `restaurant__inactive=False` - Only active restaurants
2. ✓ `daily_stock_limit__isnull=True OR remaining_stock__gt=0` - Only meals with stock
3. ✓ Existing filters (allergies, health conditions, budget, etc.)

**What This Means**:
- Recommendations automatically respect restaurant hours
- Out-of-stock meals are excluded
- Inactive restaurants are hidden
- No code changes needed in recommendation calls

---

## Daily Stock Reset Cron Job

### Command: `reset_meal_stock`

**Purpose**: Reset `remaining_stock` to `daily_stock_limit` daily

**Usage**:
```bash
# Run daily stock reset
python manage.py reset_meal_stock

# Dry run (preview without changes)
python manage.py reset_meal_stock --dry-run
```

**Cron Schedule** (Add to your cron/scheduler):
```bash
# Reset stock daily at midnight
0 0 * * * cd /path/to/foodie_robot_backend && python manage.py reset_meal_stock
```

**What It Does**:
1. Finds all meals with `daily_stock_limit` set
2. Resets `remaining_stock = daily_stock_limit`
3. Logs results

**Example Output**:
```
============================================================
Reset Meal Stock - Daily Cron Job
============================================================
Timestamp: 2025-12-02 00:00:00

Found 25 meal(s) with stock tracking enabled

  ✓ Chef's Special: 0 → 20
  ✓ Breakfast Burrito: 15 → 50
  ✓ Lunch Combo: 3 → 30
  ✓ Dinner Special: None → 25
  ✓ Seafood Pasta: 0 → 15
  ... and 20 more

✓ Successfully reset 25 meal(s)
============================================================
```

---

## Admin Interface

### Restaurant Admin

**Fields Available**:
- Name, Phone, Address, Location
- **Business Hours**: Open Time, Close Time, Available Days
- **Status**: Inactive checkbox
- Email, Website, Social Media

**Example Configuration**:
```
Restaurant: Joe's Pizza
Open Time: 10:00
Close Time: 23:00
Available Days: [monday, tuesday, wednesday, thursday, friday, saturday, sunday]
Inactive: [ ] (unchecked = active)
```

### Meal Admin

**Additional Fields**:
- **Time Availability**: Available From Time, Available To Time
- **Stock Management**: Daily Stock Limit, Remaining Stock

**Example Configurations**:

**Breakfast Item**:
```
Meal: Pancake Stack
Available From: 06:00
Available To: 11:00
Daily Stock Limit: 50
Remaining Stock: 50 (auto-managed)
```

**Unlimited Stock Item**:
```
Meal: Margherita Pizza
Available From: (empty)
Available To: (empty)
Daily Stock Limit: (empty)
Remaining Stock: (empty)
```

**Limited Daily Special**:
```
Meal: Chef's Special
Available From: 12:00
Available To: 15:00
Daily Stock Limit: 20
Remaining Stock: 15
```

---

## Use Cases & Examples

### 1. **Breakfast-Only Item**
```python
breakfast_burrito = Meal.objects.create(
    name="Breakfast Burrito",
    restaurant=restaurant,
    city=city,
    price=8.99,
    available_from_time=time(6, 0),   # 6 AM
    available_to_time=time(11, 0),    # 11 AM
    daily_stock_limit=None            # Unlimited
)
```

### 2. **Limited Daily Special**
```python
daily_special = Meal.objects.create(
    name="Chef's Special",
    restaurant=restaurant,
    city=city,
    price=15.99,
    available_from_time=time(12, 0),  # Noon
    available_to_time=time(15, 0),    # 3 PM
    daily_stock_limit=20,             # Only 20 per day
    remaining_stock=20
)
```

### 3. **Weekday-Only Restaurant**
```python
restaurant = Restaurant.objects.create(
    name="Office Lunch Spot",
    open_time=time(11, 0),
    close_time=time(15, 0),
    available_days=['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
)
```

### 4. **Temporarily Close Restaurant**
```python
restaurant = Restaurant.objects.get(name="Joe's Pizza")
restaurant.inactive = True
restaurant.save()

# All meals from this restaurant are now hidden automatically
```

### 5. **Check Meal Availability Before Ordering**
```python
from api.models.meal import Meal

def can_order_meal(meal_id):
    try:
        meal = Meal.objects.get(id=meal_id)

        if not meal.is_fully_available():
            # Determine why it's not available
            if meal.restaurant.inactive:
                return False, "Restaurant temporarily closed"
            if not meal.restaurant.is_open_now():
                return False, f"Restaurant closed (open {meal.restaurant.open_time}-{meal.restaurant.close_time})"
            if not meal.is_available_at_time():
                return False, f"Meal only available {meal.available_from_time}-{meal.available_to_time}"
            if not meal.has_stock_available():
                return False, "Out of stock for today"
            if not meal.available:
                return False, "Meal currently unavailable"

        return True, "Available"

    except Meal.DoesNotExist:
        return False, "Meal not found"
```

---

## Decreasing Stock on Order

### Manual Stock Decrement

When an order is placed, decrement the stock:

```python
from api.models.meal import Meal
from api.models.order import Order

def place_order(meal_id, quantity=1):
    meal = Meal.objects.get(id=meal_id)

    # Check availability
    if not meal.is_fully_available():
        return False, "Meal not available"

    # Check if enough stock
    if meal.daily_stock_limit is not None:
        if meal.remaining_stock is None:
            meal.remaining_stock = meal.daily_stock_limit

        if meal.remaining_stock < quantity:
            return False, f"Only {meal.remaining_stock} remaining"

        # Decrement stock
        meal.remaining_stock -= quantity
        meal.save(update_fields=['remaining_stock'])

    # Create order
    order = Order.objects.create(
        meal=meal,
        quantity=quantity,
        # ... other fields
    )

    return True, order
```

### Recommended: Use Django Signals

Create a signal to automatically decrement stock when orders are paid:

```python
# api/signals.py (add to existing file)

from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models.order import Order

@receiver(post_save, sender=Order)
def decrement_meal_stock_on_paid_order(sender, instance, created, **kwargs):
    """Decrement meal stock when order is paid."""
    # Only decrement for new paid orders
    if created and instance.paid:
        meal = instance.meal

        # Only decrement if meal has stock tracking
        if meal.daily_stock_limit is not None:
            if meal.remaining_stock is None:
                meal.remaining_stock = meal.daily_stock_limit

            # Decrement stock
            meal.remaining_stock = max(0, meal.remaining_stock - instance.quantity)
            meal.save(update_fields=['remaining_stock'])

            print(f"Stock decremented: {meal.name} - Remaining: {meal.remaining_stock}")
```

---

## Migration Details

**Migration**: `0017_meal_available_from_time_meal_available_to_time_and_more.py`

**Changes Applied**:
1. ✓ Added `available_from_time` to Meal (nullable)
2. ✓ Added `available_to_time` to Meal (nullable)
3. ✓ Added `daily_stock_limit` to Meal (nullable)
4. ✓ Added `remaining_stock` to Meal (nullable)
5. ✓ Added `available_days` to Restaurant (default empty array)
6. ✓ Added `close_time` to Restaurant (default 22:00)
7. ✓ Added `inactive` to Restaurant (default False)
8. ✓ Added `open_time` to Restaurant (default 06:00)

**Database Impact**:
- ✓ All fields are nullable or have defaults
- ✓ No data loss
- ✓ Existing restaurants default to 24/7 operation (6 AM - 10 PM, all days)
- ✓ Existing meals have unlimited stock

---

## Testing Checklist

### Restaurant Hours
- [ ] Create restaurant with specific hours
- [ ] Verify `is_open_now()` returns correct value
- [ ] Test with different days of week
- [ ] Test `inactive` flag hides meals

### Meal Availability
- [ ] Create meal with time restrictions
- [ ] Verify `is_available_at_time()` works correctly
- [ ] Test outside availability window

### Stock Management
- [ ] Create meal with stock limit
- [ ] Place order and verify stock decrements
- [ ] Run `reset_meal_stock` and verify reset
- [ ] Test out-of-stock scenario

### Recommendations
- [ ] Run meal recommendation service
- [ ] Verify inactive restaurants excluded
- [ ] Verify out-of-stock meals excluded
- [ ] Verify time-appropriate meals shown

### Admin Interface
- [ ] Edit restaurant hours in admin
- [ ] Set meal stock limits
- [ ] Toggle restaurant inactive status

---

## Monitoring & Maintenance

### Daily Tasks
1. Run `reset_meal_stock` at midnight via cron
2. Monitor stock levels throughout day
3. Check for meals frequently going out of stock

### Weekly Tasks
1. Review restaurant hours accuracy
2. Update meal availability times seasonally
3. Adjust stock limits based on demand

### Monthly Tasks
1. Analyze stock-out patterns
2. Review inactive restaurants
3. Optimize availability windows based on order data

---

## Troubleshooting

### Meals Not Showing in Recommendations

**Check**:
1. Restaurant not inactive: `restaurant.inactive == False`
2. Meal available flag: `meal.available == True`
3. Has stock: `meal.remaining_stock > 0` or `meal.daily_stock_limit == None`
4. Restaurant open: `restaurant.is_open_now() == True`
5. Meal time-available: `meal.is_available_at_time() == True`

**Debug Command**:
```python
from api.models.meal import Meal

meal = Meal.objects.get(id=123)
print(f"Available: {meal.available}")
print(f"Restaurant Inactive: {meal.restaurant.inactive}")
print(f"Restaurant Open: {meal.restaurant.is_open_now()}")
print(f"Time Available: {meal.is_available_at_time()}")
print(f"Has Stock: {meal.has_stock_available()}")
print(f"Fully Available: {meal.is_fully_available()}")
```

### Stock Not Resetting

**Check**:
1. Cron job running: `crontab -l`
2. Command works: `python manage.py reset_meal_stock --dry-run`
3. Meals have `daily_stock_limit` set
4. Check logs for errors

---

## Summary

✅ **Implemented**:
- Restaurant business hours (open_time, close_time, available_days)
- Restaurant inactive status
- Meal time-based availability (available_from_time, available_to_time)
- Meal stock management (daily_stock_limit, remaining_stock)
- Helper methods for availability checks
- Automatic filtering in recommendations
- Daily stock reset cron job
- Database migration

✅ **Benefits**:
- Better inventory management
- Accurate availability display
- Reduced customer disappointment
- Optimized operations
- Automated stock resets

✅ **Next Steps**:
- Set up cron job for daily stock reset
- Configure restaurant hours in admin
- Set stock limits for popular items
- Monitor and adjust based on usage
