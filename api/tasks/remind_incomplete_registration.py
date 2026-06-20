"""
Task to remind users to complete their registration.

Runs hourly to check for users who:
- Registered less than 24 hours ago
- Haven't completed registration (city, or delivery address)
- Last message was sent 4+ hours ago
- Haven't received the reminder yet
"""
import logging
from django import db
from django.utils import timezone
from datetime import timedelta
from huey import crontab
from huey.contrib.djhuey import periodic_task
from django.db.models import Q, Max

from api.models.user import User
from api.models.address import DeliveryAddress
from api.models.message import Message, RoleChoices
from django.conf import settings

from api.utils.whatsapp_payload_helper.user_profile_flow_data import user_data_profile_flow

logger = logging.getLogger(__name__)


@periodic_task(crontab(minute='30'))  # Runs every hour at minute 30
def remind_incomplete_registration():
    """
    Send reminder to users who haven't completed registration after 4 hours of inactivity.
    """
    db.close_old_connections()

    try:
        now = timezone.now()
        # Within 24 hours of registration
        time_24h_ago = now - timedelta(hours=24)
        # At least 4 hours since last message
        time_4h_ago = now - timedelta(hours=4)

        logger.info(f"Checking for users with incomplete registration (registered after {time_24h_ago}, inactive since {time_4h_ago})")

        # Find users who registered in the last 24 hours
        potential_users = User.objects.filter(
            created_at__gte=time_24h_ago,
            is_active=True,
            is_blocked=False,
            registration_reminder_sent=False,
        ).exclude(phone__isnull=True).exclude(phone='')

        sent_count = 0
        for user in potential_users:
            has_fill_profile = user.fitness_goals is not None
            has_delivery_address = DeliveryAddress.objects.filter(user=user).exists()

            # If registration is complete, skip
            if has_fill_profile and has_delivery_address:
                continue

            # Get user's last message timestamp
            last_user_message = Message.objects.filter(
                user=user,
                role=RoleChoices.USER
            ).aggregate(Max('created_at'))['created_at__max']

            # Skip if user sent a message less than 4 hours ago
            if last_user_message and last_user_message > time_4h_ago:
                continue

            try:
                # Send reminder message
                if not has_fill_profile:
                    Message.bot_message_flow(
                        (
                            f"👋 Hey {user.username}, welcome to FoodieRobot!\n"
                            f"You're almost done! 🎉 Please answer a quick question to get started."
                        ),
                        user=user,
                        flow_cta="Get Started",
                        flow_id=settings.WHATSAPP_FLOW_USER_PROFILE,
                        screen_name="USER_PROFILE",
                        data=user_data_profile_flow(user),
                    )

                elif has_fill_profile and not has_delivery_address:
                    Message.bot_message_request_location(
                       content=(
                            f"👋 Hey {user.username}, welcome to FoodieRobot!\n"
                            f"You're almost set 🎉 Just add your delivery location to get meal recommendations tailored to your fitness goal "
                            f"from top restaurants around you."
                        ),
                        user=user
                    )

                # Mark as sent
                user.registration_reminder_sent = True
                user.save(update_fields=['registration_reminder_sent'])

                sent_count += 1
                logger.info(f"Sent registration reminder to user {user.code} (phone: {user.phone})")

            except Exception as e:
                logger.error(f"Failed to send registration reminder to user {user.code}: {e}")
                continue

        logger.info(f"Registration reminder task completed. Sent {sent_count} messages.")

    except Exception as e:
        logger.error(f"Error in remind_incomplete_registration task: {e}", exc_info=True)
