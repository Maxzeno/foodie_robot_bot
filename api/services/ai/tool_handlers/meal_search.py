from typing import Dict
from django.db.models import Q

from api.models.user import User
from api.models.meal import Meal
from api.models.message import Message


def search_meals(user: User, query: str) -> bool:
    limit: int = 5
    try:
        if not query or len(query.strip()) == 0:
            Message.bot_message(
                "Please provide a meal name to search for.",
                user=user
            )
            return False

        # Search by name (case insensitive)
        meals = Meal.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            available=True
        )

        # Filter by user's city if available
        if user.city:
            meals = meals.filter(city=user.city)

        meals = meals[:limit]

        if not meals.exists():
            Message.bot_message(
                f"No meals found matching '{query}'. Try searching with different keywords.",
                user=user
            )
            return False

        # Format message
        currency_symbol = user.city.currency.symbol if user.city else ""
        message = f"🔍 Search results for '{query}':\n\n"

        for i, meal in enumerate(meals, 1):
            cuisines = ", ".join([c.get_name_display() for c in meal.cuisine.all()[:2]])
            time_of_day = ", ".join([t.title() for t in meal.times_of_day[:2]])

            message += f"""
{i}. {meal.name}
   💰 {currency_symbol}{meal.price:,.2f}
   🍽️ {cuisines if cuisines else 'Various'}
   📝 {meal.description[:80]}{'...' if len(meal.description) > 80 else ''}

""".strip() + "\n\n"

        message += "\nSay 'get details for meal [number]' or 'order [meal name]' to continue."

        Message.bot_message(message.strip(), user=user)

        return True

    except Exception as e:
        print(f"Error searching meals: {e}")
        Message.bot_message(
            "Sorry, something went wrong while searching for meals. Please try again.",
            user=user
        )
        return False


def get_meal_details(user: User, meal_id: int) -> bool:
    """
    Get complete details about a specific meal.
    """
    try:
        try:
            meal = Meal.objects.get(id=meal_id)
        except Meal.DoesNotExist:
            Message.bot_message(
                f"Meal not found. Please check the meal ID and try again.",
                user=user
            )
            return False

        # Format message
        currency_symbol = meal.city.currency.symbol

        # Get cuisines
        cuisines = ", ".join([c.get_name_display() for c in meal.cuisine.all()])

        # Get times of day
        times_of_day = ", ".join([t.title() for t in meal.times_of_day])

        # Get fitness goals
        fitness_goals = ", ".join([fg.get_name_display() for fg in meal.fitness_goals.all()])

        # Get restrictions
        restricted_allergies = [a.get_name_display() for a in meal.restricted_allergies.all()]
        restricted_conditions = [hc.get_name_display() for hc in meal.restricted_health_conditions.all()]

        message = f"""
🍽️ {meal.name}

📝 Description:
{meal.description}

💰 Price: {currency_symbol}{meal.price:,.2f}
📍 Available in: {meal.city.name}
⏰ Meal times: {times_of_day if times_of_day else 'Anytime'}
🍽️ Cuisine: {cuisines if cuisines else 'Various'}
{'✅ Available' if meal.available else '❌ Currently unavailable'}

🎯 Fitness Goals: {fitness_goals if fitness_goals else 'All goals'}
""".strip()

        # Add nutrition info if available
        if meal.calories:
            message += f"""
\n
📊 Nutrition (per serving):
• Calories: {float(meal.calories):.0f} kcal
• Protein: {float(meal.protein):.1f}g
• Carbs: {float(meal.carbs):.1f}g
• Fats: {float(meal.fats):.1f}g
""".strip() if meal.protein else f"\n\n📊 Nutrition: {float(meal.calories):.0f} kcal per serving"

        # Add restrictions if any
        if restricted_allergies or restricted_conditions:
            message += "\n\n⚠️ Not suitable for:"
            if restricted_allergies:
                message += f"\n• Allergies: {', '.join(restricted_allergies)}"
            if restricted_conditions:
                message += f"\n• Conditions: {', '.join(restricted_conditions)}"

        message += "\n\nSay 'order this meal' to place an order!"

        Message.bot_message(message.strip(), user=user)

        return True

    except Exception as e:
        print(f"Error getting meal details: {e}")
        Message.bot_message(
            "Sorry, something went wrong while retrieving meal details. Please try again.",
            user=user
        )
        return False
