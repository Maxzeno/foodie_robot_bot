from typing import List, Optional, Dict
from django.utils import timezone
from django.db.models import Q
from django.contrib.gis.geos import Point

from api.models.user import User
from api.models.meal import Meal, FitnessGoal, HealthCondition, Allergy, PreferredCuisine
from api.models.recommendation import Recommendation, ChoiceOption
from api.models.location import City
from api.models.message import CurrentIntentChoices, Message
from api.models.address import DeliveryAddress


def check_onboarding_status(user: User) -> str:
    missing_items = []

    # Check fitness goal
    if not user.fitness_goals:
        missing_items.append("fitness_goal")

    # Check health conditions
    if not user.health_conditions.exists():
        missing_items.append("health_conditions")

    # Check allergies
    if not user.allergies.exists():
        missing_items.append("allergies")

    # Check cuisine preferences
    if not user.preferred_cuisine.exists():
        missing_items.append("cuisine_preferences")

    # Check delivery location (city)
    if not user.city:
        missing_items.append("delivery_location")

    # If onboarding complete, return empty string
    if len(missing_items) == 0:
        return "If there is no other user request or question, you can ask if you should recommend meals."

    # Build instruction for what to ask next
    next_item = missing_items[0]
    first_part = "Never recommend till you finish onboarding even on user request. \nAfter processing the current request,"
    item_prompts = {
        "fitness_goal": f"{first_part} ask for their fitness goal (weight loss, muscle gain, or maintenance).",
        "health_conditions": f"{first_part} ask if they have any health conditions (diabetes, hypertension, etc.).",
        "allergies": f"{first_part} ask if they have any food allergies (peanuts, seafood, dairy, etc.).",
        "cuisine_preferences": f"{first_part} ask what cuisines they prefer (Nigerian, Italian, Chinese, etc.).",
        "delivery_location": f"{first_part} ask them to share their delivery location (make sure to use the request_delivery_location tool)."
    }

    instruction = f"{item_prompts.get(next_item, '')}"

    return instruction


def save_fitness_goal(user: User, fitness_goal: str) -> Dict:
    try:
        fitness_goal_obj = FitnessGoal.objects.filter(name=fitness_goal).first()
        if not fitness_goal_obj:
            return {
                "success": False,
                "message": f"Fitness goal '{fitness_goal}' not found"
            }

        user.fitness_goals = fitness_goal_obj
        user.save()

        return {
            "success": True,
            "message": f"Fitness goal saved: {fitness_goal_obj.get_name_display()}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error saving fitness goal: {str(e)}"
        }


def save_health_conditions(user: User, health_conditions: List[str]) -> Dict:
    try:
        if not health_conditions:
            user.health_conditions.clear()
            return {
                "success": True,
                "message": "Health conditions cleared"
            }

        health_objs = HealthCondition.objects.filter(name__in=health_conditions)
        user.health_conditions.set(health_objs)

        return {
            "success": True,
            "message": f"Saved {len(health_objs)} health condition(s)"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error saving health conditions: {str(e)}"
        }


def save_allergies(user: User, allergies: List[str]) -> Dict:
    try:
        if not allergies:
            user.allergies.clear()
            return {
                "success": True,
                "message": "Allergies cleared"
            }

        allergy_objs = Allergy.objects.filter(name__in=allergies)
        user.allergies.set(allergy_objs)

        return {
            "success": True,
            "message": f"Saved {len(allergy_objs)} allergy/allergies"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error saving allergies: {str(e)}"
        }


def save_cuisine_preferences(user: User, cuisine_preferences: List[str]) -> Dict:
    try:
        if not cuisine_preferences:
            user.preferred_cuisine.clear()
            return {
                "success": True,
                "message": "Cuisine preferences cleared"
            }

        cuisine_objs = PreferredCuisine.objects.filter(name__in=cuisine_preferences)
        user.preferred_cuisine.set(cuisine_objs)

        return {
            "success": True,
            "message": f"Saved {len(cuisine_objs)} cuisine preference(s)"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error saving cuisine preferences: {str(e)}"
        }


def save_delivery_location(
    user: User,
    latitude: float,
    longitude: float,
    name: Optional[str] = None,
    address: Optional[str] = None
) -> Dict:
    try:
        # Detect city from coordinates
        city = City.get_city_by_coordinates(longitude, latitude)

        if not city:
            return {
                "success": False,
                "message": "Sorry, we're not currently available in your location. Please try a different address or check back later!"
            }

        # Update user's city
        user.city = city
        user.save()

        # Create or update delivery address
        point = Point(longitude, latitude, srid=4326)

        # Create new default address
        DeliveryAddress.objects.create(
            user=user,
            point=point,
            name=name,
            street_address=address,
            is_default=False
        )

        return {
            "success": True,
            "message": f"Great! Your location has been saved in {city.name}, {city.state.name}. We'll recommend meals in your area!"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error saving delivery location: {str(e)}"
        }


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

def request_delivery_location(user: User, message_to_user: str) -> Dict:
    try:
        message = Message.bot_message_request_location(
            content=message_to_user or "Please share your delivery location.",
            user=user,
            current_intent=CurrentIntentChoices.ADD_NEW_ORDER_DELIVERY_ADDRESS,
        )
        if message:
            return {
                "success": True,
                "message": "Location request message has been sent to the user so do not respond with anything to this message if you most return something let it be an empty string",
            }
        else:
            return {
                "success": False,
                "message": "Failed to send location request message",
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error requesting delivery location"
        }
    