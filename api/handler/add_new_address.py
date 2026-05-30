from api.models.address import DeliveryAddress
from api.models.location import City
from api.models.message import Message, CurrentIntentChoices
from django.contrib.gis.geos import Point

from api.utils.whatsapp_payload_helper import number_of_plates


def add_new_address_hander(user, data: dict, reply_message_id: str):
    try:
        message = Message.objects.get(message_id=reply_message_id)
        meal_id = message.metadata["meal_id"]
    except Message.DoesNotExist:
        text = """Please we could not get your location, can you try sending it again?
        """
        Message.bot_message_request_location(text, user, current_intent=CurrentIntentChoices.ADD_NEW_ORDER_DELIVERY_ADDRESS, metadata={"meal_id": meal_id})
        return False
    
    if data is None or data.get('latitude') is None or data.get('longitude') is None:
        text = """Please we could not get your location, can you try sending it again?
        """
        Message.bot_message_request_location(text, user, current_intent=CurrentIntentChoices.ADD_NEW_ORDER_DELIVERY_ADDRESS, metadata={"meal_id": meal_id})
        return False
    
    address = data.get('address')
    name = data.get('name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    city = City.get_city_by_coordinates(longitude, latitude)
    
    if city is None:
        text = """Please we are not in your location yet, can you try another location?
        """
        Message.bot_message_request_location(text, user, current_intent=CurrentIntentChoices.ADD_NEW_ORDER_DELIVERY_ADDRESS, metadata={"meal_id": meal_id})
        return False
    
    delivery_address = DeliveryAddress.objects.create(
        user=user,  
        point=Point(longitude, latitude, srid=4326),
        street_address=address,
        name=name
    )

    if user.city.currency.id != city.currency.id:
        text = f"Your new address has been added successfully, it falls under this city: {city.name} so we have updated your city. Please the currency for this city is {city.currency.name} please remember to update your meal budget accordingly."
        Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)
    else:
        text = f"Your new address has been added successfully, it falls under this city: {city.name}."
        Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)
    
    text = "How many plates would you like to order? pick one from the list right below."
    payload = number_of_plates(text, meal_id)
    print("Payload add_new_address_hander:", payload)
    Message.bot_message_list_option(text, user, current_intent=CurrentIntentChoices.NUMBER_OF_PLATES, payload=payload)

    return True
