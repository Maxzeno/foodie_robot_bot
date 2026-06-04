from api.models.user import User
from api.models.meal import FitnessGoal, HealthCondition, Allergy, PreferredCuisine


def user_data_profile_flow(user: User):
    fitness_goals = [
        {"id": str(fg.id), "title": fg.get_name_display()}
        for fg in FitnessGoal.objects.all()
    ]

    # Get all available health conditions
    health_conditions = [
        {"id": str(hc.id), "title": hc.get_name_display()}
        for hc in HealthCondition.objects.all()
    ]

    # Get all available allergies
    allergies_diet = [
        {"id": str(allergy.id), "title": allergy.get_name_display()}
        for allergy in Allergy.objects.all()
    ]

    # Get all available cuisines
    preferred_cuisines = [
        {"id": str(cuisine.id), "title": cuisine.get_name_display()}
        for cuisine in PreferredCuisine.objects.all()
    ]

    # Get user's selected fitness goal
    selected_fitness_goal = str(user.fitness_goals.id) if user.fitness_goals else ""

    # Get user's current meal budget
    current_meal_budget = float(user.average_meal_budget) if user.average_meal_budget else 0

    # Get user's selected health conditions
    selected_health_conditions = [
        str(hc.id) for hc in user.health_conditions.all()
    ]

    # Get user's selected allergies
    selected_allergies_diet = [
        str(allergy.id) for allergy in user.allergies.all()
    ]

    # Get user's selected preferred cuisines
    selected_preferred_cuisines = [
        str(cuisine.id) for cuisine in user.preferred_cuisine.all()
    ]

    # Get currency helper text from user's city
    currency_code = user.city.currency.code if user.city and user.city.currency else "USD"
    currency_helper = f"Enter amount per meal ({currency_code})"

    return {
        "fitness_goals": fitness_goals,
        "health_conditions": health_conditions,
        "allergies_diet": allergies_diet,
        "preferred_cuisines": preferred_cuisines,
        "selected_fitness_goal": selected_fitness_goal,
        "current_meal_budget": current_meal_budget,
        "selected_health_conditions": selected_health_conditions,
        "selected_allergies_diet": selected_allergies_diet,
        "selected_preferred_cuisines": selected_preferred_cuisines,
        "currency_helper": currency_helper,
    }
    