from api.models.address import DeliveryAddress
from api.models.location import City
from api.models.message import Message, CurrentIntentChoices
from django.contrib.gis.geos import Point

from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload


def first_location_hander(user, data: dict):
    if data is None or data.get('latitude') is None or data.get('longitude') is None:
        text = """Please we could not get your location, can you try sending it again?
        """
        Message.bot_message_request_location(text, user, current_intent=CurrentIntentChoices.FIRST_LOCATION_RETRY)
        return False
    
    address = data.get('address')
    name = data.get('name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    city = City.get_city_by_coordinates(longitude, latitude)
    
    if city is None:
        text = """Please we are not in your location yet, can you try another location?
        """
        Message.bot_message_request_location(text, user, current_intent=CurrentIntentChoices.FIRST_LOCATION_RETRY)
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
    
    # Do some processing and recommend 2 meals for that time of the day
    # get the image and the meal from db (use ai for the recommendation)
    
    text = "Order rice beans and spag"
    image_url = "https://d1ffknerzfhpen.cloudfront.net/dcdfe210-9947-469b-827a-f5c85eab2d1b-image.jpg"
    meal_id = "1"
    Message.bot_message_action_reply(text, user,
                                     current_intent=CurrentIntentChoices.RECOMMENDED_MEALS, 
                                     payload=recommend_product_payload(meal_id, text, image_url))
    return True
    