# AI Tool Handlers Needed for Launch

These are the tool handlers that need to be added to `api/services/ai/tool_handlers/` and registered in `api/services/ai/tool_definitions.py` for the LLM to call based on user prompts.

---

## ✅ Already Implemented Tool Handlers

1. **save_fitness_goal** - Save user's fitness goal
2. **save_health_conditions** - Save user's health conditions
3. **save_allergies** - Save user's food allergies
4. **save_cuisine_preferences** - Save user's preferred cuisines
5. **save_delivery_location** - Save user's delivery location with coordinates
6. **request_delivery_location** - Request user to share location via WhatsApp
7. **generate_meal_recommendations** - Generate personalized meal recommendations for time of day
8. **get_nutritional_info** - Get detailed nutritional information for a meal
9. **like_or_hate_meal** - Like or hate a meal for future recommendations

---

## 🔴 CRITICAL - Order Management Tools (Must-Have for Launch)

### 1. **place_order**
- **Description**: Place an order for a meal with specified quantity
- **Parameters**:
  - `meal_id` (integer, required) - ID of the meal to order
  - `quantity` (integer, required) - Number of plates (default: 1)
  - `delivery_address_id` (integer, optional) - Specific delivery address, defaults to user's default address
  - `special_instructions` (string, optional) - Special requests/notes for the order
- **Returns**: Order confirmation with order_id, total price, estimated delivery time, payment link

### 2. **get_order_status**
- **Description**: Check the status of a specific order or get the latest order status
- **Parameters**:
  - `order_id` (integer, optional) - Specific order ID, if not provided returns latest order
- **Returns**: Order status (pending, dispatched, arrived, received), estimated delivery time, restaurant details

### 3. **get_order_history**
- **Description**: View user's past orders
- **Parameters**:
  - `limit` (integer, optional) - Number of recent orders to return (default: 10)
- **Returns**: List of past orders with meal names, dates, prices, statuses

### 4. **reorder_meal**
- **Description**: Reorder a meal from previous orders
- **Parameters**:
  - `order_id` (integer, required) - ID of the previous order to reorder
- **Returns**: New order confirmation with updated pricing

### 5. **cancel_order**
- **Description**: Cancel a pending order
- **Parameters**:
  - `order_id` (integer, required) - ID of the order to cancel
- **Returns**: Cancellation confirmation and refund status if applicable

---

## 🟡 HIGH PRIORITY - Search & Discovery Tools

### 6. **search_meals**
- **Description**: Search for meals by name, cuisine, or ingredients
- **Parameters**:
  - `query` (string, required) - Search term
  - `cuisine` (string, optional) - Filter by specific cuisine type
  - `max_price` (number, optional) - Maximum price filter
  - `time_of_day` (string, optional) - Filter by time of day (morning, afternoon, evening)
- **Returns**: List of matching meals with names, prices, descriptions, images

### 7. **browse_meals_by_cuisine**
- **Description**: Browse all available meals for a specific cuisine
- **Parameters**:
  - `cuisine_type` (string, required) - Type of cuisine (nigerian, italian, chinese, etc.)
  - `time_of_day` (string, optional) - Filter by meal time
- **Returns**: List of meals in that cuisine category

### 8. **get_meal_details**
- **Description**: Get complete details about a specific meal (different from nutritional info)
- **Parameters**:
  - `meal_id` (integer, required) - ID of the meal
- **Returns**: Full meal details including price, restaurant, ingredients, availability, reviews

---

## 🟡 HIGH PRIORITY - Address Management Tools

### 9. **get_delivery_addresses**
- **Description**: View all saved delivery addresses
- **Parameters**: None
- **Returns**: List of saved addresses with IDs, names (Home, Work), street addresses, default flag

### 10. **update_delivery_address**
- **Description**: Update an existing delivery address name or set as default
- **Parameters**:
  - `address_id` (integer, required) - ID of the address to update
  - `name` (string, optional) - New name for the address
  - `set_as_default` (boolean, optional) - Set this as default address
- **Returns**: Confirmation of address update

### 11. **delete_delivery_address**
- **Description**: Delete a saved delivery address
- **Parameters**:
  - `address_id` (integer, required) - ID of the address to delete
- **Returns**: Confirmation of deletion

---

## 🟢 MEDIUM PRIORITY - Preference Management Tools

### 12. **get_user_profile**
- **Description**: View user's current profile and preferences
- **Parameters**: None
- **Returns**: User's fitness goals, health conditions, allergies, cuisine preferences, average budget, delivery location

### 13. **update_average_budget**
- **Description**: Update user's average meal budget
- **Parameters**:
  - `budget_amount` (number, required) - New average budget per meal
- **Returns**: Confirmation of budget update

### 14. **refresh_recommendations**
- **Description**: Get new meal recommendations if user doesn't like current ones
- **Parameters**:
  - `time_of_day` (string, optional) - Specific time period, defaults to current time
- **Returns**: New set of 2 meal recommendations

---

## 🟢 MEDIUM PRIORITY - Social & Feedback Tools

### 15. **rate_meal**
- **Description**: Rate a meal after ordering/delivery
- **Parameters**:
  - `order_id` (integer, required) - ID of the order
  - `rating` (integer, required) - Rating from 1-5 stars
  - `review_text` (string, optional) - Written review
- **Returns**: Confirmation of rating submission

### 16. **get_meal_reviews**
- **Description**: View reviews for a specific meal
- **Parameters**:
  - `meal_id` (integer, required) - ID of the meal
  - `limit` (integer, optional) - Number of reviews to return (default: 5)
- **Returns**: List of reviews with ratings and comments

---

## 🔵 LOWER PRIORITY - Advanced Features

### 17. **calculate_meal_price**
- **Description**: Calculate total price for a meal order including delivery
- **Parameters**:
  - `meal_id` (integer, required) - ID of the meal
  - `quantity` (integer, optional) - Number of plates (default: 1)
  - `delivery_address_id` (integer, optional) - Address for delivery fee calculation
- **Returns**: Price breakdown (meal price, markup, delivery fee, total)

### 18. **check_meal_availability**
- **Description**: Check if a meal is currently available for ordering
- **Parameters**:
  - `meal_id` (integer, required) - ID of the meal
- **Returns**: Availability status and estimated availability time if not available

### 19. **apply_promo_code**
- **Description**: Apply a promotional discount code to an order
- **Parameters**:
  - `promo_code` (string, required) - Promo code to apply
  - `meal_id` (integer, optional) - Meal to check promo validity for
- **Returns**: Discount amount and updated price

### 20. **get_daily_nutrition_summary**
- **Description**: Get summary of nutrition from meals ordered today
- **Parameters**: None
- **Returns**: Total calories, protein, carbs, fats consumed today

### 21. **contact_support**
- **Description**: Create a support ticket or request human assistance
- **Parameters**:
  - `issue_type` (string, required) - Type of issue (order_issue, payment_problem, general_inquiry)
  - `message` (string, required) - Description of the issue
  - `order_id` (integer, optional) - Related order if applicable
- **Returns**: Support ticket ID and confirmation message

---

## Implementation Priority

### Phase 1: MVP Launch (Week 1-2)
**Must implement these first:**
1. place_order
2. get_order_status
3. cancel_order
4. get_delivery_addresses
5. calculate_meal_price (needed before placing orders)

### Phase 2: Essential UX (Week 3)
**Add these next:**
6. get_order_history
7. reorder_meal
8. search_meals
9. get_meal_details
10. update_delivery_address
11. delete_delivery_address

### Phase 3: Enhancement (Week 4)
**Nice to have before launch:**
12. refresh_recommendations
13. browse_meals_by_cuisine
14. get_user_profile
15. update_average_budget
16. rate_meal

### Phase 4: Post-Launch
**Can be added later:**
17. get_meal_reviews
18. check_meal_availability
19. apply_promo_code
20. get_daily_nutrition_summary
21. contact_support

---

## Next Steps

For each tool handler you need to:

1. **Create the handler function** in `api/services/ai/tool_handlers/` (e.g., `order.py`)
   - Function signature: `def function_name(user: User, **kwargs) -> Dict`
   - Return dictionary with success/failure and relevant data
   - Handle exceptions and send appropriate WhatsApp messages

2. **Add tool definition** in `api/services/ai/tool_definitions.py`
   - Define function name, description, parameters with types and enums
   - Follow OpenAI function calling format

3. **Register handler** in `api/services/ai/orchestrator.py`
   - Map tool name to handler function
   - Ensure proper error handling

4. **Test the tool** with actual WhatsApp messages to verify LLM can call it properly
