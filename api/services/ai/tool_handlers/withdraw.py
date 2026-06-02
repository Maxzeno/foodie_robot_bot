from api.models.message import Message
from api.models.user import User


def make_withdraw(
    user: User,
    currency: str,
    account_number: str,
    bank_name: str,
) -> bool:
    # Maybe use whatsapp flow for this.
    Message.bot_message(f"Not Implemented yet", user=user)
    return True
