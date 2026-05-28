from api.models.address import DeliveryAddress
from api.models.meal_preference import MealPreference, MealPreferenceChoices
from api.models.message import Message
from api.models.message import Message, CurrentIntentChoices
from api.models.order import Order
from api.models.recommendation import Recommendation
from api.utils.menu_options import show_menu_options
from api.utils.whatsapp_payload_helper.pick_delivery_option import pick_delivery_option
from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload

def after_recommendation(user, data: dict):
    # first validate the data
    try:
        action_id = data['button_reply']['id']
        action = action_id.split('--')[0]

        recommendation_id = action_id.split('--')[-1]
        recommendation_obj = Recommendation.objects.get(id=recommendation_id, user=user)
        recommendation_obj.accepted = True
        recommendation_obj.save()
    except Exception as e:   
        text = "Sorry, we could not process your action."
        # maybe also send a message to try again
        Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)
        show_menu_options(user)
        return False

    if action == 'order-now':
        latest_delivery_address = DeliveryAddress.objects.filter(user=user).first()
        
        text = f"Your current delivery address"
        Message.bot_message_location(text, user, current_intent=CurrentIntentChoices.NO_INTENT, latitude=latest_delivery_address.point.y, longitude=latest_delivery_address.point.x, address=latest_delivery_address.street_address)

        text = f"Great choice {recommendation_obj.meal.name}! Please confirm if we should use your current delivery address or you want to set a new one?"
        payload = pick_delivery_option(text, text)
        Message.bot_message_action_reply(text, user, current_intent=CurrentIntentChoices.PICK_DELIVERY_ADDRESS_OPTION, payload=payload)

    elif action == 'i-love-this-meal':
        MealPreference.objects.update_or_create(
            user=user,
            meal=recommendation_obj.meal,
            defaults={"preference": MealPreferenceChoices.LIKE},
        )
        text = "Meal added you favorites ❤️! We will remember this for future recommendations."
        Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)
        show_menu_options(user)

    elif action == 'i-hate-this-meal':
        MealPreference.objects.update_or_create(
            user=user,
            meal=recommendation_obj.meal,
            defaults={"preference": MealPreferenceChoices.HATE},
        )
        text = "Meal added to your dislikes 💔! We will remember this for future recommendations."
        Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)
        show_menu_options(user)
    return True
