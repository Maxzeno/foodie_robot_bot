"""
Task to send referral invitation messages to users who have completed registration.

Runs hourly to check for users who:
- Registered 3-24 hours ago
- Have completed profile (username + city set)
- Have a delivery address
- Haven't received the referral message yet
"""
import logging
import urllib.parse
from django import db
from django.utils import timezone
from datetime import timedelta
from huey import crontab
from huey.contrib.djhuey import periodic_task

from api.models.user import User
from api.models.address import DeliveryAddress
from api.models.message import Message
from api.models.settings import AppSettings

logger = logging.getLogger(__name__)


@periodic_task(crontab(minute='0'))  # Runs every hour at minute 0
def send_referral_invitation_messages():
    """
    Send referral invitation message to users who completed registration 3-24 hours ago.
    """
    db.close_old_connections()

    try:
        now = timezone.now()
        # Calculate time window: 3-24 hours ago
        time_24h_ago = now - timedelta(hours=24)
        time_3h_ago = now - timedelta(hours=3)

        logger.info(f"Checking for users to send referral messages (registered between {time_24h_ago} and {time_3h_ago})")

        # Find eligible users
        eligible_users = User.objects.filter(
            created_at__gte=time_24h_ago,
            created_at__lte=time_3h_ago,
            is_active=True,
            is_blocked=False,
            referral_message_sent=False,
            # Profile completion checks
            username__isnull=False,
            city__isnull=False,
        ).exclude(username='').exclude(phone__isnull=True).exclude(phone='')

        sent_count = 0
        for user in eligible_users:
            # Check if user has a delivery address
            has_delivery_address = DeliveryAddress.objects.filter(user=user).exists()

            if not has_delivery_address:
                continue

            try:
                # Get app settings for WhatsApp number
                setting = AppSettings.get_settings()

                # Generate referral link
                text = f"Hi, I was referred by a friend (Referral code: #{user.code})"
                encoded_text = urllib.parse.quote(text)
                referral_link = f"https://wa.me/{setting.whatsapp_phone_number}?text={encoded_text}"

                # Extra text with bonus info if city is set
                extra_text = ""
                if user.city:
                    extra_text = f"\nIn {user.city.name} you earn {user.city.currency.code} {user.city.referral_bonus} per referral (After first order payment) other cities may vary."

                # Send referral invitation message
                Message.bot_message(
                    content=(
                        "🎉 Love FoodieRobot? Invite your friends and family!\n\n"
                        "Share your unique referral link and get rewarded when they place their first order.\n\n"
                        f"Your referral link (Share with friends): {referral_link}\n\n"
                        f"{extra_text}"
                    ),
                    user=user
                )

                # Mark as sent
                user.referral_message_sent = True
                user.save(update_fields=['referral_message_sent'])

                sent_count += 1
                logger.info(f"Sent referral invitation to user {user.code} (phone: {user.phone})")

            except Exception as e:
                logger.error(f"Failed to send referral message to user {user.code}: {e}")
                continue

        logger.info(f"Referral invitation task completed. Sent {sent_count} messages.")

    except Exception as e:
        logger.error(f"Error in send_referral_invitation_messages task: {e}", exc_info=True)
