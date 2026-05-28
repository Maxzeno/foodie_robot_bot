from api.models.base import BaseModel
from django.db import models
from django.db.models import Q, CheckConstraint
# from api.models.user import User
import requests
from django.conf import settings
from requests.exceptions import RequestException



class RoleChoices(models.TextChoices):
    USER = 'user', 'User'
    BOT = 'bot', 'Bot'


class CurrentIntentChoices(models.TextChoices):
    NO_INTENT = 'no_intent', 'No Intent'
    REGISTERED = 'registered', 'Registered'
    SET_PREFERENCE = 'set_preference', 'Set Preference'
    UPDATE_PREFERENCE = 'update_preference', 'Update Preference'
    FIRST_LOCATION = 'first_location', 'First Location'
    FIRST_LOCATION_RETRY = 'first_location_retry', 'First Location Retry'
    RECOMMENDED_MEALS = 'recommended_meals', 'Recommended Meals'

    # def get_intent_summary(intent):
    #     summaries = {
    #         CurrentIntentChoices.REGISTERED: "User has registered",
    #         CurrentIntentChoices.SET_PREFERENCE: "Setting user preferences",
    #         CurrentIntentChoices.UPDATE_PREFERENCE: "Updating user preferences",
    #         CurrentIntentChoices.FIRST_LOCATION: "Setting user's first location",
    #         CurrentIntentChoices.FIRST_LOCATION_RETRY: "Retrying to set user's first location",
    #         CurrentIntentChoices.RECOMMENDED_MEALS: "Recommending meals to user",
    #     }
    #     return summaries.get(intent, "Unknown intent")


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
    def bot_message_request_location(content: str, user, current_intent: str):
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
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message
    
    @staticmethod
    def bot_message_location(content: str, user, current_intent: str):
        # TODO: Implement
        message = Message.objects.create(role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message
    
    @staticmethod
    def bot_message_list_option(content: str, user, current_intent: str):
        # TODO: Implement
        message = Message.objects.create(role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message

    @staticmethod
    def bot_message_action_reply(content: str, user, current_intent: str, payload):
        msg_type = 'interactive'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message
    
    @staticmethod
    def bot_message_flow(content: str, user, current_intent: str):
        # TODO: Implement
        message = Message.objects.create(role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
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
            "Authorization": f"Bearer {settings.WHATSAPP_API}"
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
            "Authorization": f"Bearer {settings.WHATSAPP_API}"
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
