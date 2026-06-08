"""
Django signals for the API app.

This module contains signal handlers for various model events.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models.order import Order, OrderStatus
from api.models.review import Review
from api.models.message import Message, RoleChoices
from api.models.meal import Meal, FitnessGoal, HealthCondition, Allergy, PreferredCuisine
from django.utils import timezone
from api.services.ai.meal_analyzer import MealAnalyzer
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def send_review_request_on_order_received(sender, instance, created, **kwargs):
    if created:
        return

    if instance.status != OrderStatus.RECEIVED:
        return

    # Check if user exists
    if not instance.user:
        return

    # Check if review already exists for this order
    existing_review = Review.objects.filter(order=instance).exists()
    if existing_review:
        return

    # Send WhatsApp Flow review request
    try:
        message = Message.bot_message_flow(
            content=f"🎉 Your order #{instance.code} has been delivered! How was your experience?",
            user=instance.user,
            flow_cta="Leave a Review",
            flow_id="2324812558034573",
            screen_name="ORDER_REVIEW",
            data={
                "order_id": instance.id,
            },
        )

    except Exception as e:
        print(f"Error sending review request for order {instance.id}: {str(e)}")


@receiver(post_save, sender=Order)
def update_delivered_at_timestamp(sender, instance, created, **kwargs):
    if created or instance.status != OrderStatus.RECEIVED:
        return

    if instance.delivered_at is None:
        Order.objects.filter(id=instance.id).update(delivered_at=timezone.now())


@receiver(post_save, sender=Meal)
def analyze_meal_with_ai(sender, instance, created, **kwargs):
    """
    Automatically analyze meal with AI when a new meal is created with name and image.

    This signal runs after the meal is saved, so Cloudinary upload is complete
    and the image_url field contains the actual URL.
    """
    # Only run for newly created meals
    if not created:
        return

    # Only run if meal has name and image
    if not instance.name or not instance.image_url:
        logger.info(f"Skipping AI analysis for meal {instance.id}: missing name or image")
        return

    try:
        logger.info(f"Starting AI analysis for meal: {instance.name} (ID: {instance.id})")

        # Initialize meal analyzer with model that supports structured outputs
        analyzer = MealAnalyzer(model="gpt-4o-2024-08-06")

        # Get Cloudinary URL - at this point the image is already uploaded
        image_url = str(instance.image_url.url) if hasattr(instance.image_url, 'url') else str(instance.image_url)

        # Analyze the meal
        analysis = analyzer.analyze_from_cloudinary_url(
            meal_name=instance.name,
            cloudinary_url=image_url
        )

        if not analysis:
            logger.warning(f"AI analysis returned None for meal: {instance.name} (ID: {instance.id})")
            return

        # Update the meal with analysis results
        # We use update() to avoid triggering the signal again
        update_fields = {}

        # Apply nutritional values
        if analysis.calories is not None:
            update_fields['calories'] = analysis.calories
        if analysis.protein is not None:
            update_fields['protein'] = analysis.protein
        if analysis.carbs is not None:
            update_fields['carbs'] = analysis.carbs
        if analysis.fats is not None:
            update_fields['fats'] = analysis.fats
        if analysis.fiber is not None:
            update_fields['fiber'] = analysis.fiber
        if analysis.sugar is not None:
            update_fields['sugar'] = analysis.sugar
        if analysis.sodium is not None:
            update_fields['sodium'] = analysis.sodium
        if analysis.cholesterol is not None:
            update_fields['cholesterol'] = analysis.cholesterol
        if analysis.serving_amount_g is not None:
            update_fields['serving_amount_g'] = analysis.serving_amount_g

        # Apply times_of_day
        if analysis.times_of_day:
            update_fields['times_of_day'] = analysis.times_of_day

        # Update scalar fields
        if update_fields:
            Meal.objects.filter(pk=instance.pk).update(**update_fields)
            logger.info(f"Updated nutritional fields for meal {instance.id}: {list(update_fields.keys())}")

        # Apply ManyToMany fields
        if analysis.fitness_goals:
            fitness_goal_objects = FitnessGoal.objects.filter(name__in=analysis.fitness_goals)
            if fitness_goal_objects.exists():
                instance.fitness_goals.set(fitness_goal_objects)
                logger.info(f"Set fitness goals for meal {instance.id}: {list(fitness_goal_objects.values_list('name', flat=True))}")

        if analysis.restricted_health_conditions:
            health_condition_objects = HealthCondition.objects.filter(name__in=analysis.restricted_health_conditions)
            if health_condition_objects.exists():
                instance.restricted_health_conditions.set(health_condition_objects)
                logger.info(f"Set health conditions for meal {instance.id}: {list(health_condition_objects.values_list('name', flat=True))}")

        if analysis.restricted_allergies:
            allergy_objects = Allergy.objects.filter(name__in=analysis.restricted_allergies)
            if allergy_objects.exists():
                instance.restricted_allergies.set(allergy_objects)
                logger.info(f"Set allergies for meal {instance.id}: {list(allergy_objects.values_list('name', flat=True))}")

        if analysis.cuisine:
            cuisine_objects = PreferredCuisine.objects.filter(name__in=analysis.cuisine)
            if cuisine_objects.exists():
                instance.cuisine.set(cuisine_objects)
                logger.info(f"Set cuisines for meal {instance.id}: {list(cuisine_objects.values_list('name', flat=True))}")

        # Log success with confidence level
        confidence = getattr(analysis, 'confidence', 'unknown')
        reasoning = getattr(analysis, 'reasoning', 'No reasoning provided')
        logger.info(
            f"AI analysis completed for meal {instance.id} (confidence: {confidence}). "
            f"Reasoning: {reasoning}"
        )

    except Exception as e:
        logger.error(f"Error in AI analysis for meal {instance.id}: {str(e)}", exc_info=True)
