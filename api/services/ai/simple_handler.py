"""
Simple AI handler - executes tools with minimal overhead
"""
import logging
from typing import Dict, Any
from api.models import User, FitnessGoal, HealthCondition, Allergy, PreferredCuisine, Message, CurrentIntentChoices
from api.utils.services.meal_recommendation import MealRecommendationService

logger = logging.getLogger(__name__)


class SimpleAIHandler:
    """Executes AI tools - focused on simplicity and low token usage"""

    def __init__(self, user: User):
        self.user = user

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool to handler"""
        handlers = {
            "save_fitness_goal": self.save_fitness_goal,
            "save_health_conditions": self.save_health_conditions,
            "save_allergies": self.save_allergies,
            "save_cuisines": self.save_cuisines,
            "request_location": self.request_location,
            "get_recommendations": self.get_recommendations,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return handler(**arguments)
        except Exception as e:
            logger.error(f"Tool error {tool_name}: {e}", exc_info=True)
            return {"error": str(e)}

    def save_fitness_goal(self, goal: str) -> Dict[str, Any]:
        """Save fitness goal"""
        goal_obj, _ = FitnessGoal.objects.get_or_create(name=goal)
        self.user.fitness_goals = goal_obj
        self.user.save()
        return {"success": True}

    def save_health_conditions(self, conditions: list) -> Dict[str, Any]:
        """Save health conditions"""
        self.user.health_conditions.clear()
        for condition in conditions:
            obj, _ = HealthCondition.objects.get_or_create(name=condition)
            self.user.health_conditions.add(obj)
        return {"success": True}

    def save_allergies(self, allergies: list) -> Dict[str, Any]:
        """Save allergies"""
        self.user.allergies.clear()
        for allergy in allergies:
            obj, _ = Allergy.objects.get_or_create(name=allergy)
            self.user.allergies.add(obj)
        return {"success": True}

    def save_cuisines(self, cuisines: list) -> Dict[str, Any]:
        """Save preferred cuisines"""
        self.user.preferred_cuisine.clear()
        for cuisine in cuisines:
            obj, _ = PreferredCuisine.objects.get_or_create(name=cuisine)
            self.user.preferred_cuisine.add(obj)
        return {"success": True}

    def request_location(self) -> Dict[str, Any]:
        """Send WhatsApp location request button"""
        text = "📍 Please share your delivery location by tapping the button below."
        Message.bot_message_request_location(
            text,
            self.user,
            current_intent=CurrentIntentChoices.FIRST_LOCATION
        )
        return {"success": True, "message": "Location request sent"}

    def get_recommendations(self) -> Dict[str, Any]:
        """Get meal recommendations"""
        if not self.user.city:
            return {"error": "Location required"}
        if not self.user.fitness_goals:
            return {"error": "Fitness goal required"}

        service = MealRecommendationService()
        recommendations_dict = service.get_recommendations_by_algo(
            user=self.user,
            num_recommendations_per_period=2
        )

        # Extract all unique meal IDs from all time periods
        all_meal_ids = set()
        for period_meals in recommendations_dict.values():
            all_meal_ids.update(period_meals)

        if not all_meal_ids:
            return {"error": "No meals available in your area"}

        # Format for AI response
        from api.models import Meal
        meals = Meal.objects.filter(id__in=all_meal_ids)
        result = []
        for meal in meals:
            result.append({
                "id": meal.id,
                "name": meal.name,
                "price": f"₦{meal.price}",
                "restaurant": meal.restaurant.name
            })

        return {"success": True, "meals": result}

    def is_onboarding_complete(self) -> bool:
        """Check if user completed onboarding"""
        # City and fitness goal are required
        # Others can be empty but must have been asked (we track this by checking if ANY were set)
        return (
            self.user.city is not None and
            self.user.fitness_goals is not None
        )

    def get_missing_fields(self) -> list:
        """Get list of missing onboarding fields"""
        missing = []
        if not self.user.city:
            missing.append("location")
        if not self.user.fitness_goals:
            missing.append("fitness_goal")

        # These are optional - only add to missing if user is brand new
        # Once user has fitness_goals, we assume these were asked
        if self.user.fitness_goals:
            # User is in onboarding, don't list these as missing
            pass
        else:
            # Brand new user, list all as missing
            missing.extend(["health_conditions", "allergies", "cuisines"])

        return missing
