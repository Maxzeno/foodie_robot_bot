from django.utils import timezone
from datetime import timedelta
from django.db.models import Max, Q
from api.models.user import User
from api.models.message import Message, RoleChoices
from api.models.meal import Meal, TimeOfDayChoices
from api.models.recommendation import Recommendation, ChoiceOption
from api.services.recommendation.meal_recommendation import MealRecommendationService
from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload
import logging

logger = logging.getLogger(__name__)


def send_meal_recommendations():
    """
    Main function to send meal recommendations to active users.

    Flow:
    1. Get all active users (replied in last 24 hours)
    2. Determine current time period (morning/afternoon/evening)
    3. For each user:
       - Check if they have a city set
       - Check if recommendations already exist for today and current period
       - If not, generate recommendations for all periods
       - Send messages only for current period
       - Mark sent recommendations appropriately

    Returns:
        Dict with statistics about the job execution
    """
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)

    logger.info("="*60)
    logger.info("Starting send_meal_recommendations cron job")
    logger.info(f"Current time: {now}")
    logger.info("="*60)

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
    logger.info(f"Found {total_users} active users (replied in last 24 hours)")

    if total_users == 0:
        logger.info("No active users to send recommendations to")
        return {
            "total_users": 0,
            "users_sent": 0,
            "users_skipped_no_city": 0,
            "users_skipped_already_sent": 0,
            "users_failed": 0,
            "total_messages_sent": 0
        }

    # Statistics
    users_sent = 0
    users_skipped_no_city = 0
    users_skipped_already_sent = 0
    users_failed = 0
    total_messages_sent = 0

    # Process each user
    for user in active_users:
        try:
            # Get user's current time period
            time_period = user.get_time_period()
            today = user.get_local_time().date()

            logger.debug(f"Processing user {user.phone} - Time period: {time_period}, Date: {today}")

            # Check if user has city set
            if not user.city:
                logger.info(f"User {user.phone} has no city set, skipping")
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
                logger.debug(f"User {user.phone} already received {time_period} recommendations today, skipping")
                users_skipped_already_sent += 1
                continue

            # Generate and send recommendations
            messages_sent = _generate_and_send_recommendations(user, time_period, today)

            if messages_sent > 0:
                users_sent += 1
                total_messages_sent += messages_sent
                logger.info(f" Sent {messages_sent} {time_period} recommendations to {user.phone}")
            else:
                users_failed += 1
                logger.warning(f"Failed to send recommendations to {user.phone}")

        except Exception as e:
            users_failed += 1
            logger.error(f"Error processing user {user.phone}: {str(e)}", exc_info=True)

    # Summary
    result = {
        "total_users": total_users,
        "users_sent": users_sent,
        "users_skipped_no_city": users_skipped_no_city,
        "users_skipped_already_sent": users_skipped_already_sent,
        "users_failed": users_failed,
        "total_messages_sent": total_messages_sent
    }

    logger.info("="*60)
    logger.info("Send Meal Recommendations - Summary")
    logger.info(f"Total active users: {total_users}")
    logger.info(f" Users sent recommendations: {users_sent}")
    logger.info(f"Skipped (no city): {users_skipped_no_city}")
    logger.info(f"Skipped (already sent): {users_skipped_already_sent}")
    logger.info(f" Failed: {users_failed}")
    logger.info(f"Total messages sent: {total_messages_sent}")
    logger.info("="*60)

    return result


def _generate_and_send_recommendations(user, current_time_period, today):
    """
    Generate recommendations for all time periods and send messages for current period.

    Args:
        user: User object
        current_time_period: Current time period (morning/afternoon/evening)
        today: User's local date

    Returns:
        int: Number of messages sent
    """
    try:
        # Initialize recommendation service
        service = MealRecommendationService()

        # Generate recommendations for all time periods
        # This returns: {"morning": [id1, id2], "afternoon": [id3, id4], "evening": [id5, id6]}
        recommended_meal_dict = service.get_recommendations(
            user=user,
            num_recommendations_per_period=2,
        )

        messages_sent = 0

        # Process recommendations for all time periods
        for time_period in ['morning', 'afternoon', 'evening']:
            meal_ids = recommended_meal_dict.get(time_period, [])

            if not meal_ids:
                logger.warning(f"No meals recommended for {time_period} for user {user.phone}")
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

        return messages_sent

    except Exception as e:
        logger.error(f"Error generating recommendations for user {user.phone}: {str(e)}", exc_info=True)
        return 0


def _send_recommendation_message(user, meal, recommendation_obj, time_period, index):
    """
    Send a recommendation message to the user via WhatsApp.

    Args:
        user: User object
        meal: Meal object
        recommendation_obj: Recommendation object
        time_period: Time period string (morning/afternoon/evening)
        index: Index of recommendation (0 for first, 1 for second)
    """
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

        logger.debug(f"Sent {position_text} {time_period} recommendation to {user.phone}: {meal.name}")

    except Exception as e:
        logger.error(f"Error sending message to {user.phone}: {str(e)}", exc_info=True)
        raise


def get_users_to_send_recommendations():
    """
    Helper function to get list of users who should receive recommendations.
    Useful for testing and monitoring.

    Returns:
        QuerySet of User objects
    """
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)

    # Get all users who replied in the last 24 hours
    active_users = User.objects.annotate(
        last_user_message_time=Max(
            'messages__created_at',
            filter=Q(messages__role=RoleChoices.USER)
        )
    ).filter(
        last_user_message_time__gte=twenty_four_hours_ago,
        city__isnull=False  # Must have city set
    )

    # Filter out users who already received recommendations for current time period today
    users_needing_recommendations = []

    for user in active_users:
        time_period = user.get_time_period()
        today = user.get_local_time().date()

        existing_recommendations = Recommendation.objects.filter(
            user=user,
            time_of_day=TimeOfDayChoices.get_period(time_period),
            day=today,
            sent_to_user=True
        )

        if not existing_recommendations.exists():
            users_needing_recommendations.append(user)

    return users_needing_recommendations
