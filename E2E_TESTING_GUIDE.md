# End-to-End User Flow Testing Guide

## Overview

This guide explains how to run comprehensive end-to-end tests that simulate real user interactions with the FoodBot system, from onboarding through meal recommendations to order placement.

---

## What Gets Tested

### Flow 1: Onboarding Flow ✅
**User Journey**: New User → Complete Profile

Tests the complete onboarding process:
1. User sends greeting message
2. System asks for fitness goal
3. User provides fitness goal (weight loss, muscle gain, maintenance)
4. System asks for health conditions
5. User provides health conditions (diabetes, hypertension, etc.)
6. System asks for allergies
7. User provides allergies (peanuts, seafood, dairy, etc.)
8. System asks for cuisine preferences
9. User provides cuisine preferences (Nigerian, Italian, etc.)
10. System asks for delivery location
11. User provides delivery address
12. Onboarding marked as complete

**Tests**:
- User profile data is correctly stored
- All preference fields are populated
- Onboarding flow follows correct order
- User can skip optional fields appropriately

---

### Flow 2: Meal Recommendation Flow ✅
**User Journey**: Request → Recommendation → Details

Tests the recommendation system:
1. Completed user requests meal recommendations
2. System analyzes user preferences:
   - Fitness goal (weight loss → healthier options)
   - Health conditions (diabetes → low sugar options)
   - Allergies (peanuts → nut-free meals)
   - Cuisine preferences (Nigerian → appropriate cuisines)
3. System recommends meals matching preferences
4. User views meal details (name, price, restaurant, description)
5. User can accept or decline recommendations

**Tests**:
- Recommendations respect user preferences
- Meal data is correctly retrieved
- Price and availability are accurate
- Multiple recommendations provided

---

### Flow 3: Order Placement Flow ✅
**User Journey**: Select Meal → Confirm → Payment

Tests the complete order process:
1. User selects a meal to order
2. System validates:
   - User has completed onboarding
   - User has delivery location set
   - Meal is available
   - Meal is in user's city
3. Order is created in database
4. Order details are calculated:
   - Meal price
   - Delivery fee
   - Total price
5. Payment link is generated
6. Order confirmation sent to user
7. Payment gateway initialized

**Tests**:
- Order is correctly created
- Pricing is calculated accurately
- Delivery address validation works
- Meal availability is checked
- Payment initialization succeeds
- Order status is PENDING

---

### Flow 4: Order History & Status Flow ✅
**User Journey**: Check History → View Status → Track Delivery

Tests order management:
1. User asks for order history
2. System retrieves all user orders
3. Orders displayed with pagination (3 per page)
4. User can check specific order status:
   - Pending (⏳ Being prepared)
   - Dispatched (🚗 On the way)
   - Arrived (📍 Has arrived)
   - Received (✅ Completed)
5. User can see order details:
   - Meal name and price
   - Total cost
   - Payment status
   - Delivery address
6. User can request more orders

**Tests**:
- All user orders retrieved correctly
- Order status is accurate
- Payment status is correct
- Order history pagination works
- Order details display properly

---

### Flow 5: Error Scenarios & Edge Cases ✅
**Tests**: Exception Handling

Tests how system handles errors:

#### Scenario 1: Order Without Delivery Address
- User tries to order without setting location
- System rejects gracefully
- User prompted to set delivery address

#### Scenario 2: Unavailable Meal
- User tries to order out-of-stock meal
- System rejects order
- Alternative meal suggestions provided

#### Scenario 3: Incomplete Profile
- User requests recommendations with incomplete profile
- System asks for missing information
- Continues onboarding flow

#### Scenario 4: Location Mismatch
- User's delivery address is outside service area
- System rejects order
- User prompted to update location

---

## Running the Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-django

# Ensure Django settings are configured
export DJANGO_SETTINGS_MODULE=foodie_robot_backend.settings
```

### Run All Tests

```bash
# Basic run
pytest test_e2e_user_flows.py -v

# Run with detailed output (includes print statements)
pytest test_e2e_user_flows.py -v -s

# Run specific test class
pytest test_e2e_user_flows.py::TestOnboardingFlow -v -s

# Run specific test method
pytest test_e2e_user_flows.py::TestOnboardingFlow::test_onboarding_complete_flow -v -s
```

### Run Specific Flows

```bash
# Onboarding only
pytest test_e2e_user_flows.py::TestOnboardingFlow -v -s

# Meal Recommendation only
pytest test_e2e_user_flows.py::TestMealRecommendationFlow -v -s

# Order Placement only
pytest test_e2e_user_flows.py::TestOrderPlacementFlow -v -s

# Order History only
pytest test_e2e_user_flows.py::TestOrderHistoryFlow -v -s

# Error Scenarios only
pytest test_e2e_user_flows.py::TestErrorScenarios -v -s

# Complete Journey
pytest test_e2e_user_flows.py::TestCompleteUserJourney -v -s
```

### Run with Coverage

```bash
pip install pytest-cov
pytest test_e2e_user_flows.py --cov=api --cov-report=html -v
open htmlcov/index.html
```

---

## Understanding Test Output

### Successful Test Output

```
test_e2e_user_flows.py::TestOnboardingFlow::test_onboarding_complete_flow PASSED [10%]

======================================================================
TEST: Complete Onboarding Flow
======================================================================

[STEP 1] User sends greeting
✓ Created user message: Hi, I'm new here!

[STEP 2] Handler processes greeting and asks for fitness goal
✓ Created FoodBotAIHandler for user 2348044467200

[STEP 3] User responds with fitness goal
✓ Fitness goal saved: True
  User fitness goal: weight_loss

...

[FINAL] Onboarding Complete!
======================================================================
✓ Fitness Goal: weight_loss
✓ Health Conditions: diabetes
✓ Allergies: peanuts
✓ Cuisine Preferences: nigerian
✓ City: Lagos
======================================================================
```

### Test Results Summary

```
======================== 6 passed in 45.23s ========================

TestOnboardingFlow::test_onboarding_complete_flow .................... PASSED
TestMealRecommendationFlow::test_meal_recommendation_flow ............ PASSED
TestOrderPlacementFlow::test_order_placement_flow .................... PASSED
TestOrderHistoryFlow::test_order_history_flow ........................ PASSED
TestErrorScenarios::test_order_without_delivery_address .............. PASSED
TestCompleteUserJourney::test_complete_journey_from_start_to_order ... PASSED
```

---

## Test Data Setup

### Automatic Data Creation

The test suite automatically creates:

**User Data**:
- Test user with phone number
- User profile with all fields

**Preference Data**:
- Fitness goals: Weight Loss, Muscle Gain, Maintenance
- Health conditions: Diabetes, Hypertension, etc.
- Allergies: Peanuts, Seafood, Dairy, etc.
- Cuisine types: Nigerian, Italian, French, etc.

**Location Data**:
- City: Lagos, Nigeria (WAT timezone)
- Currency: Nigerian Naira (₦)
- Coordinates: 3.1357°N, 6.6882°E

**Meal Data**:
- Test restaurant: "Test Restaurant"
- Sample meal: "Jollof Rice" (₦2,500)
- Availability: Available in afternoon
- Time of day: Afternoon (12 PM - 5 PM)

**Order Data**:
- Meal price: ₦2,500
- Delivery fee: ₦500
- Total: ₦3,000
- Status: Pending → Dispatched → Received

---

## Interpreting Results

### Test Passes ✅

Indicates:
- User flow completed successfully
- Database transactions committed
- Data validation passed
- Business logic executed correctly

### Test Fails ❌

Check the error message:

```
AssertionError: assert user.fitness_goals is None
```

Indicates:
- User preference not saved correctly
- Tool handler failed silently
- Database connection issue
- Logic error in preference saving

### Common Issues

#### Issue: "User" table doesn't exist
**Cause**: Django migrations not run
**Fix**:
```bash
python manage.py migrate
```

#### Issue: "No City found"
**Cause**: Test data not created
**Fix**: Tests auto-create data, but check database connection

#### Issue: "Message.DoesNotExist"
**Cause**: Message not created before querying
**Fix**: Verify message creation in setUp

---

## Test Metrics & Reporting

### Metrics Collected

Each test reports:

1. **Time Taken**
   ```
   [STEP 1] User sends greeting - 0.23s
   [STEP 2] Handler processes - 1.45s
   Total: 2.1s
   ```

2. **Data Validation**
   ```
   ✓ Fitness goal saved
   ✓ Health conditions: 1
   ✓ Allergies: 1
   ✓ Cuisine preferences: 1
   ```

3. **API Calls**
   ```
   ✓ Meal recommendation API: 1 call
   ✓ Order placement API: 1 call
   ✓ Payment gateway: 1 call (mocked)
   ```

4. **Database Operations**
   ```
   ✓ Users created: 1
   ✓ Orders created: 1
   ✓ Messages created: 2
   ✓ Total DB queries: 15
   ```

---

## Performance Baselines

### Expected Test Execution Times

```
Onboarding Flow .......................... 2-3 seconds
Meal Recommendation Flow ................ 1-2 seconds
Order Placement Flow .................... 1-2 seconds
Order History Flow ...................... 1-2 seconds
Error Scenarios ......................... 0.5-1 second
Complete Journey ........................ 3-5 seconds
────────────────────────────────────────────────
TOTAL .................................. 10-15 seconds
```

### Performance Limits

- Single user flow: < 5 seconds ✅
- All flows together: < 20 seconds ✅
- Database queries per flow: < 30 queries ✅

---

## Extending the Tests

### Adding New Test Scenarios

```python
class TestNewScenario(TransactionTestCase):
    """Test new user scenario"""

    def setUp(self):
        """Setup test data"""
        self.user = TestDataSetup.create_test_user()
        self.city = TestDataSetup.create_test_city()

    def test_new_scenario(self):
        """Test the scenario"""
        print("\n[SCENARIO] Description")

        # Test code here
        print("✓ Something happened")

        # Assertions
        assert condition, "Error message"
```

### Adding Custom Assertions

```python
def test_meal_price_calculation(self):
    """Test price calculation"""
    meal_price = Decimal('2500.00')
    delivery_fee = Decimal('500.00')
    total = meal_price + delivery_fee

    assert total == Decimal('3000.00'), "Price calculation incorrect"
    assert meal_price > Decimal('0'), "Meal price should be positive"
```

---

## Troubleshooting

### Tests Fail with "No fixtures found"

**Issue**: Django can't find test fixtures

**Solution**:
```bash
# Ensure migrations are run
python manage.py migrate

# Run with specific settings
DJANGO_SETTINGS_MODULE=foodie_robot_backend.settings pytest test_e2e_user_flows.py
```

### Tests Timeout After 30 seconds

**Cause**: Long-running database queries or API calls

**Solution**:
```bash
# Run with longer timeout
pytest test_e2e_user_flows.py --timeout=60
```

### "User already exists" errors

**Cause**: Test data not cleaned up

**Solution**: Tests use TransactionTestCase which rolls back, ensure:
```python
def tearDown(self):
    """Clean up if needed"""
    Message.objects.filter(user=self.user).delete()
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_DB: foodbot_test
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres

    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: 3.9

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-django pytest-cov

    - name: Run migrations
      run: python manage.py migrate

    - name: Run E2E tests
      run: pytest test_e2e_user_flows.py -v

    - name: Generate report
      run: pytest test_e2e_user_flows.py --cov=api --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## Best Practices

1. **Isolation**: Each test creates its own user and data
2. **Clarity**: Print statements explain what's happening
3. **Cleanup**: TransactionTestCase auto-rolls back
4. **Assertions**: Verify critical steps
5. **Documentation**: Each test explains expected flow

---

## Next Steps

1. **Run tests**: `pytest test_e2e_user_flows.py -v -s`
2. **Review output**: Check that all flows pass
3. **Fix issues**: Address any failures
4. **Generate report**: Collect metrics and results
5. **Monitor**: Set up CI/CD to run continuously

---

## Questions?

- **"How do I run a specific test?"** → See "Run Specific Flows" section
- **"What data is created?"** → See "Test Data Setup" section
- **"Test failed, what do I do?"** → See "Troubleshooting" section
- **"How do I add more tests?"** → See "Extending the Tests" section

