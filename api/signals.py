"""
Django signals for the API app.

This module contains signal handlers for various model events.
"""

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models.order import Order, OrderStatus
from api.models.meal import Meal
from api.models.review import Review
from api.models.message import Message
from django.utils import timezone

from api.services.ai.tool_handlers.stats import get_progress_stats


@receiver(post_save, sender=Meal)
def analyze_new_meal_with_ai(sender, instance, created, **kwargs):
    """Trigger AI analysis when a new meal is created with an image."""
    if not created:
        return

    if not instance.image_url:
        return

    meal_id = instance.id

    def queue_analysis():
        try:
            from api.tasks.analyze_meal_with_ai import analyze_meal_with_ai_task
            analyze_meal_with_ai_task(meal_id)
        except Exception as e:
            print(f"Error queuing AI analysis for meal {meal_id}: {str(e)}")

    # Queue the task after the transaction commits to avoid connection issues
    transaction.on_commit(queue_analysis)


@receiver(post_save, sender=Order)
def send_review_request_on_order_received(sender, instance, created, **kwargs):
    # Check if user exists
    if not instance.user:
        return

    if instance.status == OrderStatus.DISPATCHED:
        Message.bot_message(
                content=f"Your order #{instance.code} has been dispatched! Rider is on the way.",
                user=instance.user,
            )
        return
    
    if instance.status == OrderStatus.ARRIVED:
        Message.bot_message(
                content=f"Your order #{instance.code} has arrived! Rider is at the delivery location.",
                user=instance.user,
            )
        return
    
    if instance.status == OrderStatus.RECEIVED:
        # Check if review already exists for this order
        existing_review = Review.objects.filter(order=instance).exists()
        if existing_review:
            return

        # Send WhatsApp Flow review request
        try:
            Message.bot_message_flow(
                content=f"🎉 Your order #{instance.code} has been delivered! How was your experience?",
                user=instance.user,
                flow_cta="Leave a Review",
                flow_id=settings.WHATSAPP_FLOW_ORDER_REVIEW,
                screen_name="ORDER_REVIEW",
                data={
                    "order_id": instance.id,
                },
            )

            get_progress_stats(instance.user)
        except Exception as e:
            print(f"Error sending review request for order {instance.id}: {str(e)}")


@receiver(post_save, sender=Order)
def update_delivered_at_timestamp(sender, instance, created, **kwargs):
    if created or instance.status != OrderStatus.RECEIVED:
        return

    if instance.delivered_at is None:
        Order.objects.filter(id=instance.id).update(delivered_at=timezone.now())
