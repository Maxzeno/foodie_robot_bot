from api.models.message import Message
from api.models.message import Message, CurrentIntentChoices


def user_preference_hander(user, data: dict):
    # update the user preference here after validating the data
    # user.pref...
    
    text = """Please what is your main location (Home or office)? pick on map right below.
    """
    Message.bot_message_request_location(text, user, current_intent=CurrentIntentChoices.FIRST_LOCATION)
    return True
