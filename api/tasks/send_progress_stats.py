import logging
from django import db
from django.db.models import Max, Q
from django.utils import timezone
from datetime import timedelta
from huey import crontab
from huey.contrib.djhuey import periodic_task, task

from api.models.user import User
from api.models.message import Message, RoleChoices, CurrentIntentChoices
from api.services.ai.tool_handlers.stats import get_progress_stats

logger = logging.getLogger(__name__)


# Captions for different message types (first time, second time, regular)
CAPTIONS = {
    "first": (
        "Here's your daily progress update!\n\n"
        "See how you're doing and share with friends to inspire them on their fitness journey too!"
    ),
    "second": (
        "Your daily stats are in!\n\n"
        "Share your progress with friends and challenge them to join you!"
    ),
    "others": (
        "Your daily progress update is ready!\n\n"
        "Share your achievements with friends and show them what you've been up to!"
    ),
}


def get_message_type(user: User) -> str:
    """
    Determine message type based on how many PROGRESS_STATS_REMINDER
    messages have been sent to the user (excluding today).
    """
    local_time = user.get_local_time()
    today_start = local_time.replace(hour=0, minute=0, second=0, microsecond=0)

    stats_count = Message.objects.filter(
        user=user,
        role=RoleChoices.BOT,
        current_intent=CurrentIntentChoices.PROGRESS_STATS_REMINDER,
        created_at__lt=today_start  # Don't count today's message
    ).count()

    if stats_count == 0:
        return "first"
    elif stats_count == 1:
        return "second"
    else:
        return "others"


def has_received_stats_today(user: User) -> bool:
    """Check if user has already received progress stats today (in their local time)."""
    local_time = user.get_local_time()
    today_start = local_time.replace(hour=0, minute=0, second=0, microsecond=0)

    return Message.objects.filter(
        user=user,
        role=RoleChoices.BOT,
        current_intent=CurrentIntentChoices.PROGRESS_STATS_REMINDER,
        created_at__gte=today_start
    ).exists()


def is_valid_time_for_stats(user: User) -> bool:
    """
    Check if it's a valid time to send stats to this user.
    Valid time: 3 PM (15:00) or later, but before midnight (same day).
    """
    local_time = user.get_local_time()
    hour = local_time.hour
    return hour >= 15  # 3 PM or later (and before midnight since hour < 24)


@task()
def send_progress_stats_task():
    """
    Send progress stats to active users who are in the valid time window.

    Only sends if:
    - User is within 24-hour WhatsApp service window
    - User's local time is 3 PM or later (but same day)
    - User hasn't received stats today yet
    """
    db.close_old_connections()

    try:
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)

        # Get all users who replied in the last 24 hours (active users within service window)
        active_users = User.objects.annotate(
            last_user_message_time=Max(
                'messages__created_at',
                filter=Q(messages__role=RoleChoices.USER)
            )
        ).filter(
            last_user_message_time__gte=twenty_four_hours_ago,
            is_active=True,
            is_blocked=False,
        )

        total_users = active_users.count()
        logger.info(f"Found {total_users} active users within 24-hour window")

        sent_count = 0
        failed_count = 0
        skipped_wrong_time = 0
        skipped_already_sent = 0
        first_count = 0
        second_count = 0
        others_count = 0

        for user in active_users:
            try:
                # Check if it's valid time for this user (3 PM - midnight local time)
                if not is_valid_time_for_stats(user):
                    skipped_wrong_time += 1
                    continue

                # Check if already sent today
                if has_received_stats_today(user):
                    skipped_already_sent += 1
                    continue

                # Get appropriate caption based on message history
                message_type = get_message_type(user)
                caption = CAPTIONS[message_type]

                # Track message type counts
                if message_type == "first":
                    first_count += 1
                elif message_type == "second":
                    second_count += 1
                else:
                    others_count += 1

                # Send progress stats with the appropriate caption
                success = get_progress_stats(user=user, caption=caption)
                if success:
                    # Update the last sent message to have the correct intent for tracking
                    last_bot_message = Message.objects.filter(
                        user=user,
                        role=RoleChoices.BOT
                    ).order_by('-created_at').first()

                    if last_bot_message:
                        last_bot_message.current_intent = CurrentIntentChoices.PROGRESS_STATS_REMINDER
                        last_bot_message.save(update_fields=['current_intent'])

                    sent_count += 1
                    logger.info(f"Sent progress stats to user {user.code} (type: {message_type})")
                else:
                    failed_count += 1

            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending progress stats to user {user.code}: {e}")
                continue

        result = {
            "total_active_users": total_users,
            "sent": sent_count,
            "failed": failed_count,
            "skipped_wrong_time": skipped_wrong_time,
            "skipped_already_sent": skipped_already_sent,
            "by_type": {
                "first": first_count,
                "second": second_count,
                "others": others_count,
            }
        }

        logger.info(f"Progress stats task completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in send_progress_stats_task: {e}", exc_info=True)
        return {
            "error": str(e),
            "sent": 0,
            "failed": 0,
        }


@periodic_task(crontab(minute='0'))  # Runs every hour to check users in different timezones
def scheduled_send_progress_stats():
    """
    Periodic task that runs hourly to send progress stats.
    Checks each user's local timezone to send at 3 PM or later.
    """
    logger.info("Starting scheduled progress stats task (hourly check)")
    return send_progress_stats_task()
