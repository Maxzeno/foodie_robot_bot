from api.models.base import BaseModel
from django.db import models
from django.db.models import Q, CheckConstraint
# from api.models.user import User
import requests
from django.conf import settings
from requests.exceptions import RequestException
from typing import List
import uuid

class RoleChoices(models.TextChoices):
    USER = 'user', 'User'
    BOT = 'bot', 'Bot'


class CurrentIntentChoices(models.TextChoices):
    NO_INTENT = 'no_intent', 'No intent'
    NEEDS_REPLY = 'needs_reply', 'Needs reply'
    REMINDER_MESSAGE = 'reminder_message', 'Reminder message'
    FLOW_MESSAGE = 'flow_message', 'Flow message'
    COMPLETED_REPLY = 'completed_reply', 'Completed reply' # meaning no need to add it as an ssistant reply


class Message(BaseModel):
    message_id = models.CharField(max_length=250, unique=True)
    role = models.CharField(max_length=10, choices=RoleChoices.choices)
    content = models.TextField(null=True, blank=True)
    # llm_content = models.TextField(null=True, blank=True) # smarter (usually shorter and has key info) content if set used inplace of the actually content when passed into the llm messages

    resp = models.JSONField(null=True, blank=True)
    preview_media = models.URLField(max_length=1024, null=True, blank=True)
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
        indexes = [
            # Conversation history queries (most frequent)
            models.Index(fields=['user', '-created_at'], name='msg_user_created_idx'),
            # Check if bot message exists for user
            models.Index(fields=['user', 'role'], name='msg_user_role_idx'),
            # Ordered conversation by role and time
            models.Index(fields=['user', 'role', '-created_at'], name='msg_user_role_created_idx'),
            # Reply message lookups
            models.Index(fields=['message_id'], name='msg_message_id_idx'),
            # Filter by current intent
            models.Index(fields=['user', 'current_intent'], name='msg_user_intent_idx'),
        ]

    def get_content_meta(self):
        if self.metadata:
            return f"{self.content} - metadata: {self.metadata}"
        return self.content or ""
    
    @staticmethod
    def bot_message(content: str, user, current_intent: str=CurrentIntentChoices.NO_INTENT, metadata: dict=None):
        payload = {"body": content}
        msg_type = 'text'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent, metadata=metadata)
        return message
    
    @staticmethod
    def bot_message_image(content: str, user, preview_media: str, current_intent: str=CurrentIntentChoices.NO_INTENT):
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
    def bot_message_request_location(content: str, user, current_intent: str=CurrentIntentChoices.NO_INTENT, metadata: dict=None):
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
    def bot_message_location(content: str, user, latitude: float, longitude: float, address: str, current_intent: str=CurrentIntentChoices.NO_INTENT):
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
    def bot_message_list_option(content: str, user, payload, current_intent: str=CurrentIntentChoices.NO_INTENT):
        msg_type = 'interactive'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message

    @staticmethod
    def bot_message_action_reply(content: str, user, payload, current_intent: str=CurrentIntentChoices.NO_INTENT, metadata=None):
        msg_type = 'interactive'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent, metadata=metadata)
        return message
    
    def bot_message_url_cta(content: str, action_text: str, action_url: str, user, current_intent: str=CurrentIntentChoices.NO_INTENT, metadata: dict=None):
        payload = {
            "type": "cta_url",
            "body": {
                "text": content
            },
            "action": {
            "name": "cta_url",
                "parameters": {
                    "display_text": action_text,
                    "url": action_url
                }
            },
        }
        msg_type = 'interactive'
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent, metadata=metadata)
        return message
    
    @staticmethod
    def bot_message_action_reply_simple(content: str, user, action_replies: List[str], current_intent: str=CurrentIntentChoices.NO_INTENT, metadata=None):
        msg_type = 'interactive'
        payload = {
            "type": "button",
            "body": {
                "text": content
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": reply.strip().lower().replace(" ", "-"),
                            "title": reply
                        }
                    } for reply in action_replies
                ]
            }
        }
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent, metadata=metadata)
        return message
    
    @staticmethod
    def bot_message_flow(content: str, user, flow_cta: str, flow_id: str, screen_name: str, data: dict, current_intent: str=CurrentIntentChoices.NO_INTENT):
        if screen_name not in {'ORDER_FLOW', 'USER_PROFILE', 'ORDER_REVIEW', 'WITHDRAWAL'}:
            return None
        
        msg_type = 'interactive'
        
        payload = {
            "type": "flow",
            "body": {
                "text": content
            },
            "action": {
                "name": "flow",
                "parameters": {
                    "flow_message_version": "3",
                    "flow_token": f"{uuid.uuid4().hex}--{screen_name}",
                    "flow_id": flow_id,
                    "flow_cta": flow_cta,
                    "flow_action": "navigate",
                    "flow_action_payload": {
                        "screen":  screen_name,
                        "data": data
                    }
                }
            }
        }
        message_id = Message.send_message(user, msg_type, payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=content, user=user, current_intent=current_intent)
        return message
    
    @staticmethod
    def bot_message_template(template_name: str, user, language_code = "en_US", current_intent: str=CurrentIntentChoices.NO_INTENT):
        
        payload = {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }
        
        message_id = Message.send_message(user, "template", payload)
        message = Message.objects.create(message_id=message_id, role=RoleChoices.BOT, content=template_name, user=user, current_intent=current_intent)
        return message
    
    @staticmethod
    def user_message(message_id: str, resp, content: str, user, enable_typing_indicator: bool = False, reply_message_id: str=None, current_intent: str=CurrentIntentChoices.NO_INTENT):
        if enable_typing_indicator:
            Message.enable_typing_indicator(message_id)
        
        found_msg = None
        if reply_message_id:
            found_msg = Message.objects.filter(message_id=reply_message_id).first()
        message = Message.objects.create(role=RoleChoices.USER, message_id=message_id, resp=resp, content=content, user=user, reply_to=found_msg, current_intent=current_intent)
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
            pass
        
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
            print("WhatsApp API response:", response.text)
            response.raise_for_status()  # raises HTTPError for 4xx/5xx
            return response.json().get("messages", [{}])[0].get("id")
        except RequestException as e:
            print(str(e), 'Failed to send WhatsApp message')
            raise RuntimeError(f"Failed to send WhatsApp message: {e}")

    def __str__(self):
        return f"Message from {self.role}: {self.user} - {self.current_intent}: {self.content}"
