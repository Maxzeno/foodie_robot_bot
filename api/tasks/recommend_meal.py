import logging
from huey import crontab
from huey.contrib.djhuey import periodic_task, task

from api.models.meal import Meal, TimeOfDayChoices
from api.models.recommendation import Recommendation, ChoiceOption
from api.services.recommendation.meal_recommendation import MealRecommendationService
from django.db import transaction

from django.utils import timezone
from datetime import timedelta
from django.db.models import Max, Q
from api.models.user import User
from api.models.message import RoleChoices


logger = logging.getLogger(__name__)


@task()
def send_meal_recommendations_task():
    """
    Task to send meal recommendations to active users.
    Can be triggered manually or scheduled via periodic task.
    """
    
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)

    # Get all users who replied in the last 24 hours (active users)
    active_users = User.objects.annotate(
        last_user_message_time=Max(
            'messages__created_at',
            filter=Q(messages__role=RoleChoices.USER)
        )
    ).filter(
        last_user_message_time__gte=twenty_four_hours_ago
    )

    total_users = active_users.count()

    if total_users == 0:
        result = {
            "total_users": 0,
            "users_sent": 0,
            "users_skipped_no_city": 0,
            "users_skipped_already_sent": 0,
            "users_no_meals_available": 0,
            "users_failed": 0,
            "total_messages_sent": 0
        }
        logger.info(f"Meal recommendations task completed (no users): {result}")
        return result

    # Statistics
    users_sent = 0
    users_skipped_no_city = 0
    users_skipped_already_sent = 0
    users_no_meals_available = 0
    users_failed = 0
    total_messages_sent = 0

    # Process each user
    for user in active_users:
        try:
            # Get user's current time period
            time_period = user.get_time_period()
            today = user.get_local_time().date()

            # Check if user has city set
            if not user.city:
                users_skipped_no_city += 1
                continue

            # Check if recommendations already exist for today and current time period
            existing_recommendations = Recommendation.objects.filter(
                user=user,
                time_of_day=TimeOfDayChoices.get_period(time_period),
                day=today,
                sent_to_user=True
            )

            if existing_recommendations.exists():
                users_skipped_already_sent += 1
                continue

            # Generate and send recommendations
            messages_sent, notified_no_meals = _generate_and_send_recommendations(user, time_period, today)

            if messages_sent > 0:
                users_sent += 1
                total_messages_sent += messages_sent
            elif notified_no_meals:
                # User was notified that no meals are available (not a failure)
                users_no_meals_available += 1
            else:
                users_failed += 1

        except Exception as e:
            users_failed += 1
            logger.error(f"Error processing recommendations for user {user.id}: {e}")

    # Summary
    result = {
        "total_users": total_users,
        "users_sent": users_sent,
        "users_skipped_no_city": users_skipped_no_city,
        "users_skipped_already_sent": users_skipped_already_sent,
        "users_no_meals_available": users_no_meals_available,
        "users_failed": users_failed,
        "total_messages_sent": total_messages_sent
    }

    logger.info(f"Meal recommendations task completed: {result}")
    return result


def _generate_and_send_recommendations(user, current_time_period, today):
    """Helper function to generate and send recommendations for a user."""

    with transaction.atomic():
        try:
            # Initialize recommendation service
            service = MealRecommendationService()

            # Generate recommendations for all time periods
            recommended_meal_dict = service.get_recommendations(
                user=user,
                num_recommendations_per_period=2,
            )

            messages_sent = 0

            # Check if no recommendations were found for the current time period
            current_period_meals = recommended_meal_dict.get(current_time_period, [])
            no_results_reason = recommended_meal_dict.get('no_results_reason')

            if not current_period_meals and no_results_reason:
                # No meals available - send explanation message to user
                _send_no_recommendation_message(user, no_results_reason)
                return (0, True)  # Return (messages_sent=0, notified_no_meals=True)

            # Process recommendations for all time periods
            for time_period in ['morning', 'afternoon', 'evening']:
                meal_ids = recommended_meal_dict.get(time_period, [])

                if not meal_ids:
                    continue

                # Get meal objects
                recommended_meals = Meal.objects.filter(id__in=meal_ids)

                # Create recommendation objects and send messages
                for index, meal in enumerate(recommended_meals):
                    # Determine choice option (first or second)
                    choice_option = ChoiceOption.FIRST if index == 0 else ChoiceOption.SECOND

                    # Check if this recommendation already exists
                    existing_rec = Recommendation.objects.filter(
                        user=user,
                        meal=meal,
                        time_of_day=TimeOfDayChoices.get_period(time_period),
                        day=today,
                        choice_option=choice_option
                    ).first()

                    if existing_rec:
                        # Recommendation already exists, just check if we need to send it
                        if time_period == current_time_period and not existing_rec.sent_to_user:
                            _send_recommendation_message(user, meal, existing_rec, time_period, index)
                            existing_rec.sent_to_user = True
                            existing_rec.save(update_fields=['sent_to_user'])
                            messages_sent += 1
                        continue

                    # Create new recommendation object
                    recommendation_obj = Recommendation.objects.create(
                        user=user,
                        meal=meal,
                        time_of_day=TimeOfDayChoices.get_period(time_period),
                        choice_option=choice_option,
                        sent_to_user=(time_period == current_time_period),
                        day=today
                    )

                    # Send message only if this is the current time period
                    if time_period == current_time_period:
                        _send_recommendation_message(user, meal, recommendation_obj, time_period, index)
                        messages_sent += 1

            return (messages_sent, False)  # (messages_sent, notified_no_meals=False)

        except Exception as e:
            logger.error(f"Error generating recommendations for user {user.id}: {e}")
            return (0, False)  # Error occurred


def _send_recommendation_message(user, meal, recommendation_obj, time_period, index):
    """Helper function to send a recommendation message to a user."""
    from api.models.message import Message
    from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload

    try:
        # Format message text
        position_text = 'first' if index == 0 else 'second'
        text = f"Your {position_text} {time_period} meal recommendation, {meal.name}, Meal Cost {meal.price:,.2f}"

        # Get image URL
        image_url = meal.image_url.url if meal.image_url else None

        # Create WhatsApp payload with action buttons
        payload = recommend_product_payload(recommendation_obj.id, text, image_url)

        # Send message
        Message.bot_message_action_reply(
            content=text,
            user=user,
            payload=payload,
            metadata={
                "meal_id": str(meal.id),
                "recommendation_id": recommendation_obj.id,
                "description": "Users can order, like or hate meal"
            }
        )

    except Exception as e:
        logger.error(f"Error sending recommendation message to user {user.id}: {e}")
        raise


def _send_no_recommendation_message(user, filter_stats):
    """
    Send a message to the user explaining why no meal recommendations are available.

    Args:
        user: User instance
        filter_stats: Dictionary containing filter statistics from MealRecommendationService
    """
    from api.models.message import Message
    from api.utils.whatsapp_payload_helper.no_recommendation import (
        get_no_recommendation_message,
        get_no_recommendation_message_short,
        should_show_profile_update_flow
    )
    from api.utils.whatsapp_payload_helper.user_profile_flow_data import user_data_profile_flow

    try:
        # Get currency symbol from user's city
        currency_symbol = "₦"  # Default to Naira
        if user.city and user.city.currency:
            currency_symbol = user.city.currency.symbol

        # Generate user-friendly message
        message_text = get_no_recommendation_message(filter_stats, currency_symbol)

        # Log the reason
        primary_reason = filter_stats.get('primary_reason', 'unknown')
        short_reason = get_no_recommendation_message_short(primary_reason)
        logger.info(f"Sending no-recommendation message to user {user.id}: {short_reason}")

        # Check if profile update can help fix this issue
        if should_show_profile_update_flow(primary_reason):
            # Send message with profile update flow button
            Message.bot_message_flow(
                content=message_text,
                user=user,
                flow_cta="Update profile",
                flow_id="1822264872503617",
                screen_name="USER_PROFILE",
                data=user_data_profile_flow(user),
            )
        else:
            # Send regular text message (for issues that can't be fixed by profile update)
            Message.bot_message(
                content=message_text,
                user=user,
                metadata={
                    "type": "no_recommendation",
                    "reason": primary_reason,
                }
            )

    except Exception as e:
        logger.error(f"Error sending no-recommendation message to user {user.id}: {e}")
        # Don't raise - this is a non-critical message


@periodic_task(crontab(minute='0,30'))
def scheduled_send_meal_recommendations():
    """
    Periodic task that runs every 30 minutes to send meal recommendations.
    Schedule: Every 30 minutes (e.g., 10:00, 10:30, 11:00, 11:30, etc.)
    """
    logger.info("Starting scheduled meal recommendations task")
    return send_meal_recommendations_task()
