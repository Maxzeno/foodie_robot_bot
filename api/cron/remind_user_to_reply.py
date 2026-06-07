from django.utils import timezone
from datetime import timedelta
from api.models.user import User
from api.models.message import Message, RoleChoices, CurrentIntentChoices
from django.db.models import Max, Q


def remind_users_to_reply():
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
            # Look for bot messages with REMINDER_MESSAGE intent sent after the user's last message
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
                "Hi!\n\n"
                "It's important you respond so we know you still want meal recommendations. "
                "If you don't reply, we might stop sending recommendations until you message us.\n\n"
                "Reply with anything to keep receiving personalized meal suggestions!"
            )

            Message.bot_message_action_reply_simple(
                content=message_content,
                user=user,
                action_replies=["Yes, continue"],
                current_intent=CurrentIntentChoices.REMINDER_MESSAGE
            )

            reminded_count += 1

        except Exception as e:
            error_count += 1
            print(f"Error sending reminder to user {user.id}: {e}")


    return {
        "reminded": reminded_count,
        "already_reminded": already_reminded_count,
        "errors": error_count,
        "total_checked": users_with_last_reply.count()
    }
