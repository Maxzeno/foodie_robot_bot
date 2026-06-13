import uuid
from api.models.meal import Meal
from api.models.message import CurrentIntentChoices, Message, RoleChoices
import json
from ninja import Router
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

router = Router(tags=["Webhook"])

VERIFY_TOKEN: str = settings.WHATSAPP_API_VERIFY_TOKEN
WHATSAPP_PHONE_NUMBER_ID: str = settings.WHATSAPP_PHONE_NUMBER_ID

@csrf_exempt
@transaction.atomic
@router.post('/whatsapp', auth=None)
def whatsapp_webhook(request):
    print("Received WhatsApp webhook")
    # Verify that the request is from WhatsApp by checking the signature
    signature = request.headers.get('X-Hub-Signature-256', '')
    if not verify_whatsapp_signature(request.body, signature):
        return HttpResponse("Forbidden: Invalid signature", status=403)

    json_data = json.loads(request.body)
    print('Webhook received:', json_data)

    try:
        entry = json_data["entry"][0]
        change = entry["changes"][0]["value"]
        if change.get("messages") is None:
            return {"detail": "Done"}
        
        message = change["messages"][0]

        try:
            phone_number_id: str = change['metadata']['phone_number_id']
            if phone_number_id.strip().lower() != WHATSAPP_PHONE_NUMBER_ID.strip().lower():
                return {"detail": "Skipped: Not for this service"}
        except Exception as e:
            print("Error extracting phone number ID:", e)
            return {"detail": "Skipped: No phone number ID"}
        
        try:
            username = change["contacts"][0]['profile']['name']
        except:
            username = None

        msg_type = message['type']

        phone = message["from"]
        sender_message_id = message["id"]
        reply_message_id = None
        text = None
        json_resp = None
        
        # Rate limiting: 30 messages per minute per user
        try:
            check_rate_limit(
                user_identifier=phone,
                max_requests=30,
                window_seconds=60
            )
        except RateLimitExceeded as e:
            # Return success to WhatsApp to avoid retries, but don't process the message
            # Note: We intentionally don't send a warning message here to avoid
            # creating more messages when user is already spamming
            return {"detail": "Rate limited"}

        if msg_type == 'text':
            text = message["text"]["body"]
         
        elif msg_type == "location":
            json_resp = message[msg_type]
            address = json_resp.get('address')
            name = json_resp.get('name')
            latitude = json_resp.get('latitude')
            longitude = json_resp.get('longitude')
            text = f"Location - name: {name or ''}, address: {address or ''}, latitude: {latitude}, longitude: {longitude}"
        
        elif msg_type == "button":
            json_resp = message[msg_type]
            text = json_resp.get('text') or ''
        
        elif msg_type == "interactive":
            interactive = message["interactive"]
            interactive_type = interactive.get("type")
            if interactive_type == "button_reply":
                text = interactive["button_reply"]["title"]
            elif interactive_type == "list_reply":
                text = interactive["list_reply"]["title"]

            elif interactive_type == "nfm_reply":
                user, created = User.objects.get_or_create(phone=phone)

                if user.is_blocked:
                    return {"detail": "Done"}

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

    except Exception as e:
        print("Error parsing webhook:", e)
        return {"detail": "Done"}

    found_msg = Message.objects.filter(message_id=sender_message_id).first()
    if found_msg:
        return {"detail": "Done"}

    user, created = User.objects.get_or_create(phone=phone)

    if user.is_blocked:
        return {"detail": "Done"}

    if username and not user.username:
        user.username = username
        user.save(update_fields=['username'])

    Message.user_message(message_id=sender_message_id, 
        resp=json_resp, content=text, 
        user=user, enable_typing_indicator=True, reply_message_id=reply_message_id)

    found_bot_msg = Message.objects.filter(user=user, role=RoleChoices.BOT).exists()

    if not found_bot_msg:
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
            flow_id=settings.WHATSAPP_FLOW_USER_PROFILE,
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

# # TODO: to be removed in production
@csrf_exempt
@router.get("/whatsapp-test-template")
def whatsapp_test_template(request):
    user = User.objects.get(phone="2349077745730")
    Message.bot_message_template("still_want_meal_recommendations", user=user)
    return {"detail": "Done"}

# # TODO: to be removed in production
@csrf_exempt
@router.get("/test-temp-recommendation")
def text_temp_recommendation(request):
    user = User.objects.filter(phone="2349077745730").first()
    print("User:", user)
    service = MealRecommendationService()
    # service = HybridMealRecommendationService()


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

# # TODO: to be removed in production
# @csrf_exempt
# @router.get("/test-temp-time")
# def text_temp_time(request):
#     user = User.objects.filter(phone="2349077745730").first()
#     print("User:", user)
#     print("User:", user.get_local_time(), user.get_local_time().hour)
#     print('now', timezone.now(), timezone.now().hour)
 
#     return {"status": 'ok'}
