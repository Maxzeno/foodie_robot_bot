from api.models.message import Message
from api.models.user import CurrentIntentChoices


def user_preference_hander(user, data: dict):
    # update the user preference here after validating the data
    # user.
    # after updating the preference, change the intent 
    
    user.current_intent = CurrentIntentChoices.FIRST_LOCATION
    user.save()
    
    text = """Please can what is your main location? pick on map right below.
    """
    Message.bot_message_request_location(text, user)
    return user
    