from api.models.message import Message
from api.models.user import CurrentIntentChoices, User


def new_user_hander(phone: str):
    text = "Your account has been created please let's know more about you"
    
    user = User.objects.create(phone=phone, current_intent=CurrentIntentChoices.REGISTERED)
    print("New user created:", user)
    Message.bot_message(text, user)
    print("Sent bot message to new user")
    
    text = """What’s your current fitness goal?
        1. Weight Loss
        2. Muscle Gain
        3. Maintenance
    """
    Message.bot_message(text, user)
    return user
    