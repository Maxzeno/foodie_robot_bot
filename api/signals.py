"""
Django signals for the API app.

This module contains signal handlers for various model events.
"""

from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction
from api.models.order import Order, OrderStatus
from api.models.review import Review
from api.models.message import Message
from api.models.meal import Meal
from django.utils import timezone
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


@receiver(pre_save, sender=Meal)
def track_meal_image_change(sender, instance: Meal, **kwargs):
    """
    Track the old image URL before save to detect if image was changed.
    """
    if instance.pk:
        try:
            old_instance = Meal.objects.get(pk=instance.pk)
            instance._old_image_url = old_instance.image_url
        except Meal.DoesNotExist:
            instance._old_image_url = None
    else:
        instance._old_image_url = None


@receiver(post_save, sender=Meal)
def process_meal_after_save(sender, instance: Meal, created, **kwargs):
    """
    Signal to queue asynchronous tasks for meal processing after save.

    Tasks queued:
    1. Image processing (add logo and text overlay) - runs on creation OR when image is updated
    2. AI analysis (nutritional info and categorization) - runs ONLY on creation
    """
    # Determine if image was changed
    old_image_url = getattr(instance, '_old_image_url', None)
    image_changed = False

    if created:
        # New meal - image is new if it exists
        image_changed = bool(instance.image_url)
    else:
        # Existing meal - check if image URL changed
        # Compare the actual image references (both public_id and URL)
        old_public_id = getattr(old_image_url, 'public_id', None) if old_image_url else None
        new_public_id = getattr(instance.image_url, 'public_id', None) if instance.image_url else None

        image_changed = old_public_id != new_public_id

    # Queue tasks using transaction.on_commit to ensure they only run if the save succeeds
    def queue_meal_processing_tasks():
        from api.tasks.process_meal_image import process_meal_image_task
        from api.tasks.analyze_meal_with_ai import analyze_meal_with_ai_task

        # Queue image processing task if image was added or updated
        if image_changed and instance.image_url:
            logger.info(f"Queuing image processing task for meal {instance.id}: {instance.name}")
            process_meal_image_task(instance.id)

        # Queue AI analysis task ONLY on creation (not on updates)
        if created and instance.name and instance.image_url:
            logger.info(f"Queuing AI analysis task for meal {instance.id}: {instance.name}")
            analyze_meal_with_ai_task(instance.id)

    # Execute tasks after transaction commits to ensure meal is saved
    transaction.on_commit(queue_meal_processing_tasks)
