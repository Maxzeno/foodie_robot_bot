from api.models.meal import Meal
from api.models.user import User
from api.models.message import Message, CurrentIntentChoices
from api.utils.menu_options import show_menu_options
from api.utils.whatsapp_payload_helper.number_of_plates import number_of_plates


def delivery_address_option(user, data: dict):
    # first validate the data
    try:
        action_id = data['button_reply']['id']
        action = action_id.split('--')[0]

        meal_id = action_id.split('--')[-1]
        meal_obj = Meal.objects.get(id=meal_id)
    except Exception as e:   
        text = "Sorry, we could not process your request. Would you like to the Quick Actions."
        show_menu_options(user, text)
        return False

    if action == 'current-address':
        text = "Great! How many plates would you like to order? pick one from the list right below."
        payload = number_of_plates(text, meal_id)
        Message.bot_message_list_option(text, user, current_intent=CurrentIntentChoices.NUMBER_OF_PLATES, payload=payload)

    elif action == 'new-address':
        text = "Please what is your delivery location? click on button right below."
        Message.bot_message_request_location(text, user, current_intent=CurrentIntentChoices.ADD_NEW_ORDER_DELIVERY_ADDRESS, metadata={"meal_id": meal_id})

    elif action == 'see-all-manu-options':
        show_menu_options(user)
    return True
