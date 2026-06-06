from typing import Optional, Dict
from decimal import Decimal

from api.models.location import City
from api.models.user import User
from api.models.meal import Meal
from api.models.order import Order, OrderStatus
from api.models.address import DeliveryAddress
from api.models.message import Message
import requests
from django.conf import settings

from api.utils.distance import cal_delivery_fee

# Format status message
ORDER_STATUS_EMOJI = {
    OrderStatus.PENDING: "⏳",
    OrderStatus.DISPATCHED: "🚗",
    OrderStatus.ARRIVED: "📍",
    OrderStatus.RECEIVED: "✅"
}

ORDER_STATUS_MESSAGE = {
    OrderStatus.PENDING: "Your order is being prepared",
    OrderStatus.DISPATCHED: "Your order is on the way",
    OrderStatus.ARRIVED: "Your order has arrived",
    OrderStatus.RECEIVED: "Order completed"
}

def payment_link(order: Order):
    # url = "https://api.staging.myvendy.com/public/transactions/payment-url"
    url = "https://api.myvendy.com/public/transactions/payment-url"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.VENDY_PUBLIC_KEY}"
    }

    payload = {
        "amount": float(order.total_price),
        "msisdn": order.user.phone,
        "currency": "NGN",
        "channel": "whatsapp",
        "meta": {
            "orderId": order.id
        },
        "charge_customer": True,
        "product": "transactions"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json()['data']['meta']['payment_link_url']
    return None


def place_order_form(
        user: User,
        meal_id: int
    ) -> bool:

    if not user.city:
        Message.bot_message_request_location("Please set your delivery location first before placing an order.", user=user)
        return False

    # Validate meal
    try:
        meal = Meal.objects.get(id=meal_id, available=True)
    except Meal.DoesNotExist:
        Message.bot_message(
            "Sorry, this meal is not available at the moment. Please choose another meal.",
            user=user
        )
        return False

    # Check if meal is in user's city
    if meal.city != user.city:
        Message.bot_message(
            f"Sorry, this meal is only available in {meal.city.name}. Your current location is in {user.city.name if user.city else 'an unknown city'}.",
            user=user
        )
        return False

    delivery_address = DeliveryAddress.objects.filter(user=user).first()

    if not delivery_address:
        Message.bot_message(
            "Please set a delivery address first before placing an order.",
            user=user
        )
        return False
    
    address_city = City.get_city_by_coordinates(delivery_address.point.x, delivery_address.point.y)
    if address_city != user.city:
        Message.bot_message(
            "Your selected delivery address is outside your current city. Please update your delivery address or change your delivery location.",
            user=user
        )
        return False

    try:
        message = Message.bot_message_flow("Please complete the order", 
            user=user, 
            flow_cta="Fill form", 
            flow_id="1531243271627499", 
            screen_name="ORDER_FLOW",
            data={
                "current_address": delivery_address.street_address or 'Last set address',
                "maps_url": f"https://www.google.com/maps?q={delivery_address.point.y},{delivery_address.point.x}",
                "meal_id": meal_id
            }
        )
    except Exception as e:
        Message.bot_message(
            "Sorry, something went wrong while initiating your order. Please try again.",
            user=user
        )
        return False
    return True


def place_order(
    user: User,
    meal_id: int,
    number_of_plates: int=None,
    # delivery_address_id: Optional[int] = None,
    special_instructions: Optional[str] = None,
    recreated_with_new_address: bool = False
) -> bool:
    print("Placing order...", meal_id, number_of_plates, special_instructions)
    try:
        if not number_of_plates:
            Message.bot_message(
                "How many plates would you like to order?",
                user=user,
                metadata={
                    "meal_id": meal_id, 
                    "description": "User can order meal"
                }
            ) 
            return False
        
        if type(number_of_plates) != int:
            number_of_plates = int(number_of_plates)
        
        if type(meal_id) != int:
            meal_id = int(meal_id)

        if not user.city:
            Message.bot_message_request_location("Please set your delivery location first before placing an order.", user=user)
            return False
        
        if number_of_plates < 1:
            Message.bot_message(
                "Number of plates must be at least 1.",
                user=user
            )
            return False
        
        # Validate meal
        try:
            meal = Meal.objects.get(id=meal_id, available=True)
        except Meal.DoesNotExist:
            Message.bot_message(
                "Sorry, this meal is not available at the moment. Please choose another meal.",
                user=user
            )
            return False

        # Check if meal is in user's city
        if meal.city != user.city:
            Message.bot_message(
                f"Sorry, this meal is only available in {meal.city.name}. Your current location is in {user.city.name if user.city else 'an unknown city'}.",
                user=user
            )
            return False

        # Get delivery address
        # if delivery_address_id:
        #     try:
        #         delivery_address = DeliveryAddress.objects.get(id=delivery_address_id, user=user)
        #     except DeliveryAddress.DoesNotExist:
        #         delivery_address = DeliveryAddress.objects.filter(user=user).first()
        # else:
        #     delivery_address = DeliveryAddress.objects.filter(user=user).first()

        delivery_address = DeliveryAddress.objects.filter(user=user).first()

        if not delivery_address:
            Message.bot_message(
                "Please set a delivery address first before placing an order.",
                user=user
            )
            return False
        
        address_city = City.get_city_by_coordinates(delivery_address.point.x, delivery_address.point.y)
        if address_city != user.city:
            Message.bot_message(
                "Your selected delivery address is outside your current city. Please update your delivery address or change your delivery location.",
                user=user
            )
            return False
        
        # Calculate pricing
        meal_price = meal.price * number_of_plates

        delivery_fee = Decimal(str(cal_delivery_fee(meal.city.delivery_fee_per_km, 
                                                    meal.city.min_delivery_fee, 
                                                    meal.restaurant.point.y, 
                                                    meal.restaurant.point.x, 
                                                    delivery_address.point.y, 
                                                    delivery_address.point.x)))

        total_price = meal_price + delivery_fee

        # Create order
        order = Order.objects.create(
            user=user,
            meal=meal,
            quantity=number_of_plates,
            status=OrderStatus.PENDING,
            note=special_instructions or "",
            currency=user.city.currency,
            meal_price=meal_price,
            delivery_fee=delivery_fee,
            total_price=total_price,
            amount_paid=Decimal('0.00'),
            paid=False,
            dropoff_street_address=delivery_address.street_address,
            dropoff_point=delivery_address.point,
            pickup_street_address=meal.restaurant.street_address if hasattr(meal.restaurant, 'street_address') else None,
            pickup_point=meal.restaurant.point if hasattr(meal.restaurant, 'point') else None,
        )

        payment_url = payment_link(order)
        if not payment_url:
            Message.bot_message(
                "Sorry, we couldn't generate a payment link at the moment. Please try again later.",
                user=user
            )
            return False
        
        # Format message
        currency_symbol = user.city.currency.symbol
        message = f"""
✅ {"Order placed successfully!" if recreated_with_new_address == False else "Your last Order recreated with your new address" }

📋 Order #{order.code}
🍽️ {meal.name}
🔢 Quantity: {number_of_plates} plate(s)

💰 Price Breakdown:
• Meal: {currency_symbol}{meal_price:,.2f}
• Delivery: {currency_symbol}{delivery_fee:,.2f}
• Total: {currency_symbol}{total_price:,.2f}

📍 Delivery to: 
• Address: {delivery_address.street_address or 'Last set address'} 
• View current delivery address: https://www.google.com/maps?q={delivery_address.point.y},{delivery_address.point.x} (You can update the delivery address if this isn’t your desired location.)

💳 Please proceed to payment to confirm your order.
""".strip()

        Message.bot_message_url_cta(message, action_text="Pay now", action_url=payment_url, user=user)

        return True

    except Exception as e:
        print(f"Error placing order: {e}")
        Message.bot_message(
            "Sorry, something went wrong while placing your order. Please try again.",
            user=user
        )
        return False


def get_order_status(user: User, order_id: Optional[int] = None) -> bool:
    try:
        if order_id:
            try:
                order = Order.objects.get(id=order_id, user=user)
            except Order.DoesNotExist:
                Message.bot_message(
                    f"Order #{order_id} not found. Please check the order number and try again.",
                    user=user
                )
                return False
        else:
            # Get latest order
            order = Order.objects.filter(user=user).order_by('-created_at').first()
            if not order:
                Message.bot_message(
                    "You haven't placed any orders yet. Browse our meals and place your first order!",
                    user=user
                )
                return False

        currency_symbol = order.currency.symbol
        payment_status = "Paid" if order.paid else "Pending"

        message = f"""
Order #{order.code}
🍽️ {order.meal.name}
🔢 Quantity: {order.quantity} plate(s)
💰 Total: {currency_symbol}{order.total_price:,.2f}
{ORDER_STATUS_EMOJI.get(order.status, '📋')} Status: {"Your order will be processed after payment" if not order.paid else ORDER_STATUS_MESSAGE.get(order.status, 'Processing your order')}
💳 Payment: {payment_status}

""".strip()

        Message.bot_message(message, user=user)

        return True

    except Exception as e:
        print(f"Error getting order status: {e}")
        Message.bot_message(
            "Sorry, something went wrong while retrieving your order status. Please try again.",
            user=user
        )
        return False


def get_order_history(user: User, page: int = 1) -> bool:
    try:
        # Calculate offset
        limit: int = 3
        offset = (page - 1) * limit

        # Get orders
        total_orders = Order.objects.filter(user=user).count()
        orders = Order.objects.filter(user=user).order_by('-created_at')[offset:offset + limit]

        if not orders.exists():
            if page == 1:
                Message.bot_message(
                    "You haven't placed any orders yet. Browse our meals and place your first order!",
                    user=user
                )
            else:
                Message.bot_message(
                    "No more orders to show.",
                    user=user
                )
            return False

        # Format message
        currency_symbol = user.city.currency.symbol if user.city else ""
        message = f"📋 Your Order History (Page {page}):\n\n"

        for i, order in enumerate(orders, 1):
            payment_status = "Paid" if order.paid else "Pending"

            message += f"""
{offset + i}. Order #{order.code}
   🍽️ {order.meal.name}
   🔢 Quantity: {order.quantity} plate(s)
   💰 Total: {currency_symbol}{order.total_price:,.2f}
   {ORDER_STATUS_EMOJI.get(order.status, '📋')} Status: {"Your order will be processed after payment" if not order.paid else ORDER_STATUS_MESSAGE.get(order.status, 'Processing your order')}
   💳 Payment: {payment_status}
   📅 Ordered on: {order.created_at.strftime('%b %d, %Y')}

""".strip() + "\n\n"

        Message.bot_message_action_reply_simple(message.strip(), user=user, action_replies=[f'Page {page + 1}'])
        return True

    except Exception as e:
        print(f"Error getting order history: {e}")
        Message.bot_message(
            "Sorry, something went wrong while retrieving your order history. Please try again.",
            user=user
        )
        return False
