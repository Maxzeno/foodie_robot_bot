from api.models.message import Message
from api.models.message import CurrentIntentChoices
from api.utils.whatsapp_payload_helper.show_menu_options import pick_delivery_option


def show_menu_options(user, text="Here are some quick actions menu"):
    payload = pick_delivery_option(text)
    Message.bot_message_list_option(text, user, current_intent=CurrentIntentChoices.MENU_OPTIONS, payload=payload)
