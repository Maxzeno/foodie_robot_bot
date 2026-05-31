from typing import Dict
from decimal import Decimal

from api.models.user import User
from api.models.meal_preference import MealPreference
from api.models.message import Message


def get_user_profile(user: User) -> Dict:
    try:
        # Get fitness goal
        fitness_goal = user.fitness_goals.get_name_display() if user.fitness_goals else "Not set"

        # Get health conditions
        health_conditions = [hc.get_name_display() for hc in user.health_conditions.all()]
        health_conditions_str = ", ".join(health_conditions) if health_conditions else "None"

        # Get allergies
        allergies = [a.get_name_display() for a in user.allergies.all()]
        allergies_str = ", ".join(allergies) if allergies else "None"

        # Get preferred cuisines
        cuisines = [c.get_name_display() for c in user.preferred_cuisine.all()]
        cuisines_str = ", ".join(cuisines) if cuisines else "Not set"

        # Get budget info
        city_name = user.city.name if user.city else "Not set"
        currency_symbol = user.city.currency.symbol if user.city else ""
        budget_str = f"{currency_symbol}{user.average_meal_budget:,.2f}" if user.average_meal_budget else "Not set"

        message = f"""
👤 Your Profile

🎯 Fitness Goal: {fitness_goal}

⚕️ Health Conditions: {health_conditions_str}

🚫 Allergies: {allergies_str}

🍽️ Preferred Cuisines: {cuisines_str}

💰 Average Meal Budget: {budget_str}

📍 Location: {city_name}

You can update any of these by saying things like:
• "Update my budget to <amount>"
• "Change my fitness goal"
• "Update my allergies"
""".strip()

        Message.bot_message(message, user=user)

        return True

    except Exception as e:
        print(f"Error getting user profile: {e}")
        Message.bot_message(
            "Sorry, something went wrong while retrieving your profile. Please try again.",
            user=user
        )
        return False


def update_average_budget(user: User, budget_amount: float) -> Dict:
    try:
        if budget_amount <= 0:
            Message.bot_message(
                "Please provide a valid budget amount greater than 0.",
                user=user
            )
            return False

        # Check if user has a city set
        if not user.city:
            Message.bot_message_request_location(
                "Please set your delivery location first before setting a budget.",
                user=user
            )
            return False

        # Update budget
        user.average_meal_budget = Decimal(str(budget_amount))
        user.save()

        currency_symbol = user.city.currency.symbol
        currency_code = user.city.currency.code

        message = f"""
✅ Budget updated successfully!

Your average meal budget is now set to:
💰 {currency_symbol}{budget_amount:,.2f} {currency_code}

We'll use this to recommend meals within your budget.
Note: Your currency is set to {currency_code} based on your delivery location.
""".strip()

        Message.bot_message(message, user=user)

        return True

    except Exception as e:
        print(f"Error updating budget: {e}")
        Message.bot_message(
            "Sorry, something went wrong while updating your budget. Please try again.",
            user=user
        )
        return False


def get_user_meal_preferences(user: User, is_liked: bool, page: int=1) -> Dict:
    try:
        limit: int = 3
        offset = (page - 1) * limit
        meal_preferences = MealPreference.objects.filter(
            user=user,
            preference='like' if is_liked else 'hate'
        ).select_related('meal', 'meal__restaurant')[offset:offset + limit]

        if not meal_preferences.exists():
            if  page == 1:
                Message.bot_message(
                    f"You haven't {'liked' if is_liked else 'disliked'} any meals yet. Start exploring meals and let us know what you think!" ,
                    user=user
                )
            else:
                Message.bot_message(
                    f"You have no more {'liked' if is_liked else 'disliked'} meals to show.",
                    user=user
                )

            return False

        message = f"🍽️ Your Meal Preferences (Page {page}):\n\n"

        # Add liked meals
        if meal_preferences.exists():
            message += f"Meals You {'liked' if is_liked else 'disliked'}:\n"
            for i, pref in enumerate(meal_preferences, 1):
                meal = pref.meal
                message += f"{i}. {meal.name}\n"
            message += "\n"

        message += "We use these preferences to improve your recommendations!"

        Message.bot_message_action_reply_simple(message.strip(), user=user, action_replies=[f'Page {page + 1}'])

        return True

    except Exception as e:
        print(f"Error getting meal preferences: {e}")
        Message.bot_message(
            "Sorry, something went wrong while retrieving your preferences. Please try again.",
            user=user
        )
        return False
