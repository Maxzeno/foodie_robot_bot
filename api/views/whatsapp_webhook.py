from api.models.message import Message
import json
from ninja import Router
from api.models.user import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction
from django.conf import settings

from api.services.ai.orchestrator import FoodBotAIHandler
from api.services.recommendation.meal_recommendation import MealRecommendationService


router = Router(tags=["Webhook"])

VERIFY_TOKEN = settings.WHATSAPP_API_VERIFY_TOKEN

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

        if msg_type == 'text':
            text = message["text"]["body"]
            
        elif msg_type == "location":
            json_resp = message[msg_type]
            address = json_resp.get('address')
            name = json_resp.get('name')
            latitude = json_resp.get('latitude')
            longitude = json_resp.get('longitude')
            text = f"Location - name: {name}, address: {address}, latitude: {latitude}, longitude: {longitude}"
        
        elif msg_type == "interactive":
            interactive = message["interactive"]
            interactive_type = interactive.get("type")
            if interactive_type == "button_reply":
                text = interactive["button_reply"]["title"]
            elif interactive_type == "list_reply":
                text = interactive["list_reply"]["title"]
            json_resp = interactive
 
        if message.get("context"):
            context = message["context"]
            reply_message_id = context["id"]
            
        print("msg type:", msg_type)
        print("Phone Number:", phone)
        print("Message:", text)
        print("sender_message_id:", sender_message_id)
        print("reply_message_id:", reply_message_id)

    except Exception as e:
        print("Error parsing webhook:", e)
        return {"detail": "Done"}
        
    found_msg = Message.objects.filter(message_id=sender_message_id).first()
    if found_msg:
        return {"detail": "Done"}
    
    user, created = User.objects.get_or_create(phone=phone)

    Message.user_message(message_id=sender_message_id, 
        resp=json_resp, content=text, 
        user=user, enable_typing_indicator=True, reply_message_id=reply_message_id)
    
    if created:
        Message.bot_message("Welcome to Foodie Robot! I'm here to help you with personalized meal recommendations. To get started, could you please share your fitness goal (weight loss, muscle gain, or maintenance)?", user=user)
    else:        
        response_message = FoodBotAIHandler(user, sender_message_id, reply_message_id).process_message()
        if response_message:
            Message.bot_message(response_message, user=user)

    return {"detail": "Done"}


@csrf_exempt
@router.get("/whatsapp")
def whatsapp_verify(request):
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return HttpResponse(challenge, status=200)

    return HttpResponse("Error: token mismatch", status=403)


# TODO: to be removed in production
@csrf_exempt
@router.get("/test-temp")
def text_temp_verify(request):
    user = User.objects.filter(phone="2349077745730").first()
    print("User:", user)
    service = MealRecommendationService()

    # recommend by LLM
    recommended_meal_ids = service.get_recommendations(
        user=user,
        num_recommendations_per_period=2,
    )
    print("Recommended Meal IDs:", recommended_meal_ids)
    return HttpResponse("Done", status=200)
