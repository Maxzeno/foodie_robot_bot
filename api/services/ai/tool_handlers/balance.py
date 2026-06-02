from api.models.message import Message
from api.models.user import User


def show_balance(
    user: User,
) -> bool:
    Message.bot_message(f"Balance: \n Current referral balance: {user.current_referral_earnings}", user=user)
    return True
