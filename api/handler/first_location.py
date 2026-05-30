from api.models.address import DeliveryAddress
from api.models.location import City
from api.models.meal import Meal, TimeOfDayChoices
from api.models.message import Message, CurrentIntentChoices
from django.contrib.gis.geos import Point

from api.models.recommendation import ChoiceOption, Recommendation
from api.services.recommendation.meal_recommendation import MealRecommendationService
from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload


def first_location_hander(user, data: dict):
    if data is None or data.get('latitude') is None or data.get('longitude') is None:
        text = """Please we could not get your location, can you try sending it again?
        """
        Message.bot_message_request_location(text, user, current_intent=CurrentIntentChoices.FIRST_LOCATION)
        return False
    
    address = data.get('address')
    name = data.get('name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    city = City.get_city_by_coordinates(longitude, latitude)
    
    if city is None:
        text = """Please we are not in your location yet, can you try another location?
        """
        Message.bot_message_request_location(text, user, current_intent=CurrentIntentChoices.FIRST_LOCATION)
        return False
    
    delivery_address = DeliveryAddress.objects.create(
        user=user,  
        point=Point(longitude, latitude, srid=4326),
        street_address=address,
        name=name
    )
    
    user.city = city
    user.currency = city.currency
    user.average_meal_budget = city.average_meal_budget
    user.save()    
    
    text = f"""Your location has been set successfully, it falls under this city: {city.name}. We can now start recommending meals 🍽️🤖
    """
    Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)
    
    # Recommend meals after setting location
    service = MealRecommendationService()
    
    recommended_meal_map = service.get_recommendations_by_algo(
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
            )

            if user.get_time_period() == period:
                payload = recommend_product_payload(recomendation_obj.id, text, image_url)

                Message.bot_message_action_reply(text, user,
                    current_intent=CurrentIntentChoices.RECOMMENDED_MEALS, 
                    payload=payload)

    return True
