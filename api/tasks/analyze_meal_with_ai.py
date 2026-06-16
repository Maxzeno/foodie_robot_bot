import logging
from django import db
from huey.contrib.djhuey import task
from cloudinary.utils import cloudinary_url
from django.conf import settings

logger = logging.getLogger(__name__)


@task()
def analyze_meal_with_ai_task(meal_id):
    """
    Task to analyze meal with OpenAI API and update nutritional information.

    Args:
        meal_id: ID of the meal to analyze
    """
    # Close stale database connections
    db.close_old_connections()

    try:
        from api.models.meal import Meal, FitnessGoal, HealthCondition, Allergy, PreferredCuisine
        from api.services.ai.meal_analyzer import MealAnalyzer

        # Fetch the meal
        try:
            meal = Meal.objects.get(pk=meal_id)
        except Meal.DoesNotExist:
            logger.error(f"Meal {meal_id} not found for AI analysis")
            return

        # Check if meal has required fields
        if not meal.name or not meal.image_url:
            logger.info(f"Skipping AI analysis for meal {meal_id}: missing name or image")
            return

        logger.info(f"Starting AI analysis for meal: {meal.name} (ID: {meal_id})")

        # Fetch available options from database
        fitness_goals = list(FitnessGoal.objects.values_list('name', flat=True))

        logger.info(
            f"Fetched database options - "
            f"Fitness Goals: {len(fitness_goals)}, "
        )

        # Initialize meal analyzer with model that supports structured outputs
        analyzer = MealAnalyzer(model="gpt-4o")

        # # Get full Cloudinary URL from the stored path
        # image_path = meal.image_url.name
        # # Extract public_id (filename without extension)
        # public_id = image_path.split("/")[-1].split(".")[0] if "/" in image_path else image_path.split(".")[0]
        # image_url, _ = cloudinary_url(public_id)

        print(meal.image_url.name)
        print(meal.image_url.url)
        # print(meal.image_url.path)

        image_url = f"https://res.cloudinary.com/{settings.CLOUDINARY_CLOUD_NAME}/{meal.image_url.name}"

        print(f"Using Cloudinary URL for analysis: {image_url}")

        # Analyze the meal with database values
        analysis = analyzer.analyze_from_cloudinary_url(
            meal_name=meal.name,
            cloudinary_url=image_url,
            fitness_goals=fitness_goals,
        )

        if not analysis:
            logger.warning(f"AI analysis returned None for meal: {meal.name} (ID: {meal_id})")
            return

        # Update the meal with analysis results
        # We use update() to avoid triggering the signal again
        update_fields = {}

        if analysis.calories is not None:
            update_fields['calories'] = analysis.calories

        # Apply times_of_day
        if analysis.times_of_day:
            update_fields['times_of_day'] = analysis.times_of_day

        # Update scalar fields
        if update_fields:
            Meal.objects.filter(pk=meal_id).update(**update_fields)
            logger.info(f"Updated nutritional fields for meal {meal_id}: {list(update_fields.keys())}")

        # Apply ManyToMany fields
        # Re-fetch the meal instance for M2M operations
        meal_instance = Meal.objects.get(pk=meal_id)

        if analysis.fitness_goals:
            fitness_goal_objects = FitnessGoal.objects.filter(name__in=analysis.fitness_goals)
            if fitness_goal_objects.exists():
                meal_instance.fitness_goals.set(fitness_goal_objects)
                logger.info(f"Set fitness goals for meal {meal_id}: {list(fitness_goal_objects.values_list('name', flat=True))}")
            else:
                logger.warning(f"No matching FitnessGoal objects found for: {analysis.fitness_goals}")

        # Log success with confidence level
        confidence = getattr(analysis, 'confidence', 'unknown')
        reasoning = getattr(analysis, 'reasoning', 'No reasoning provided')
        logger.info(
            f"AI analysis completed for meal {meal_id} (confidence: {confidence}). "
            f"Reasoning: {reasoning}"
        )

    except Exception as e:
        logger.error(f"Error in AI analysis for meal {meal_id}: {str(e)}", exc_info=True)
