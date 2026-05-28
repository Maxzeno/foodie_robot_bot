from api.models.base import BaseModel
from django.db import models

from api.models.user import User
import requests
from django.conf import settings
from requests.exceptions import RequestException


class RoleChoices(models.TextChoices):
    USER = 'user', 'User'
    BOT = 'bot', 'Bot'


class Message(BaseModel):
    # TODO: Add more fields (eg. reply_to another message)
    message_id = models.CharField(max_length=250)
    role = models.CharField(max_length=10, choices=RoleChoices.choices)
    content = models.TextField(null=True, blank=True)
    resp = models.JSONField(null=True, blank=True)
    preview_media = models.FileField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    
    @staticmethod
    def bot_message(content: str, user: User, preview_media: str = None):
        print("Bot message:", content)
        payload = {"body": content}
        msg_type = 'text'
        Message.send_message(user, msg_type, payload)
        message = Message.objects.create(role=RoleChoices.BOT, content=content, user=user, preview_media=preview_media)
        return message
    
    @staticmethod
    def bot_message_request_location(content: str, user: User, preview_media: str = None):
        print("Bot message request location:", content)
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
        Message.send_message(user, msg_type, payload)
        message = Message.objects.create(role=RoleChoices.BOT, content=content, user=user, preview_media=preview_media)
        return message
    
    @staticmethod
    def bot_message_list_option(content: str, user: User, preview_media: str = None):
        # TODO: Implement
        print("Bot message list option:", content)
        message = Message.objects.create(role=RoleChoices.BOT, content=content, user=user, preview_media=preview_media)
        return message
        
    @staticmethod
    def bot_message_action_reply(content: str, user: User, preview_media: str = None):
        # TODO: Implement
        print("Bot message action reply:", content)
        message = Message.objects.create(role=RoleChoices.BOT, content=content, user=user, preview_media=preview_media)
        return message
    
    @staticmethod
    def bot_message_flow(content: str, user: User, preview_media: str = None):
        # TODO: Implement
        print("Bot message flow:", content)
        message = Message.objects.create(role=RoleChoices.BOT, content=content, user=user, preview_media=preview_media)
        return message
    
    @staticmethod
    def user_message(message_id: str, resp, content: str, user: User):
        message = Message.objects.create(role=RoleChoices.USER, message_id=message_id, resp=resp, content=content, user=user)
        return message
    
    @staticmethod
    def send_message(self, user, msg_type, payload):
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
            
        print(data)

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()  # raises HTTPError for 4xx/5xx
            print(response.json())
            return response
        except RequestException as e:
            raise RuntimeError(f"Failed to send WhatsApp message: {e}")

    def __str__(self):
        return f"Message from {self.role}: {self.content[:200]}"
