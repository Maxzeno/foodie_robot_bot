from typing import Optional, Dict
from django.utils import timezone
from django.db.models import Q

from api.models.user import User
from api.models.meal import Meal
from api.models.recommendation import Recommendation, ChoiceOption


def generate_meal_recommendations(
    user: User,
    time_of_day: Optional[str] = None
) -> Dict:
    try:
        # Determine time of day if not specified
        if not time_of_day:
            time_of_day = user.get_time_period()

        # Get user's city, fitness goals, allergies, health conditions
        city = user.city
        fitness_goal = user.fitness_goals
        allergies = user.allergies.all()
        health_conditions = user.health_conditions.all()
        preferred_cuisines = user.preferred_cuisine.all()
        budget = user.average_meal_budget

        # Build query
        query = Q(available=True, times_of_day__contains=[time_of_day])

        if city:
            query &= Q(city=city)

        if fitness_goal:
            query &= Q(fitness_goals=fitness_goal)

        # Exclude meals with restricted allergies or health conditions
        if allergies.exists():
            query &= ~Q(restricted_allergies__in=allergies)

        if health_conditions.exists():
            query &= ~Q(restricted_health_conditions__in=health_conditions)

        # Filter by budget if specified
        if budget:
            query &= Q(price__lte=budget)

        # Get meals
        meals = Meal.objects.filter(query).distinct()

        # Prefer meals matching cuisine preferences if available
        if preferred_cuisines.exists():
            preferred_meals = meals.filter(cuisine__in=preferred_cuisines).distinct()
            if preferred_meals.exists():
                meals = preferred_meals

        # Get 2 random meals for recommendations
        recommendations_list = list(meals.order_by('?')[:2])

        if len(recommendations_list) < 2:
            return {
                "success": False,
                "message": f"Not enough meals available for {time_of_day}. Please adjust your preferences or try a different time.",
                "recommendations": []
            }

        # Create recommendation records
        today = timezone.now().date()

        # Clear old recommendations for this time slot
        Recommendation.objects.filter(
            user=user,
            day=today,
            time_of_day=time_of_day
        ).delete()

        # Create new recommendations
        rec1 = Recommendation.objects.create(
            user=user,
            meal=recommendations_list[0],
            time_of_day=time_of_day,
            choice_option=ChoiceOption.FIRST,
            day=today
        )

        rec2 = Recommendation.objects.create(
            user=user,
            meal=recommendations_list[1],
            time_of_day=time_of_day,
            choice_option=ChoiceOption.SECOND,
            day=today
        )

        # Format response
        def format_meal(meal: Meal):
            return {
                "id": meal.id,
                "name": meal.name,
                "description": meal.description,
                "price": float(meal.price),
                "restaurant": meal.restaurant.name,
                "calories": float(meal.calories) if meal.calories else None,
                "protein": f"{float(meal.protein)}g" if meal.protein else None,
            }

        return {
            "success": True,
            "time_of_day": time_of_day,
            "recommendations": [
                format_meal(recommendations_list[0]),
                format_meal(recommendations_list[1])
            ]
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating recommendations: {str(e)}",
            "recommendations": []
        }


def get_nutritional_info(user: User, meal_id: int) -> Dict:
    try:
        meal = Meal.objects.get(id=meal_id)

        return {
            "success": True,
            "meal_id": meal_id,
            "meal_name": meal.name,
            "nutrition": {
                "calories": float(meal.calories) if meal.calories else None,
                "protein": f"{float(meal.protein)}g" if meal.protein else None,
                "carbs": f"{float(meal.carbs)}g" if meal.carbs else None,
                "fats": f"{float(meal.fats)}g" if meal.fats else None,
                "fiber": f"{float(meal.fiber)}g" if meal.fiber else None,
                "sugar": f"{float(meal.sugar)}g" if meal.sugar else None,
                "sodium": f"{float(meal.sodium)}mg" if meal.sodium else None,
                "cholesterol": f"{float(meal.cholesterol)}mg" if meal.cholesterol else None,
                "serving_size": f"{float(meal.serving_amount_g)}g" if meal.serving_amount_g else None,
            },
            "restaurant": meal.restaurant.name,
            "restricted_allergies": [a.name for a in meal.restricted_allergies.all()],
            "restricted_health_conditions": [h.name for h in meal.restricted_health_conditions.all()],
        }
    except Meal.DoesNotExist:
        return {
            "success": False,
            "message": f"Meal with ID {meal_id} not found"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting nutritional info: {str(e)}"
        }
