from api.models.message import Message
from api.models.settings import AppSettings
from api.models.user import User


def referral_link(
    user: User,
) -> bool:
    setting = AppSettings.get_settings()
    link = f"https://wa.me/{setting.whatsapp_phone_number}?text=Hi, i was referred by #{user.code}"
    
    extra_text = ""
    if user.city:
        extra_text = f"In {user.city.name} you earn {user.city.currency.code} {user.city.referral_bonus} per referral other cities may vary."
    Message.bot_message(f"Your referral link: {link} \n{extra_text}", user=user)
    return True
