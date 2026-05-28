from api.handler.first_location import first_location_hander
from api.handler.user_preference import user_preference_hander
from api.models.message import Message
import json
from ninja import Router
from api.handler.new_user import new_user_hander
from api.models.user import CurrentIntentChoices, User
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
    print(request.body)
    json_data = json.loads(request.body)

    try:
        entry = json_data["entry"][0]
        change = entry["changes"][0]["value"]
        message = change["messages"][0]
        msg_type = message['type']

        phone = message["from"]
        sender_message_id = message["id"]
        
        if msg_type in set('text'):
            text = message["text"]["body"]
        else:
            if msg_type == 'location':
                json_resp = message["location"]

        print("Phone Number:", phone)
        print("Message:", text)
        print("JSON resp:", json_resp)

    except Exception as e:
        print("Error parsing webhook:", e)
        return {"detail": "Done"}
    
    Message.user_message(message_id=sender_message_id, resp=json_resp, content=text, user=user)
    user = User.objects.filter(phone=phone).first()
    
    # Handlers here
    if not user:
        user = new_user_hander(phone=phone)
    
    elif user.current_intent == CurrentIntentChoices.SET_PREFERENCE:
        user = user_preference_hander(user, data=json_resp)
    
    elif (user.current_intent == CurrentIntentChoices.FIRST_LOCATION 
          or user.current_intent == CurrentIntentChoices.FIRST_LOCATION_RETRY):
        user = first_location_hander(user, data=json_resp)
        
    elif user.current_intent == CurrentIntentChoices.RECOMMENDED_MEALS:
        pass
        
    return {"detail": "Done"}
