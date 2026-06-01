from typing import List, Dict

from api.models.message import Message
from api.models.user import User
from api.models.meal import AllergyChoices, CuisineChoices, FitnessGoal, HealthCondition, Allergy, HealthConditionChoices, PreferredCuisine


def save_fitness_goal(user: User, fitness_goal: str) -> Dict:
    is_new = user.city is None
    try:
        fitness_goal = fitness_goal.replace(" ", "_").lower()

        fitness_goal_obj = FitnessGoal.objects.filter(name=fitness_goal).first()
        if not fitness_goal_obj:
            Message.bot_message("We couldn't find the fitness goal you specified. Please try again (weight loss, muscle gain, or maintenance)?", user=user)
            return False

        user.fitness_goals = fitness_goal_obj
        user.save()
        if is_new:
            Message.bot_message(f"Fitness goal set to {fitness_goal_obj.get_name_display()}. From the list please list any health conditions you have {', '.join(HealthConditionChoices.labels)}", user=user)
        else: 
            Message.bot_message(f"Fitness goal updated to {fitness_goal_obj.get_name_display()}.", user=user)
        return True
    except Exception as e:
        Message.bot_message("Something went wrong while trying to set your fitness goal. Please try again (weight loss, muscle gain, or maintenance)?", user=user)
        return False


def save_health_conditions(user: User, health_conditions: List[str]) -> Dict:
    is_new = user.city is None
    try:
        health_conditions = [item.replace(" ", "_") for item in health_conditions]

        if not health_conditions:
            user.health_conditions.clear()
            if is_new:
                Message.bot_message(f"Health conditions set successfully. From the list please list any Allergies {', '.join(AllergyChoices.labels)}", user=user)
            else:
                Message.bot_message("Health conditions updated successfully.", user=user)
            return True

        health_objs = HealthCondition.objects.filter(name__in=health_conditions)
        user.health_conditions.set(health_objs)
        if is_new:
            Message.bot_message(f"Health conditions set successfully. From the list please list any Allergies {', '.join(AllergyChoices.labels)}", user=user)
        else:
            Message.bot_message("Health conditions updated successfully.", user=user)
            
        return True
    except Exception as e:
        Message.bot_message(f"Something went wrong when trying to set health conditions. Please try again {', '.join(HealthConditionChoices.labels)}", user=user)
        return False


def save_allergies(user: User, allergies: List[str]) -> Dict:
    is_new = user.city is None
    try:
        allergies = [item.replace(" ", "_") for item in allergies]
            
        if not allergies:
            user.allergies.clear()
            if is_new:
                Message.bot_message(f"Allergies set successfully. From the list please list any preferred cuisines {', '.join(CuisineChoices.labels)}", user=user)
            else:
                Message.bot_message("Allergies updated successfully.", user=user)
            return True

        allergy_objs = Allergy.objects.filter(name__in=allergies)
        user.allergies.set(allergy_objs)
        if is_new:
            Message.bot_message(f"Allergies set successfully. From the list please list any preferred cuisines {', '.join(CuisineChoices.labels)}", user=user)
        else:
            Message.bot_message("Allergies updated successfully.", user=user)
        return True
    except Exception as e:
        Message.bot_message(f"Something went wrong when trying to set allergies. Please try again {', '.join(AllergyChoices.labels)}", user=user)
        return False


def save_cuisine_preferences(user: User, cuisine_preferences: List[str]) -> Dict:
    is_new = user.city is None

    try:
        cuisine_preferences = [item.replace("/", "_") for item in cuisine_preferences]

        if not cuisine_preferences:
            user.preferred_cuisine.clear()
            if is_new:
                Message.bot_message_request_location("Preferred cuisine set successfully. Please click the button below to send us your main delivery location.", user=user)
            else:
                Message.bot_message("Preferred cuisine updated successfully.", user=user)
            return True

        cuisine_objs = PreferredCuisine.objects.filter(name__in=cuisine_preferences)
        user.preferred_cuisine.set(cuisine_objs)

        if is_new:
            Message.bot_message_request_location("Preferred cuisine set successfully. Please click the button below to send us your main delivery location.", user=user)
        else:
            Message.bot_message("Preferred cuisine updated successfully.", user=user)
        return True
        
    except Exception as e:
        Message.bot_message(f"Something went wrong when trying to set preferred cuisine. Please try again {', '.join(CuisineChoices.labels)}", user=user)
        return False

