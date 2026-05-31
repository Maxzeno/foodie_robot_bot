from typing import Dict

from api.models.user import User
from api.models.order import Order
from api.models.message import Message


def get_payment_status(user: User) -> Dict:
    try:
        # Get latest order
        order = Order.objects.filter(user=user).order_by('-created_at').first()

        if not order:
            Message.bot_message(
                "You haven't placed any orders yet. Browse our meals and place your first order!",
                user=user
            )
            return False

        # Check payment status
        currency_symbol = order.currency.symbol

        if order.paid:
            message = f"""
✅ Payment Confirmed!

Order #{order.code}
🍽️ {order.meal.name}
💰 Amount Paid: {currency_symbol}{order.amount_paid:,.2f}

Your order is being processed.
""".strip()

        else:
            message = f"""
⏳ Payment Pending

Order #{order.code}
🍽️ {order.meal.name}
💰 Total: {currency_symbol}{order.total_price:,.2f}
💳 Payment Status: Not confirmed yet

If you've already paid, please wait a few moments for the payment to be processed. You'll receive a confirmation message once payment is verified.
""".strip()

        Message.bot_message(message, user=user)

        return False

    except Exception as e:
        print(f"Error getting payment status: {e}")
        Message.bot_message(
            "Sorry, something went wrong while checking your payment status. Please try again.",
            user=user
        )
        return False
