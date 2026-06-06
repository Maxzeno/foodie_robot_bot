from api.models.currency import Currency
from api.models.message import Message
from api.models.user import User
from api.models.user_balance import UserBalance
from api.models.withdrawal import Withdrawal
from django.db import transaction

def withdrawal_history(user: User, page: int=1) -> bool:
    try:
        limit: int = 3
        offset = (page - 1) * limit

        withdrawals = Withdrawal.objects.filter(
            user=user
        ).select_related('currency').order_by('-created_at')[offset:offset + limit]

        if not withdrawals.exists():
            if page == 1:
                Message.bot_message(
                    "You haven't made any withdrawal requests yet.",
                    user=user
                )
            else:
                Message.bot_message(
                    f"You have no more withdrawals to show.",
                    user=user
                )
            return False

        message = f"💰 Your Withdrawal History (Page {page}):\n\n"

        for i, withdrawal in enumerate(withdrawals, 1):
            status_emoji = {
                'pending': '⏳',
                'approved': '✅',
                'rejected': '❌'
            }.get(withdrawal.status, '•')

            message += f"{i}. {status_emoji} {withdrawal.amount:,.2f} {withdrawal.currency.code}\n"
            message += f"Status: {withdrawal.status.title()}\n"
            message += f"Bank: {withdrawal.bank_name}\n"
            message += f"Account name: {withdrawal.account_name}\n"
            message += f"Account number: {withdrawal.account_number}\n"
            message += f"Date: {withdrawal.created_at.strftime('%b %d, %Y')}\n\n"

        message = message.strip()

        Message.bot_message_action_reply_simple(
            message,
            user=user,
            action_replies=[f'Page {page + 1}']
        )

        return True

    except Exception as e:
        print(f"Error getting withdrawal history: {e}")
        Message.bot_message(
            "Sorry, something went wrong while retrieving your withdrawal history. Please try again.",
            user=user
        )
        return False


def make_withdrawal(
    user: User,
    account_name: str,
    account_number: str,
    bank_name: str,
    currency: str,
) -> bool:
    try:
        with transaction.atomic():
            currency_obj = Currency.objects.filter(code=currency).first()

            if not currency_obj:
                Message.bot_message("Failed to place withdrawal invalid currency code. Please contact customer support.", user=user)
                return False
            
            user_balance = UserBalance.get_balance(user=user, currency=currency_obj)
            if user_balance.amount < 500:
                Message.bot_message(f"Insufficient balance to make a withdrawal. Minimum withdrawal balance is 500 ({currency}).", user=user)
                return False
            
            Withdrawal.objects.create(
                user=user,
                amount=user_balance.amount,
                currency=currency_obj,
                account_name=account_name,
                account_number=account_number,
                bank_name=bank_name,
            )
            user_balance.amount = 0
            user_balance.save()

            Message.bot_message("Your withdrawal is being processed.", user=user)
        return True
    except:
        Message.bot_message("Failed to place withdrawal. Please contact customer support.", user=user)
