from api.models.meal import Meal
from api.models.message import CurrentIntentChoices, Message
import json
from ninja import Router
from api.models.order import Order
from api.models.user import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction
from django.conf import settings

from api.services.ai.orchestrator import FoodBotAIHandler
from api.services.recommendation.meal_recommendation import MealRecommendationService
from api.utils.nfm_reply import nfm_reply_hander
from api.utils.text_extract import extract_user_code
from api.utils.whatsapp_payload_helper.user_profile_flow_data import user_data_profile_flow
from api.utils.whatsapp_verification import verify_whatsapp_signature
from api.utils.rate_limit import check_rate_limit, RateLimitExceeded
import uuid

router = Router(tags=["Webhook"])

VERIFY_TOKEN = settings.WHATSAPP_API_VERIFY_TOKEN

@csrf_exempt
@transaction.atomic
@router.post('/whatsapp', auth=None)
def whatsapp_webhook(request):
    # Verify that the request is from WhatsApp by checking the signature
    signature = request.headers.get('X-Hub-Signature-256', '')
    if not verify_whatsapp_signature(request.body, signature):
        return HttpResponse("Forbidden: Invalid signature", status=403)

    json_data = json.loads(request.body)
    print('json_data flow', json_data)

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
            text = f"Location - name: {name or ''}, address: {address or ''}, latitude: {latitude}, longitude: {longitude}"
        
        elif msg_type == "interactive":
            interactive = message["interactive"]
            interactive_type = interactive.get("type")
            if interactive_type == "button_reply":
                text = interactive["button_reply"]["title"]
            elif interactive_type == "list_reply":
                text = interactive["list_reply"]["title"]

            elif interactive_type == "nfm_reply":
                user, created = User.objects.get_or_create(phone=phone)

                fields = interactive['nfm_reply']['response_json']
                fields = json.loads(fields)
                flow_token = fields.pop('flow_token', None)

                text = ", ".join(f"{key}: {value}" for key, value in fields.items())
                Message.user_message(message_id=sender_message_id, 
                    resp=fields, content=text, 
                    user=user, enable_typing_indicator=True, current_intent=CurrentIntentChoices.FLOW_MESSAGE)
    
                nfm_reply_hander(user, fields, flow_token)
                return {"detail": "Done"}

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

    # Rate limiting: 30 messages per minute per user
    try:
        check_rate_limit(
            user_identifier=phone,
            max_requests=30,
            window_seconds=60
        )
    except RateLimitExceeded as e:
        print(f"Rate limit exceeded for phone {phone}: {e}")
        # Return success to WhatsApp to avoid retries, but don't process the message
        # Optionally send a warning message to the user
        user_obj = User.objects.filter(phone=phone).first()
        if user_obj:
            Message.bot_message(
                "You're sending messages too quickly. Please wait a moment before trying again.",
                user=user_obj
            )
        return {"detail": "Rate limited"}

    user, created = User.objects.get_or_create(phone=phone)

    Message.user_message(message_id=sender_message_id, 
        resp=json_resp, content=text, 
        user=user, enable_typing_indicator=True, reply_message_id=reply_message_id)
    
    if created:
        user_code = extract_user_code(text)
        if user_code:
            referrer = User.objects.filter(code=user_code.lower()).first()
            if referrer and referrer != user:
                user.referred_by = referrer
                user.save()

        message = "Welcome to Foodie Robot! I'm here to help you with personalized meal recommendations. To get started, could you please fill out your user profile?"
        Message.bot_message_flow(
            message, 
            user=user,
            flow_cta="Create profile", 
            flow_id="1822264872503617", 
            screen_name="USER_PROFILE",
            data=user_data_profile_flow(user),
        )
    else:
        if text == None:
            Message.bot_message("Unsupported message type", user=user)
            return {"detail": "Done"}     
          
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


@csrf_exempt
@router.post("/whatsapp-test")
def whatsapp_test(request, text:str):
    sender_message_id = uuid.uuid4().hex
    found_msg = Message.objects.filter(message_id=sender_message_id).first()
    if found_msg:
        return {"detail": "Done"}
    
    user = User.objects.get(phone="2349077745730")

    Message.user_message(message_id=sender_message_id, 
        resp={}, content=text, 
        user=user, enable_typing_indicator=True, reply_message_id=None)
    
    response_message = FoodBotAIHandler(user, sender_message_id, None).process_message()
    if response_message:
        Message.bot_message(response_message, user=user)

    return {"detail": "Done"}

# TODO: to be removed in production
@csrf_exempt
@router.get("/test-temp-recommendation")
def text_temp_verify(request):
    user = User.objects.filter(phone="2349077745730").first()
    print("User:", user)
    service = MealRecommendationService()

    # recommend by LLM
    recommended_meal_ids = service.get_recommendations(
        user=user,
        num_recommendations_per_period=2,
    )

    res = {}
    for k, v in recommended_meal_ids.items():
        meals = Meal.objects.filter(id__in=v).values('id', 'name')
        print(f"Recommended Meals: {k} -", json.dumps(list(meals), indent=2))
        res[k] = list(meals)
    print("Recommended Meal IDs:", recommended_meal_ids)
    return res
