from api.models.message import Message
import json
from ninja import Router
from api.handler.new_user import new_user_hander
from api.models.user import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction


router = Router(tags=["Webhook"])

VERIFY_TOKEN = "0123456789dgfhjkldjhsdjksdjksdjkjsdjksdkjdssd"

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
    
    # phone = json_data['data']['phone']
    # text = json_data['data']['phone']
    
    try:
        entry = json_data["entry"][0]
        change = entry["changes"][0]["value"]

        # Sender phone number
        phone = change["messages"][0]["from"]

        # Message body (for text messages)
        text = change["messages"][0]["text"]["body"]

        print("Phone Number:", phone)
        print("Message:", text)

    except Exception as e:
        print("Error parsing webhook:", e)
        return {"detail": "Done"}
    
    
    user = User.objects.filter(phone=phone).first()
    
    if not user:
        user = new_user_hander(phone=phone)
    Message.user_message(text, user)
    
    # other handlers here

    return {"detail": "Done"}
