from api.models.message import Message
from api.models.user import User


def make_withdraw(
    user: User,
    currency: str,
    withdrawal_method: str,
    withdrawal_details: str,
) -> bool:
    # TODO: Maybe use whatsapp flow for this.
    Message.bot_message(f"Not Implemented yet", user=user)
    return True
