from api.models.message import Message
from api.models.user import User
from api.models.user_balance import UserBalance, BalanceType


def show_balance(
    user: User,
    balance_type: str = None
) -> bool:
    if not balance_type:
        Message.bot_message(
            "What balance do you want to check? (referral, wallet, bonus)",
            user=user,
        ) 
        
    # Normalize balance_type to match BalanceType choices
    balance_type = balance_type.lower()

    # Map common user inputs to BalanceType choices
    balance_type_map = {
        'referral': BalanceType.REFERRAL,
        'referrals': BalanceType.REFERRAL,
        'wallet': BalanceType.WALLET,
        'bonus': BalanceType.BONUS,
    }

    # Get the balance type or default to referral
    selected_balance_type = balance_type_map.get(balance_type, BalanceType.REFERRAL)

    # Get all balances for this type
    balances = UserBalance.get_balances_by_type(user, selected_balance_type)

    # Filter out zero balances
    non_zero_balances = [b for b in balances if b.amount > 0]

    # Build the message
    balance_type_display = selected_balance_type.label

    if not non_zero_balances:
        message = f"{balance_type_display}:\nNo balance available"
    else:
        message = f"{balance_type_display}:\n"
        for balance in non_zero_balances:
            message += f"  {balance.currency.symbol}{balance.amount:,.2f} ({balance.currency.code})\n"

    Message.bot_message(message.strip(), user=user)
    return True
