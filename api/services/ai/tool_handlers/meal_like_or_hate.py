from api.models.address import DeliveryAddress
from api.models.meal import Meal
from api.models.meal_preference import MealPreference, MealPreferenceChoices
from api.models.message import Message
from api.models.message import Message, CurrentIntentChoices
from api.models.order import Order
from api.models.recommendation import Recommendation
from api.models.user import User
from api.utils.menu_options import show_menu_options
from api.utils.whatsapp_payload_helper.pick_delivery_option import pick_delivery_option
from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload


def like_or_hate_meal(user: User, meal_id: int, action: str):
    try:
        meal_obj = Meal.objects.get(id=meal_id)
    except Exception as e:   
        text = "Sorry, we could not process your request. Would you like to see the Quick Actions."
        show_menu_options(user, text)
        return False

    if action == 'like':
        MealPreference.objects.update_or_create(
            user=user,
            meal=meal_obj,
            defaults={"preference": MealPreferenceChoices.LIKE},
        )
        text = "Meal added you favorites ❤️! We will remember this for future recommendations."
        Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)
        show_menu_options(user)

    elif action == 'hate':
        MealPreference.objects.update_or_create(
            user=user,
            meal=meal_obj,
            defaults={"preference": MealPreferenceChoices.HATE},
        )
        text = "Meal added to your dislikes 💔! We will remember this for future recommendations."
        Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)
        show_menu_options(user)
    return True
