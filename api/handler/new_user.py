from api.models.message import Message
from api.models.user import CurrentIntentChoices, User


def new_user_hander(phone: str):
    user = User.objects.create(phone=phone, current_intent=CurrentIntentChoices.SET_PREFERENCE)
    
    text = """Welcome to Foodie Robot! 🍽️🤖\n
    Now Please fill in your preferences so we can serve you better.
    """
    Message.bot_message_flow(text, user)
    return user
    