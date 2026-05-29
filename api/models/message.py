from api.models.base import BaseModel
from django.db import models
from django.db.models import Q, CheckConstraint
# from api.models.user import User
import requests
from django.conf import settings
from requests.exceptions import RequestException
import random


class RoleChoices(models.TextChoices):
    USER = 'user', 'User'
    BOT = 'bot', 'Bot'


class CurrentIntentChoices(models.TextChoices):
    NO_INTENT = 'no_intent', 'No Intent'
    MENU_OPTIONS = 'menu_options', 'Menu Options'
    REGISTERED = 'registered', 'Registered'
    SET_PREFERENCE = 'set_preference', 'Set Preference'
    UPDATE_PREFERENCE = 'update_preference', 'Update Preference'
    FIRST_LOCATION = 'first_location', 'First Location'
    # FIRST_LOCATION_RETRY = 'first_location_retry', 'First Location Retry'
    RECOMMENDED_MEALS = 'recommended_meals', 'Recommended Meals'

    PICK_DELIVERY_ADDRESS_OPTION = 'pick_delivery_address_option', 'Pick Delivery Address Option'
    ADD_NEW_ORDER_DELIVERY_ADDRESS = 'add_new_order_delivery_address', 'Add New Order Delivery Address'

    NUMBER_OF_PLATES = 'number_of_plates', 'Number of Plates'
    PAY_FOR_ORDER = 'pay_for_order', 'Pay for Order'
    ORDER_PLACED = 'order_placed', 'Order Placed'

    # add order status, updates, review of the food, etc

    # TODO: Add more menu options intents eg. Order the current recommendation (first or second), see orders and status, see/update liked/hated meals, see/update preferences, etc.


class Message(BaseModel):
    message_id = models.CharField(max_length=250, unique=True)
    role = models.CharField(max_length=10, choices=RoleChoices.choices)
    content = models.TextField(null=True, blank=True)
    resp = models.JSONField(null=True, blank=True)
    preview_media = models.FileField(null=True, blank=True)
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name='messages')
    current_intent = models.CharField(max_length=100, choices=CurrentIntentChoices.choices, null=True, blank=True)
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies"
    )
    metadata = models.JSONField(null=True, blank=True)
    

    class Meta:
        ordering = ['-created_at']
        constraints = [
            CheckConstraint(
                check=(
                    Q(role=RoleChoices.USER) | 
                    (Q(role=RoleChoices.BOT) & ~Q(current_intent=None))
                ),
                name="bot_messages_require_current_intent",
            )
        ]
    
    @staticmethod
    def bot_message(content: str, user, current_intent: str):
        payload = {"body": content}
        msg_type = 'text'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message
    
    @staticmethod
    def bot_message_image(content: str, user, current_intent: str, preview_media: str):
        payload = {
            "caption": content,
            "link": preview_media,
            # "id": "",
        }
        
        msg_type = 'image'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, preview_media=preview_media, current_intent=current_intent)
        return message
    
    @staticmethod
    def bot_message_request_location(content: str, user, current_intent: str, metadata: dict=None):
        payload = {
            "type": "location_request_message",
            "body": {
                "text": content
            },
            "action": {
                "name": "send_location"
            }
        }
        msg_type = 'interactive'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent, metadata=metadata)
        return message
    
    @staticmethod
    def bot_message_location(content: str, user, current_intent: str, latitude: float, longitude: float, address: str):
        payload = {
            "latitude": latitude,
            "longitude":longitude,
            "name": content,
            "address": address
        }
        msg_type = 'location'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message
    
    @staticmethod
    def bot_message_list_option(content: str, user, current_intent: str, payload):
        msg_type = 'interactive'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message

    @staticmethod
    def bot_message_action_reply(content: str, user, current_intent: str, payload):
        msg_type = 'interactive'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message
    
    @staticmethod
    def bot_message_flow(content: str, user, current_intent: str, payload):
        # TODO: Implement
        # msg_type = 'interactive'
        # message_id = Message.send_message(user, msg_type, payload)

        message_id = str(random.randint(1000000, 9999999)) # TODO: to be removed
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message
    
    @staticmethod
    def user_message(message_id: str, resp, content: str, user, enable_typing_indicator: bool = False, reply_message_id: str=None):
        if enable_typing_indicator:
            Message.enable_typing_indicator(message_id)
        
        found_msg = None
        if reply_message_id:
            found_msg = Message.objects.filter(message_id=reply_message_id).first()
        message = Message.objects.create(role=RoleChoices.USER, message_id=message_id, resp=resp, content=content, user=user, reply_to=found_msg)
        return message
    
    @staticmethod
    def enable_typing_indicator(message_id: str):
        url = settings.WHATSAPP_MESSAGE_BASE_URL
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.WHATSAPP_API_KEY}"
        }
        data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
            "typing_indicator": {
                "type": "text"
            }
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()  # raises HTTPError for 4xx/5xx
            return response
        except RequestException as e:
            raise RuntimeError(f"Failed to enable typing indicator: {e}")
        
    @staticmethod
    def send_message(user, msg_type, payload):
        url = settings.WHATSAPP_MESSAGE_BASE_URL
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.WHATSAPP_API_KEY}"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": user.phone,
            "type": msg_type,
        }
        
        data[msg_type] = payload
            
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()  # raises HTTPError for 4xx/5xx
            return response.json().get("messages", [{}])[0].get("id")
        except RequestException as e:
            raise RuntimeError(f"Failed to send WhatsApp message: {e}")

    def __str__(self):
        return f"Message from {self.role} - {self.current_intent}: {self.content}"
