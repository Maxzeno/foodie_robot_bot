from api.models.message import Message
from api.models.user import User


def make_withdrawal_form(
    user: User,
) -> bool:
    # TODO: send Whatsapp flow message for withdrawal
    Message.bot_message(f"Not Implemented yet", user=user)
    return True
