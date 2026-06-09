from typing import Optional
from django.contrib.gis.geos import Point

from api.models.message import Message
from api.models.order import Order
from api.models.user import User
from api.models.location import City
from api.models.address import DeliveryAddress
from api.services.ai.tool_handlers.meal import build_meal_recommendation
from api.services.ai.tool_handlers.order import place_order
from datetime import timedelta
from api.services.ai.tool_handlers.menu_options import show_menu_options

def save_delivery_location(
    user: User,
    latitude: float,
    longitude: float,
    name: Optional[str] = None,
    address: Optional[str] = None,
) -> bool:
    is_new = user.city is None
    try:
        # Detect city from coordinates
        city = City.get_city_by_coordinates(longitude, latitude)

        if not city:
            Message.bot_message_request_location("The delivery location is not in our currently supported cities. Please click the button below if you want to try a different delivery location.", user=user)
            return False

        # Update user's city
        old_city = user.city
        user.city = city
        user.save()

        # Create or update delivery address
        point = Point(longitude, latitude, srid=4326)

        # Create new default address
        DeliveryAddress.objects.create(
            user=user,
            point=point,
            name=name,
            street_address=address,
            is_default=False
        )
        if is_new:
            show_menu_options(user, f"Your delivery location has been set successfully. It falls under {city.name}. \n\nYou can also explore our Quick Actions menu to see more things you can do, such as checking your calorie stats, referring a friend (and earning rewards), and more.")
        elif old_city and (old_city.currency == user.city.currency):
            Message.bot_message(f"Your delivery location has been updated successfully. It falls under {city.name}", user=user)
        else:
            Message.bot_message(f"Your delivery location has been updated successfully. It falls under {city.name}. \n\nPlease review your average meal budget since your current location uses a different currency from your last location.", user=user)

    except Exception as e:
        print("Error in save_delivery_location:", e)
        Message.bot_message_request_location("Something went wrong when trying to set delivery location. Please click the button below to send us your delivery location.", user=user)
        return False
    
    try:
        # Recommend meals after setting location if they change city
        if not is_new and old_city == city:
            order = Order.objects.filter(user=user).first()
            # also check that the time is not to far apart from current time
            time_diff = user.get_local_time() - order.created_at
            if order and order.paid == False and time_diff < timedelta(hours=6):
                place_order(user=user, meal_id=order.meal.id, number_of_plates=order.quantity, special_instructions=order.note, recreated_with_new_address=True)
            return True
        
        build_meal_recommendation(user=user)

        return True
    except Exception as e:
        print("Error in save_delivery_location:", e)
        return False


def request_delivery_location(user: User) -> bool:
    try:
        message = Message.bot_message_request_location(
            content="Please share your delivery location.",
            user=user,
        )
        # generate food recommendations after getting location and send to them
        if message:
            return True
        else:
            Message.bot_message("Something went wrong when trying to request your delivery location.", user=user)
    
    except Exception as e:
        Message.bot_message("Something went wrong when trying to request your delivery location.", user=user)
        return False
    

def get_current_location(user: User) -> bool:
    try:
        text = f"Your current delivery address"
        
        latest_delivery_address = DeliveryAddress.objects.filter(user=user).first()
        Message.bot_message_location(latest_delivery_address.name or text, user, latitude=latest_delivery_address.point.y, longitude=latest_delivery_address.point.x, address=latest_delivery_address.street_address)

        return True
    except Exception as e:
        Message.bot_message("Something went wrong when trying to get your current delivery location.", user=user)
        return False