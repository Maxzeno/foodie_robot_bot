from typing import Dict

from api.models.user import User
from api.models.message import Message
from django.conf import settings


def contact_support(user: User) -> Dict:
    try:
        support_message = f"Please reach our support team at {settings.CUSTOMER_SUPPORT_NUMBER}"
        Message.bot_message(support_message, user=user)
        return True

    except Exception as e:
        Message.bot_message("Sorry, something went wrong", user=user)
        return False
