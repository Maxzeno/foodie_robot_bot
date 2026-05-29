from api.handler.add_new_address import add_new_address_hander
from api.handler.after_recomendation import after_recommendation
from api.handler.delivery_address_option import delivery_address_option
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

from api.utils.services.meal_recommendation import MealRecommendationService


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
        print("Message:", message)

        if msg_type in {'text'}:
            text = message["text"]["body"]
        elif msg_type in {"interactive", "location"}:
            json_resp = message[msg_type]
            
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
    
    print("body:", request.body)
    
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
    
    elif user.get_intent(reply_message_id) == CurrentIntentChoices.MENU_OPTIONS:
        # TODO: Handle navigation options
        # {'type': 'list_reply', 'list_reply': {'id': 'view-orders', 'title': 'View Orders'}}
        pass

    elif user.get_intent(reply_message_id) == CurrentIntentChoices.SET_PREFERENCE:
        status = user_preference_hander(user, data=json_resp)
    
    elif user.get_intent(reply_message_id) == CurrentIntentChoices.FIRST_LOCATION:
        status = first_location_hander(user, data=json_resp)
        
    elif user.get_intent(reply_message_id) == CurrentIntentChoices.RECOMMENDED_MEALS:
        status = after_recommendation(user, data=json_resp)
    
    elif user.get_intent(reply_message_id) == CurrentIntentChoices.PICK_DELIVERY_ADDRESS_OPTION:
        status = delivery_address_option(user, data=json_resp)
    
    elif user.get_intent(reply_message_id) == CurrentIntentChoices.ADD_NEW_ORDER_DELIVERY_ADDRESS:
        status = add_new_address_hander(user, data=json_resp, reply_message_id=reply_message_id)

    return {"detail": "Done"}


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


# TODO: to be removed in production
@csrf_exempt
@router.get("/test-temp")
def text_temp_verify(request):
    user = User.objects.all()[4]
    print("User:", user)
    service = MealRecommendationService()

    # print(service._get_eligible_meals(user))

    # recommend by algo
    # print("Recommended Meal IDs - algo:", service.get_recommendations_by_algo(
    #     user=user,
    #     num_recommendations_per_period=2,
    # ))

    # recommend by LLM
    recommended_meal_ids = service.get_recommendations_by_llm(
        user=user,
        num_recommendations_per_period=2,
    )
    print("Recommended Meal IDs:", recommended_meal_ids)
    return HttpResponse("Done", status=200)
