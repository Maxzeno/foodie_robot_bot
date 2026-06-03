from api.models.meal import Meal
from api.models.meal_preference import MealPreference, MealPreferenceChoices
from api.models.message import Message
from api.models.message import Message, CurrentIntentChoices
from api.models.user import User


def like_or_hate_meal(user: User, meal_id: int, action: str):
    try:
        meal_obj = Meal.objects.get(id=meal_id)

        if action == 'like':
            MealPreference.objects.update_or_create(
                user=user,
                meal=meal_obj,
                defaults={"preference": MealPreferenceChoices.LIKE},
            )
            text = "Meal added you favorites ❤️! We will remember this for future recommendations."
            Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)

        elif action == 'hate':
            MealPreference.objects.update_or_create(
                user=user,
                meal=meal_obj,
                defaults={"preference": MealPreferenceChoices.HATE},
            )
            text = "Meal added to your dislikes 💔! We will remember this for future recommendations."
            Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)
        return True
    
    except Exception as e:   
        text = "Sorry, an error occured while trying to process your request please try again."
        Message.bot_message(text, user, current_intent=CurrentIntentChoices.NO_INTENT)
        return False