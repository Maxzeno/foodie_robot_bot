from api.models.message import Message
from api.utils.whatsapp_payload_helper.show_menu_options import show_menu_options_payload


def show_menu_options(user, text="Here are some quick actions menu"):
    payload = show_menu_options_payload(text)
    Message.bot_message_list_option(text, user, payload=payload)
