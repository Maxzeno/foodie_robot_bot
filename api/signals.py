"""
Django signals for the API app.

This module contains signal handlers for various model events.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from api.models.order import Order, OrderStatus
from api.models.review import Review
from api.models.message import Message, RoleChoices
from django.utils import timezone


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
