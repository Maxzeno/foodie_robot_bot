from api.models.user import User
from api.models.message import Message, CurrentIntentChoices


def new_user_hander(phone: str, message_id: str, content:str=None, resp=None):
    user = User.objects.create(phone=phone)
    
    Message.user_message(message_id=message_id, 
            resp=resp, content=content, 
            user=user, enable_typing_indicator=True)
    
    text = """Welcome to Foodie Robot! 🍽️🤖\n
    Now Please fill in your preferences so we can serve you better.
    """
    Message.bot_message_flow(text, user, current_intent=CurrentIntentChoices.SET_PREFERENCE)
    return True
