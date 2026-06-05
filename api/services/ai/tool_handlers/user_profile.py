
from api.models.user import User
from api.models.meal_preference import MealPreference
from api.models.message import Message
from api.models.meal import FitnessGoal, PreferredCuisine, HealthCondition, Allergy
from api.utils.whatsapp_payload_helper.user_profile_flow_data import user_data_profile_flow


def update_user_profile(
    user: User, fitness_goal: str, health_conditions: list=[], allergies_diet: list=[],
    preferred_cuisines: list=[], meal_budget: float=None) -> bool:
    is_new = user.city is None

    try:
        if fitness_goal:
            fitness_goal_obj = FitnessGoal.objects.filter(id=fitness_goal).first()
            if fitness_goal_obj:
                user.fitness_goals = fitness_goal_obj

        if health_conditions:
            health_condition_objs = HealthCondition.objects.filter(id__in=health_conditions)
            user.health_conditions.set(health_condition_objs)

        if allergies_diet:
            allergy_objs = Allergy.objects.filter(id__in=allergies_diet)
            user.allergies.set(allergy_objs)

        if preferred_cuisines:
            cuisine_objs = PreferredCuisine.objects.filter(id__in=preferred_cuisines)
            user.preferred_cuisine.set(cuisine_objs)

        if meal_budget is not None:
            user.average_meal_budget = meal_budget

        user.save()

        
        if is_new:
            Message.bot_message_request_location("Your profile has been created successfully! Please click the button below to send us your delivery location so we can start sending you meal recommendations.", user=user)
        else:
            Message.bot_message(
                "Your profile has been updated successfully!",
                user=user
            )

        return True

    except Exception as e:
        print(f"Error updating user profile: {e}")
        Message.bot_message(
            "Sorry, something went wrong while updating your profile. Please try again.",
            user=user
        )
        return False


def get_update_user_profile_form(user: User) -> bool:
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

# TODO: Send it as flow message incase they want to update it
        message = f"""
👤 Your Profile

🎯 Fitness Goal: {fitness_goal}

⚕️ Health Conditions: {health_conditions_str}

🚫 Allergies: {allergies_str}

🍽️ Preferred Cuisines: {cuisines_str}

💰 Average Meal Budget: {budget_str}

📍 Location: {city_name}

""".strip()

        Message.bot_message_flow(
            message, 
            user=user,
            flow_cta="Update profile", 
            flow_id="1822264872503617", 
            screen_name="USER_PROFILE",
            data=user_data_profile_flow(user),
            )

        return True

    except Exception as e:
        print(f"Error getting user profile: {e}")
        Message.bot_message(
            "Sorry, something went wrong while retrieving your profile. Please try again.",
            user=user
        )
        return False


def get_user_meal_preferences(user: User, filter_by: str=None, page: int=1) -> bool:
    try:
        limit: int = 3
        offset = (page - 1) * limit

        
        if filter_by is None:
            Message.bot_message_action_reply_simple(
                "Would you like to view your liked or disliked meal preferences?",
                user=user,
                action_replies=['Liked', 'Disliked']
            ) 
            return False
        
        if filter_by.lower() not in ['liked', 'disliked']:
            Message.bot_message_action_reply_simple(
                "Invalid filter option. Please choose 'liked' or 'disliked'.",
                user=user,
                action_replies=['Liked', 'Disliked']
            )
            return False

        is_liked = filter_by.lower() == 'liked'
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
