from api.models.message import Message
from api.models.settings import AppSettings
from api.models.user import User
import urllib.parse

def referral_link(
    user: User,
) -> bool:
    try:
        setting = AppSettings.get_settings()
        text = f"Hi, I was referred by #{user.code}"
        encoded_text = urllib.parse.quote(text)

        link = f"https://wa.me/{setting.whatsapp_phone_number}?text={encoded_text}"
            
        extra_text = ""
        if user.city:
            extra_text = f"In {user.city.name} you earn {user.city.currency.code} {user.city.referral_bonus} per referral (After first order payment) other cities may vary."
        Message.bot_message(f"Your referral link (Share with friends): {link} \n\n{extra_text}", user=user)
        return True
    except Exception as e:
        Message.bot_message("Sorry, something went wrong", user=user)
        return False
