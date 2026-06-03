from typing import Dict

from api.models.settings import AppSettings
from api.models.user import User
from api.models.message import Message


def contact_support(user: User) -> bool:
    try:
        setting = AppSettings.get_settings()
        support_message = f"Please reach our support team at {setting.whatsapp_support_phone_number}"
        Message.bot_message(support_message, user=user)
        return True

    except Exception as e:
        Message.bot_message("Sorry, something went wrong", user=user)
        return False
