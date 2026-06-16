from django.conf import settings
from api.models.message import Message
from api.models.user import User
from api.models.meal import Meal, TimeOfDayChoices
from api.models.recommendation import Recommendation, ChoiceOption
from api.services.recommendation.meal_recommendation import MealRecommendationService
from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload
from api.utils.whatsapp_payload_helper.no_recommendation import (
    get_no_recommendation_message,
    should_show_profile_update_flow
)
from api.utils.whatsapp_payload_helper.user_profile_flow_data import user_data_profile_flow
from django.db import transaction


def format_engaging_recommendation_message(
    user: User,
    meal: Meal,
    choice_option: str,
    time_of_day: str,
    currency_symbol: str = "₦"
) -> str:
    day_number = user.get_recommendation_day_number()
    streak = user.get_recommendation_streak()

    # Time of day greeting variations
    time_greetings = {
        'morning': 'Breakfast time',
        'afternoon': 'Lunch time',
        'evening': 'Dinner time'
    }

    # Get greeting based on time
    greeting = time_greetings.get(time_of_day, 'Your pick')

    # Choice ordinal
    choice_text = "1st" if choice_option.lower() == 'first' else "2nd"

    # Build the message
    lines = []

    # Day header with milestone celebrations
    if day_number == 1:
        lines.append(f"*Day {day_number}* - Welcome to your food journey!")
    elif day_number == 7:
        lines.append(f"*Day {day_number}* - One week of great meals!")
    elif day_number == 30:
        lines.append(f"*Day {day_number}* - A month of delicious discoveries!")
    elif day_number == 100:
        lines.append(f"*Day {day_number}* - 100 days! You're a foodie legend!")
    elif day_number % 10 == 0:
        lines.append(f"*Day {day_number}* - Keep the streak going!")
    else:
        lines.append(f"*Day {day_number}*")

    # Streak bonus message (if streak > 1)
    if streak > 1:
        if streak >= 7:
            lines.append(f"*{streak}-day streak* - You're on fire!")
        else:
            lines.append(f"*{streak}-day streak*")

    lines.append("")  # Empty line for spacing

    # Main recommendation
    lines.append(f"{greeting}! Here's your {choice_text} pick:")
    lines.append("")
    lines.append(f"*{meal.name}*")
    lines.append(f"*{currency_symbol}{meal.price:,.0f}*")

    return "\n".join(lines)


def build_meal_recommendation(user: User) -> bool:
    """
    Build and send meal recommendations to the user.

    Returns:
        bool: True if recommendations were sent, False if no meals available
    """
    with transaction.atomic():
        service = MealRecommendationService()

        recommended_meal_map = service.get_recommendations(
            user=user,
            num_recommendations_per_period=2,
        )

        # Check if no meals are available
        no_results_reason = recommended_meal_map.get('no_results_reason')
        current_period = user.get_time_period()
        current_period_meals = recommended_meal_map.get(current_period, [])

        if not current_period_meals and no_results_reason:
            # Send explanation message to user
            currency_symbol = "₦"
            if user.city and user.city.currency:
                currency_symbol = user.city.currency.symbol

            message_text = get_no_recommendation_message(no_results_reason, currency_symbol)
            primary_reason = no_results_reason.get('primary_reason', 'unknown')

            # Check if profile update can help fix this issue
            if should_show_profile_update_flow(primary_reason):
                # Send message with profile update flow button
                Message.bot_message_flow(
                    content=message_text,
                    user=user,
                    flow_cta="Update profile",
                    flow_id=settings.WHATSAPP_FLOW_USER_PROFILE,
                    screen_name="USER_PROFILE",
                    data=user_data_profile_flow(user),
                )
            else:
                # Send regular text message
                Message.bot_message(
                    content=message_text,
                    user=user,
                    metadata={
                        "type": "no_recommendation",
                        "reason": primary_reason
                    }
                )
            return False

        # Get currency symbol for message formatting
        currency_symbol = "₦"
        if user.city and user.city.currency:
            currency_symbol = user.city.currency.symbol

        messages_sent = 0
        for period, recommended_meals_list in recommended_meal_map.items():
            # Skip the no_results_reason key (it's not a time period)
            if period == 'no_results_reason':
                continue

            recommended_meals = Meal.objects.filter(id__in=recommended_meals_list)
            for index, meal in enumerate(recommended_meals):
                choice_option = 'first' if index == 0 else 'second'

                recomendation_obj = Recommendation.objects.create(
                    user=user,
                    meal=meal,
                    time_of_day=TimeOfDayChoices.get_period(period),
                    choice_option=ChoiceOption.FIRST if index == 0 else ChoiceOption.SECOND,
                    sent_to_user=True if user.get_time_period() == period else False,
                    day=user.get_local_time()
                )

                meal_id = str(meal.id)

                if user.get_time_period() == period:
                    # Use engaging message format
                    text = format_engaging_recommendation_message(
                        user=user,
                        meal=meal,
                        choice_option=choice_option,
                        time_of_day=period,
                        currency_symbol=currency_symbol
                    )
                    payload = recommend_product_payload(text, meal)

                    Message.bot_message_action_reply(text, user,
                        payload=payload,
                        metadata={
                            "meal_id": meal_id,
                            "recomendation_id": recomendation_obj.id,
                            "description": "Users can order, like or hate meal"
                            }
                    )
                    messages_sent += 1

        return messages_sent > 0

def meal_recommendations(
    user: User,
) -> bool:
    """
    Get meal recommendations for the user.

    Returns:
        bool: True if recommendations were sent, False otherwise
    """
    time_of_day = user.get_time_period()

    # Check if it's night time - no recommendations during night
    if time_of_day == 'night':
        Message.bot_message(
            content="It's currently night time. Meal recommendations are not available during this period. Please check back in the morning for breakfast recommendations!",
            user=user,
        )
        return False

    try:
        # Check for existing recommendations first
        found_recommendations = Recommendation.objects.filter(
            user=user,
            time_of_day=time_of_day,
            day=user.get_local_time()
        )[:2]
        found_recommendations = list(found_recommendations)[::-1]

        if found_recommendations:
            # Get currency symbol for message formatting
            currency_symbol = "₦"
            if user.city and user.city.currency:
                currency_symbol = user.city.currency.symbol

            for recom in found_recommendations:
                meal = recom.meal
                # Use engaging message format
                text = format_engaging_recommendation_message(
                    user=user,
                    meal=meal,
                    choice_option=recom.choice_option.lower(),
                    time_of_day=time_of_day,
                    currency_symbol=currency_symbol
                )
                meal_id = str(meal.id)

                payload = recommend_product_payload(text, meal)

                Message.bot_message_action_reply(text, user,
                    payload=payload,
                    metadata={
                        "meal_id": meal_id,
                        "recomendation_id": recom.id,
                        "description": "Users can order, like or hate meal"
                        }
                )
            return True

        # If user has no city, request location and stop (can't generate recommendations)
        if user.city is None:
            Message.bot_message_request_location(
                content="To start getting meal recommendations, please share your delivery location.",
                user=user,
            )
            return False

        # Generate new recommendations
        return build_meal_recommendation(user=user)

    except Exception as e:
        Message.bot_message(f"Error generating meal recommendations", user=user)
        return False


def get_nutritional_info(user: User, meal_id: int) -> bool:
    try:
        meal = Meal.objects.get(id=meal_id)
        Message.bot_message(
            f"Nutritional info for {meal.name}: "
            f"Calories: {float(meal.calories) if meal.calories else 'N/A'}, "
            f"Protein: {f'{float(meal.protein)}g' if meal.protein else 'N/A'}, "
            f"Carbs: {f'{float(meal.carbs)}g' if meal.carbs else 'N/A'}, "
            f"Fats: {f'{float(meal.fats)}g' if meal.fats else 'N/A'}, "
            f"Fiber: {f'{float(meal.fiber)}g' if meal.fiber else 'N/A'}, "
            f"Sugar: {f'{float(meal.sugar)}g' if meal.sugar else 'N/A'}, "
            f"Sodium: {f'{float(meal.sodium)}mg' if meal.sodium else 'N/A'}, "
            f"Cholesterol: {f'{float(meal.cholesterol)}mg' if meal.cholesterol else 'N/A'}, "
            f"Serving Size: {f'{float(meal.serving_amount_g)}g' if meal.serving_amount_g else 'N/A'}, "
            
            f"allergies: {', '.join([a.name for a in user.allergies.all()])}, "
            f"fitness_goals: {user.fitness_goals}, "
            f"health_conditions: {', '.join([h.name for h in user.health_conditions.all()])}, "
            f"preferred_cuisines: {', '.join([c.name for c in user.preferred_cuisine.all()])}, ",
            user=user
        )
        return True
    except Meal.DoesNotExist:
        Message.bot_message("Meal info not found", user=user)
        
        return False
    except Exception as e:
        Message.bot_message("Error fetching nutritional info", user=user)
        return False
