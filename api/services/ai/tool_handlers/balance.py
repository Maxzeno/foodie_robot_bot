from api.models.currency import Currency
from api.models.message import Message
from api.models.user import User
from api.models.user_balance import UserBalance


def show_balance_withdraw(
    user: User,
) -> bool:
    try:
        currencies = Currency.objects.all()
        balances = UserBalance.objects.filter(user=user)

        if not balances:
            message = f"Your balance is empty"
        else:
            message = f"Your wallets:\n"
            for balance in balances:
                message += f"{balance.currency.symbol}{balance.amount:,.2f} ({balance.currency.code})\n"

        Message.bot_message_flow(message.strip(), 
            user=user,
            flow_cta="Place Withdrawal", 
            flow_id="1870920103798521", 
            screen_name="WITHDRAWAL",
            data={
                "balance_options": [{"id": currency.code, "title": currency.code} for currency in currencies],
            }
        )
        return True
    except Exception as e:
        print(f"Error placing order: {e}")
        Message.bot_message(
            "Sorry, something went wrong while trying to show balance. Please try again.",
            user=user
        )
        return False
    