import logging
from huey import crontab
from huey.contrib.djhuey import periodic_task, task
from django import db

logger = logging.getLogger(__name__)


@task()
def remind_users_to_reply_task():
    """
    Task to remind users who haven't replied in 23-24 hours.
    Can be triggered manually or scheduled via periodic task.
    """
    # Close stale database connections before starting
    db.close_old_connections()

    from django.utils import timezone
    from datetime import timedelta
    from api.models.user import User
    from api.models.message import Message, RoleChoices, CurrentIntentChoices
    from django.db.models import Max, Q

    now = timezone.now()

    # Time windows
    twenty_three_hours_ago = now - timedelta(hours=23)
    twenty_four_hours_ago = now - timedelta(hours=24)

    # Get all users with their last user message timestamp
    users_with_last_reply = User.objects.annotate(
        last_user_message_time=Max(
            'messages__created_at',
            filter=Q(messages__role=RoleChoices.USER)
        )
    ).filter(
        last_user_message_time__isnull=False,
        last_user_message_time__gte=twenty_four_hours_ago,
        last_user_message_time__lte=twenty_three_hours_ago
    )

    reminded_count = 0
    already_reminded_count = 0
    error_count = 0

    for user in users_with_last_reply:
        try:
            # Check if we already sent a reminder in the last 24 hours
            existing_reminder = Message.objects.filter(
                user=user,
                role=RoleChoices.BOT,
                current_intent=CurrentIntentChoices.REMINDER_MESSAGE,
                created_at__gte=user.last_user_message_time
            ).exists()

            if existing_reminder:
                already_reminded_count += 1
                continue

            # Send reminder message
            message_content = (
                "Don’t lose your progress… 👀\n\n"
                f"You haven’t responded, and this is usually how people drift away from their {user.fitness_goals.get_name_display() if user.fitness_goals else 'fitness'} journey.\n\n"
                "If you’re still committed, reply now to keep receiving your meal recommendations.\n\n"
                "No reply means we’ll pause recommendations until you message FoodieRobot."
            )

            Message.bot_message_action_reply_simple(
                content=message_content,
                user=user,
                action_replies=["Continue"],
                current_intent=CurrentIntentChoices.REMINDER_MESSAGE
            )

            reminded_count += 1

        except Exception as e:
            error_count += 1
            logger.error(f"Error sending reminder to user {user.id}: {e}")

    result = {
        "reminded": reminded_count,
        "already_reminded": already_reminded_count,
        "errors": error_count,
        "total_checked": users_with_last_reply.count()
    }

    logger.info(f"Remind users task completed: {result}")
    return result


@periodic_task(crontab(minute='0,30'))
def scheduled_remind_users_to_reply():
    """
    Periodic task that runs every 30 minutes to remind users who haven't replied.
    Schedule: Every 30 minutes (e.g., 10:00, 10:30, 11:00, 11:30, etc.)
    """
    logger.info("Starting scheduled remind users to reply task")
    return remind_users_to_reply_task()
