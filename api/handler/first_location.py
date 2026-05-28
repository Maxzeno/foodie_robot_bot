from api.models.message import Message
from api.models.user import CurrentIntentChoices


def first_location_hander(user, data: dict):
    # after validating the data, add the delivery location and get the city it fall under then set it on the user 
    # also from the city get the user currency and set it on the user
    # user.city = 
    
    if not user.city:
        user.current_intent = CurrentIntentChoices.FIRST_LOCATION_RETRY
        user.save()
        text = """Please we are not in your location yet, can you try another location?
        """
        Message.bot_message_request_location(text, user)
        return user
    
    text = """Your location has been set successfully [the city name]. We can now start recommending meals 🍽️🤖
    """
    Message.bot_message(text, user)
    
    # recommend 2 meals for that time of the day
    user.current_intent = CurrentIntentChoices.RECOMMENDED_MEALS
    user.save()
    text = ""
    Message.bot_message_action_reply(text, user)
    return user
    