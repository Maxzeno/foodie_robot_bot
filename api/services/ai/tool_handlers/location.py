from typing import Optional
from django.contrib.gis.geos import Point

from api.models.meal import Meal, TimeOfDayChoices
from api.models.message import Message
from api.models.recommendation import ChoiceOption, Recommendation
from api.models.user import User
from api.models.location import City
from api.models.address import DeliveryAddress
from api.services.recommendation.meal_recommendation import MealRecommendationService
from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload


def save_delivery_location(
    user: User,
    latitude: float,
    longitude: float,
    name: Optional[str] = None,
    address: Optional[str] = None
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
            Message.bot_message(f"Your delivery location has been set successfully. It falls under {city.name}", user=user)
        else:
            Message.bot_message("Your delivery location has been updated successfully. It's adviced to review your average meal budget anytime you change your delivery location.", user=user)

        # Recommend meals after setting location if they change city
        if not is_new and old_city == city:
            return True
        
        service = MealRecommendationService()
        
        recommended_meal_map = service.get_recommendations(
            user=user,
            num_recommendations_per_period=2,
        )

        for period, recommended_meals_list in recommended_meal_map.items():
            recommended_meals = Meal.objects.filter(id__in=recommended_meals_list)
            for index, meal in enumerate(recommended_meals):
                text = f"Your {'first' if index == 0 else 'second'} {user.get_time_period()} meal recommendation, {meal.name}"
                image_url = meal.image_url.url if meal.image_url else None
                meal_id = str(meal.id)
                
                recomendation_obj = Recommendation.objects.create(
                    user=user,
                    meal=meal,
                    time_of_day=TimeOfDayChoices.get_period(period),
                    choice_option=ChoiceOption.FIRST if index == 0 else ChoiceOption.SECOND,
                    sent_to_user=True if user.get_time_period() == period else False,
                    day=user.get_local_time()
                )

                if user.get_time_period() == period:
                    payload = recommend_product_payload(recomendation_obj.id, text, image_url)

                    Message.bot_message_action_reply(text, user,
                        payload=payload,
                        metadata={
                            "meal_id": meal_id, 
                            "recomendation_id": recomendation_obj.id,
                            "description": "Users can order, like or hate meal"
                            }
                    )

        return True
    except Exception as e:
        print("Error in save_delivery_location:", e)
        Message.bot_message_request_location("Something went wrong when trying to set delivery location. Please click the button below to send us your delivery location.", user=user)
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