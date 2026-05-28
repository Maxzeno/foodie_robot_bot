from api.handler.first_location import first_location_hander
from api.handler.user_preference import user_preference_hander
from api.models.message import Message, CurrentIntentChoices
import json
from ninja import Router
from api.handler.new_user import new_user_hander
from api.models.user import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction
from django.conf import settings


router = Router(tags=["Webhook"])

VERIFY_TOKEN = settings.WHATSAPP_API_VERIFY_TOKEN

@csrf_exempt
@router.get("/whatsapp")
def whatsapp_verify(request):
    print("Verifying webhook", request.GET)
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return HttpResponse(challenge, status=200)

    return HttpResponse("Error: token mismatch", status=403)


@csrf_exempt
@transaction.atomic
@router.post('/whatsapp', auth=None)
def whatsapp_webhook(request):
    json_data = json.loads(request.body)

    try:
        entry = json_data["entry"][0]
        change = entry["changes"][0]["value"]
        message = change["messages"][0]
        msg_type = message['type']

        phone = message["from"]
        sender_message_id = message["id"]
        reply_message_id = None
        text = None
        json_resp = None
        
        if msg_type in ['text']:
            text = message["text"]["body"]
        else:
            if msg_type == 'location':
                json_resp = message["location"]

        if message.get("context"):
            context = message["context"]
            reply_message_id = context["id"]
            
        print("msg type:", msg_type)
        print("Phone Number:", phone)
        print("Message:", text)
        print("sender_message_id:", sender_message_id)
        print("reply_message_id:", reply_message_id)
        print("JSON resp:", json_resp)

    except Exception as e:
        print("Error parsing webhook:", e)
        return {"detail": "Done"}
    
    print(request.body)
    
    found_msg = Message.objects.filter(message_id=sender_message_id).first()
    
    if found_msg:
        return {"detail": "Done"}
    
    user = User.objects.filter(phone=phone).first()
    if user:
        Message.user_message(message_id=sender_message_id, 
            resp=json_resp, content=text, 
            user=user, enable_typing_indicator=True, reply_message_id=reply_message_id)
            
    # Handlers here
    if not user:
        status = new_user_hander(phone=phone, message_id=sender_message_id, content=text, resp=json_resp)
    
    elif user.get_intent(reply_message_id) == CurrentIntentChoices.SET_PREFERENCE:
        status = user_preference_hander(user, data=json_resp)
    
    elif (user.get_intent(reply_message_id) == CurrentIntentChoices.FIRST_LOCATION 
          or user.get_intent(reply_message_id) == CurrentIntentChoices.FIRST_LOCATION_RETRY):
        status = first_location_hander(user, data=json_resp)
        
    elif user.get_intent(reply_message_id) == CurrentIntentChoices.RECOMMENDED_MEALS:
        pass
        
    return {"detail": "Done"}
