from typing import Dict

from api.models.message import Message
from api.models.user import User
from api.models.meal import Meal, TimeOfDayChoices
from api.models.recommendation import Recommendation, ChoiceOption
from api.services.recommendation.meal_recommendation import MealRecommendationService
from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload


def meal_recommendations(
    user: User,
) -> Dict:
    time_of_day = user.get_time_period()
    try:
        found_recommendations = Recommendation.objects.filter(user=user, time_of_day=time_of_day, day=user.get_local_time())[:2]
        if found_recommendations:
            for recom in found_recommendations:
                meal = recom.meal
                text = f"Your {recom.choice_option.lower()} {time_of_day} meal recommendation, {meal.name}, Meal Cost {meal.price:,.2f}"
                image_url = meal.image_url.url if meal.image_url else None
                meal_id = str(meal.id)
                
                payload = recommend_product_payload(recom.id, text, image_url)

                Message.bot_message_action_reply(text, user,
                    payload=payload,
                    metadata={
                        "meal_id": meal_id, 
                        "recomendation_id": recom.id,
                        "description": "Users can order, like or hate meal"
                        }
                )
            return True
        
        if user.city == None:
            Message.bot_message_request_location(
            content="To start getting meal recommendations, please share your delivery location.",
            user=user,
        )
            
        service = MealRecommendationService()
        
        recommended_meal_dict = service.get_recommendations(
            user=user,
            num_recommendations_per_period=2,
        )
        
        recommended_meals = Meal.objects.filter(id__in=recommended_meal_dict.get(time_of_day, []))
        
        for index, meal in enumerate(recommended_meals):
            text = f"Your {'first' if index == 0 else 'second'} {user.get_time_period()} meal recommendation, {meal.name}"
            image_url = meal.image_url.url if meal.image_url else None
            meal_id = str(meal.id)
            
            recomendation_obj = Recommendation.objects.create(
                user=user,
                meal=meal,
                time_of_day=TimeOfDayChoices.get_period(time_of_day),
                choice_option=ChoiceOption.FIRST if index == 0 else ChoiceOption.SECOND,
                sent_to_user=True if user.get_time_period() == time_of_day else False,
                day=user.get_local_time()
            )

            if user.get_time_period() == time_of_day:
                payload = recommend_product_payload(recomendation_obj.id, text, image_url)

                Message.bot_message_action_reply(text, user,
                    payload=payload,
                    metadata={
                        "meal_id": meal_id, 
                        "recomendation_id": recomendation_obj.id,
                        "description": "Users can order, like or hate meal"
                        }
                )
        return True

    except Exception as e:
        Message.bot_message("Error generating meal recommendations", user=user)
        return False


def get_nutritional_info(user: User, meal_id: int) -> Dict:
    try:
        meal = Meal.objects.get(id=meal_id)
        Message.bot_message(
            f"Nutritional info for {meal.name}: "
            f"Calories: {float(meal.calories) if meal.calories else 'N/A'}, "
            f"Protein: {f'{float(meal.protein)}g' if meal.protein else 'N/A'}, "
            f"Carbs: {f'{float(meal.carbs)}g' if meal.carbs else 'N/A'}, "
            f"Fats: {f'{float(meal.fats)}g' if meal.fats else 'N/A'}, "
            f"Fiber: {f'{float(meal.fiber)}g' if meal.fiber else 'N/A'}, "
            f"Sugar: {f'{float(meal.sugar)}g' if meal.sugar else 'N/A'}, "
            f"Sodium: {f'{float(meal.sodium)}mg' if meal.sodium else 'N/A'}, "
            f"Cholesterol: {f'{float(meal.cholesterol)}mg' if meal.cholesterol else 'N/A'}, "
            f"Serving Size: {f'{float(meal.serving_amount_g)}g' if meal.serving_amount_g else 'N/A'}, "
            
            f"allergies: {', '.join([a.name for a in user.allergies.all()])}, "
            f"fitness_goals: {user.fitness_goals}, "
            f"health_conditions: {', '.join([h.name for h in user.health_conditions.all()])}, "
            f"preferred_cuisines: {', '.join([c.name for c in user.preferred_cuisine.all()])}, ",
            user=user
        )
        return True
    except Meal.DoesNotExist:
        Message.bot_message("Meal info not found", user=user)
        
        return False
    except Exception as e:
        Message.bot_message("Error fetching nutritional info", user=user)
        return False
