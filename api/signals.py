"""
Django signals for the API app.

This module contains signal handlers for various model events.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from api.models.order import Order, OrderStatus
from api.models.review import Review
from api.models.message import Message
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
            flow_id=settings.WHATSAPP_FLOW_ORDER_REVIEW,
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
def analyze_meal_with_ai(sender, instance: Meal, created, **kwargs):
    if not created:
        return

    if not instance.name or not instance.image_url:
        logger.info(f"Skipping AI analysis for meal {instance.id}: missing name or image")
        return

    try:
        logger.info(f"Starting AI analysis for meal: {instance.name} (ID: {instance.id})")

        # Fetch available options from database
        fitness_goals = list(FitnessGoal.objects.values_list('name', flat=True))
        health_conditions = list(HealthCondition.objects.values_list('name', flat=True))
        allergies = list(Allergy.objects.values_list('name', flat=True))
        cuisines = list(PreferredCuisine.objects.values_list('name', flat=True))

        logger.info(
            f"Fetched database options - "
            f"Fitness Goals: {len(fitness_goals)}, "
            f"Health Conditions: {len(health_conditions)}, "
            f"Allergies: {len(allergies)}, "
            f"Cuisines: {len(cuisines)}"
        )

        # Initialize meal analyzer with model that supports structured outputs
        analyzer = MealAnalyzer(model="gpt-4o")

        # Get Cloudinary URL - at this point the image is already uploaded
        image_url = str(instance.image_url.url) if hasattr(instance.image_url, 'url') else str(instance.image_url)

        # Analyze the meal with database values
        analysis = analyzer.analyze_from_cloudinary_url(
            meal_name=instance.name,
            cloudinary_url=image_url,
            fitness_goals=fitness_goals,
            health_conditions=health_conditions,
            allergies=allergies,
            cuisines=cuisines
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

        # Apply ManyToMany fields AFTER transaction commits
        # This is critical because ManyToMany changes in signals can be rolled back
        def set_many_to_many_fields():
            meal_instance = Meal.objects.get(pk=instance.pk)

            if analysis.fitness_goals:
                fitness_goal_objects = FitnessGoal.objects.filter(name__in=analysis.fitness_goals)
                if fitness_goal_objects.exists():
                    meal_instance.fitness_goals.set(fitness_goal_objects)
                    logger.info(f"Set fitness goals for meal {meal_instance.id}: {list(fitness_goal_objects.values_list('name', flat=True))}")
                else:
                    logger.warning(f"No matching FitnessGoal objects found for: {analysis.fitness_goals}")

            if analysis.restricted_health_conditions:
                health_condition_objects = HealthCondition.objects.filter(name__in=analysis.restricted_health_conditions)
                if health_condition_objects.exists():
                    meal_instance.restricted_health_conditions.set(health_condition_objects)
                    logger.info(f"Set health conditions for meal {meal_instance.id}: {list(health_condition_objects.values_list('name', flat=True))}")
                else:
                    logger.warning(f"No matching HealthCondition objects found for: {analysis.restricted_health_conditions}")

            if analysis.restricted_allergies:
                allergy_objects = Allergy.objects.filter(name__in=analysis.restricted_allergies)
                if allergy_objects.exists():
                    meal_instance.restricted_allergies.set(allergy_objects)
                    logger.info(f"Set allergies for meal {meal_instance.id}: {list(allergy_objects.values_list('name', flat=True))}")
                else:
                    logger.warning(f"No matching Allergy objects found for: {analysis.restricted_allergies}")

            if analysis.cuisine:
                cuisine_objects = PreferredCuisine.objects.filter(name__in=analysis.cuisine)
                if cuisine_objects.exists():
                    meal_instance.cuisine.set(cuisine_objects)
                    logger.info(f"Set cuisines for meal {meal_instance.id}: {list(cuisine_objects.values_list('name', flat=True))}")
                else:
                    logger.warning(f"No matching PreferredCuisine objects found for: {analysis.cuisine}")

        # Execute ManyToMany updates after the transaction commits
        transaction.on_commit(set_many_to_many_fields)

        # Log success with confidence level
        confidence = getattr(analysis, 'confidence', 'unknown')
        reasoning = getattr(analysis, 'reasoning', 'No reasoning provided')
        logger.info(
            f"AI analysis completed for meal {instance.id} (confidence: {confidence}). "
            f"Reasoning: {reasoning}"
        )

    except Exception as e:
        logger.error(f"Error in AI analysis for meal {instance.id}: {str(e)}", exc_info=True)
