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
    role = models.CharField(max_length=10, choices=RoleChoices.choices)
    content = models.TextField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    
    @staticmethod
    def bot_message(content: str, user: User, image_url: str = None):
        print("Bot message:", content)
        message = Message.objects.create(role=RoleChoices.BOT, content=content, user=user, image_url=image_url)
        return message
    
    @staticmethod
    def user_message(content: str, user: User, image_url: str = None):
        message = Message.objects.create(role=RoleChoices.USER, content=content, user=user, image_url=image_url)
        return message
    
    def send_message(self, content, user):
        url = settings.WHATSAPP_MESSAGE_BASE_URL
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.WHATSAPP_API}"
        }
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": user.phone,  # must be full international format
            "type": "text",
            "text": {"body": content}
        }
        print(data)

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()  # raises HTTPError for 4xx/5xx
            print(response.json())
            return response
        except RequestException as e:
            raise RuntimeError(f"Failed to send WhatsApp message: {e}")

    
    def save(self, *args, **kwargs):
        is_new = self.pk is None 
        print("Message save called", self.content, self.role, is_new)
        print("Saving message, is new:", is_new, self.role, RoleChoices.BOT == self.role, RoleChoices.BOT)
        if self.role == RoleChoices.BOT and is_new:
            print("Sending bot message to user:", self.user.phone)
            self.send_message(self.content, self.user)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Message from {self.role}: {self.content[:200]}"
