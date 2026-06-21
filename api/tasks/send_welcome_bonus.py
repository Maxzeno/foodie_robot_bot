import logging
from django import db
from django.utils import timezone
from datetime import timedelta
from huey import crontab
from huey.contrib.djhuey import periodic_task, task

from api.models.user import User
from api.models.order import Order
from api.models.recommendation import Recommendation
from api.models.message import Message, RoleChoices, CurrentIntentChoices

logger = logging.getLogger(__name__)


def get_welcome_message(user: User) -> str:
    """Generate the welcome bonus message for a user."""
    name = user.username or "there"
    return (
        f"👋 Hey {name}!\n"
        f"Welcome to FoodieRobot 🤖\n\n"
        f"🎁 Enjoy {user.city.currency.symbol}{user.city.delivery_fee_per_km} OFF your first order today only"
    )


def has_received_welcome_bonus(user: User) -> bool:
    """Check if user has already received the welcome bonus message."""
    return Message.objects.filter(
        user=user,
        role=RoleChoices.BOT,
        current_intent=CurrentIntentChoices.WELCOME_BONUS_MESSAGE
    ).exists()


def registered_today(user: User) -> bool:
    """Check if user registered today (in their local time)."""
    local_time = user.get_local_time()
    today_start = local_time.replace(hour=0, minute=0, second=0, microsecond=0)
    return user.created_at >= today_start


def got_recommendations_at_least_10_min_ago(user: User) -> bool:
    """Check if user received meal recommendations at least 10 minutes ago."""
    ten_minutes_ago = timezone.now() - timedelta(minutes=10)
    return Recommendation.objects.filter(
        user=user,
        sent_to_user=True,
        created_at__lte=ten_minutes_ago
    ).exists()


def has_no_paid_orders(user: User) -> bool:
    """Check if user has no paid orders."""
    return not Order.objects.filter(user=user, paid=True).exists()


@task()
def send_welcome_bonus_task():
    db.close_old_connections()

    try:
        now = timezone.now()
        today_utc_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get users who registered today (approximate filter, will refine per-user)
        # We use a wider window to account for timezone differences
        yesterday = today_utc_start - timedelta(days=1)

        new_users = User.objects.filter(
            created_at__gte=yesterday,
            is_active=True,
            is_blocked=False,
            username__isnull=False,
            city__isnull=False,
        ).exclude(username='')

        total_checked = 0
        sent_count = 0
        skipped_not_today = 0
        skipped_no_recommendations = 0
        skipped_has_paid_orders = 0
        skipped_already_sent = 0
        failed_count = 0

        for user in new_users:
            total_checked += 1
            try:
                # Check if registered today (in user's local time)
                if not registered_today(user):
                    skipped_not_today += 1
                    continue

                # Check if already received welcome bonus
                if has_received_welcome_bonus(user):
                    skipped_already_sent += 1
                    continue

                # Check if got recommendations at least 10 min ago
                if not got_recommendations_at_least_10_min_ago(user):
                    skipped_no_recommendations += 1
                    continue

                # Check if has no paid orders
                if not has_no_paid_orders(user):
                    skipped_has_paid_orders += 1
                    continue

                # All criteria met - send welcome bonus message
                message_content = get_welcome_message(user)
                Message.bot_message(
                    content=message_content,
                    user=user,
                    current_intent=CurrentIntentChoices.WELCOME_BONUS_MESSAGE,
                )

                sent_count += 1
                logger.info(f"Sent welcome bonus to user {user.code}")

            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending welcome bonus to user {user.code}: {e}")
                continue

        result = {
            "total_checked": total_checked,
            "sent": sent_count,
            "skipped_not_today": skipped_not_today,
            "skipped_no_recommendations": skipped_no_recommendations,
            "skipped_has_paid_orders": skipped_has_paid_orders,
            "skipped_already_sent": skipped_already_sent,
            "failed": failed_count,
        }

        logger.info(f"Welcome bonus task completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Error in send_welcome_bonus_task: {e}", exc_info=True)
        return {
            "error": str(e),
            "sent": 0,
            "failed": 0,
        }


@periodic_task(crontab(minute='0'))  # Runs every hour
def scheduled_send_welcome_bonus():
    logger.info("Starting scheduled welcome bonus task")
    return send_welcome_bonus_task()
