"""
Cron job to remind users to reply within the 24-hour free messaging window.

This job should run every hour to check for users who:
- Haven't replied in 23-24 hours
- Haven't already received a reminder

WhatsApp's free messaging window is 24 hours after the last user message.
We want to prompt users to reply before that window closes.
"""

from django.utils import timezone
from datetime import timedelta
from api.models.user import User
from api.models.message import Message, RoleChoices, CurrentIntentChoices
from django.db.models import Max, Q
import logging

logger = logging.getLogger(__name__)


def remind_users_to_reply():
    """
    Find users whose last reply was 23-24 hours ago and send them a reminder.
    This keeps them within the WhatsApp 24-hour free messaging window.
    """
    now = timezone.now()

    # Time windows
    twenty_three_hours_ago = now - timedelta(hours=23)
    twenty_four_hours_ago = now - timedelta(hours=24)

    logger.info("Starting remind_users_to_reply cron job")
    logger.info(f"Looking for users who last replied between {twenty_four_hours_ago} and {twenty_three_hours_ago}")

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

    logger.info(f"Found {users_with_last_reply.count()} potential users to remind")

    reminded_count = 0
    already_reminded_count = 0
    error_count = 0

    for user in users_with_last_reply:
        try:
            # Check if we already sent a reminder in the last 24 hours
            # Look for bot messages with REMINDER_MESSAGE intent sent after the user's last message
            existing_reminder = Message.objects.filter(
                user=user,
                role=RoleChoices.BOT,
                current_intent=CurrentIntentChoices.REMINDER_MESSAGE,
                created_at__gte=user.last_user_message_time
            ).exists()

            if existing_reminder:
                logger.debug(f"User {user.phone} already received a reminder, skipping")
                already_reminded_count += 1
                continue

            # Send reminder message
            message_content = (
                "Hi! =K\n\n"
                "It's important you respond so we know you still want meal recommendations. "
                "If you don't reply, we might stop sending recommendations until you message us.\n\n"
                "Reply with anything to keep receiving personalized meal suggestions!"
            )

            Message.bot_message_action_reply_simple(
                content=message_content,
                user=user,
                action_replies=["Yes, keep them coming!"],
                current_intent=CurrentIntentChoices.REMINDER_MESSAGE
            )

            reminded_count += 1
            logger.info(f"Sent reminder to user {user.phone} (last reply: {user.last_user_message_time})")

        except Exception as e:
            error_count += 1
            logger.error(f"Error sending reminder to user {user.phone}: {str(e)}", exc_info=True)

    # Summary
    logger.info("="*60)
    logger.info("Remind Users to Reply - Summary")
    logger.info(f"Users reminded: {reminded_count}")
    logger.info(f"Already reminded (skipped): {already_reminded_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("="*60)

    return {
        "reminded": reminded_count,
        "already_reminded": already_reminded_count,
        "errors": error_count,
        "total_checked": users_with_last_reply.count()
    }


def get_users_needing_reminder():
    """
    Helper function to get list of users who need reminders.
    Useful for testing and monitoring.

    Returns:
        QuerySet of User objects who need reminders
    """
    now = timezone.now()
    twenty_three_hours_ago = now - timedelta(hours=23)
    twenty_four_hours_ago = now - timedelta(hours=24)

    users = User.objects.annotate(
        last_user_message_time=Max(
            'messages__created_at',
            filter=Q(messages__role=RoleChoices.USER)
        )
    ).filter(
        last_user_message_time__isnull=False,
        last_user_message_time__gte=twenty_four_hours_ago,
        last_user_message_time__lte=twenty_three_hours_ago
    )

    # Filter out users who already received a reminder
    users_needing_reminder = []
    for user in users:
        existing_reminder = Message.objects.filter(
            user=user,
            role=RoleChoices.BOT,
            current_intent=CurrentIntentChoices.REMINDER_MESSAGE,
            created_at__gte=user.last_user_message_time
        ).exists()

        if not existing_reminder:
            users_needing_reminder.append(user)

    return users_needing_reminder
