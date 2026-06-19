"""Background tasks for order rider assignment and timeout management using Huey."""

from huey.contrib.djhuey import task, periodic_task
from huey import crontab
from django.utils import timezone
from datetime import timedelta
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import random

from api.models.order import Order, OrderStatus
from api.models.rider import Rider


@task()
def assign_rider_to_order(order_id):
    """
    Auto-assign a rider to an order.

    This task is triggered when an order payment is confirmed.
    It finds an available rider and assigns them to the order.

    Args:
        order_id: The ID of the order to assign a rider to
    """
    try:
        order = Order.objects.select_related('meal__city').get(id=order_id)

        # Check if order is already assigned or not paid
        if order.rider or not order.paid or order.status != OrderStatus.PENDING:
            print(f"Order {order_id} already assigned or not eligible for assignment")
            return

        # Get available riders (simple round-robin for now)
        # TODO: Implement intelligent assignment based on:
        # - Rider location proximity
        # - Rider availability status
        # - Rider ratings
        # - Current workload
        available_riders = list(Rider.objects.all())

        if not available_riders:
            print(f"No available riders for order {order_id}")
            return

        # Select a random rider (you can implement more sophisticated logic)
        selected_rider = random.choice(available_riders)

        # Assign rider and set timestamp
        order.rider = selected_rider
        order.rider_assigned_at = timezone.now()
        order.save(update_fields=['rider', 'rider_assigned_at'])

        print(f"Order {order_id} assigned to rider {selected_rider.id}")

        # Notify rider via WebSocket
        notify_rider_of_assignment(order, selected_rider)

    except Order.DoesNotExist:
        print(f"Order {order_id} not found")
    except Exception as e:
        print(f"Error assigning rider to order {order_id}: {e}")


@periodic_task(crontab(minute='*/5'))
def check_order_assignment_timeouts():
    """
    Periodic task that runs every 5 minutes to check for order assignment timeouts.

    Finds orders that:
    - Have a rider assigned
    - Status is still PENDING (not accepted)
    - Were assigned more than 5 minutes ago
    - Are paid

    Reassigns these orders to a different rider.
    """
    print("Running order assignment timeout check...")

    # Calculate timeout threshold (5 minutes ago)
    timeout_threshold = timezone.now() - timedelta(minutes=5)

    # Find orders that have timed out
    timed_out_orders = Order.objects.select_related('rider', 'meal__city').filter(
        rider__isnull=False,
        status=OrderStatus.PENDING,
        paid=True,
        rider_assigned_at__lte=timeout_threshold
    )

    count = 0
    for order in timed_out_orders:
        try:
            old_rider = order.rider
            old_rider_id = old_rider.id if old_rider else None

            # Notify the old rider that the order timed out
            if old_rider_id:
                notify_rider_of_timeout(order.id, old_rider_id)

            # Get available riders excluding the one who timed out
            available_riders = list(Rider.objects.exclude(id=old_rider_id))

            if not available_riders:
                print(f"No other riders available for order {order.id}")
                # Reset assignment to try again later
                order.rider = None
                order.rider_assigned_at = None
                order.save(update_fields=['rider', 'rider_assigned_at'])
                continue

            # Select a new rider
            new_rider = random.choice(available_riders)

            # Reassign order
            order.rider = new_rider
            order.rider_assigned_at = timezone.now()
            order.save(update_fields=['rider', 'rider_assigned_at'])

            print(f"Order {order.id} reassigned from rider {old_rider_id} to rider {new_rider.id}")

            # Notify new rider via WebSocket
            notify_rider_of_assignment(order, new_rider)

            count += 1

        except Exception as e:
            print(f"Error reassigning order {order.id}: {e}")

    print(f"Reassigned {count} timed-out orders")
    return count


def notify_rider_of_assignment(order: Order, rider: Rider):
    """
    Send WebSocket notification to rider about new order assignment.

    Args:
        order: The Order instance
        rider: The Rider instance
    """
    try:
        channel_layer = get_channel_layer()
        rider_group = f"rider_{rider.user_id}"

        order_data = {
            'id': order.id,
            'code': order.code,
            'restaurantPaymentTransactionId': order.restaurant_payment_transaction_id,
            'restaurantPaymentCompletedAt': order.restaurant_payment_completed_at,
            'restaurantName': order.meal.restaurant.name,
            'restaurantPhone': order.meal.restaurant.phone,
            'pickupAddress': order.pickup_street_address or '',
            'dropoffAddress': order.dropoff_street_address or '',
            'customerName': order.user.get_full_name() or order.user.username or '',
            'customerPhone': order.user.phone or '',
            'deliveryFee': float(order.delivery_fee),
            'status': order.status,
            'mealName': order.meal.name,
            'mealQuantity': order.quantity,
            'mealPrice': float(order.meal_price),
            'paymentCompleted': order.paid,
            'createdAt': order.created_at,
            'completedAt': order.delivered_at
        }

        async_to_sync(channel_layer.group_send)(
            rider_group,
            {
                'type': 'order_assigned',
                'order': order_data
            }
        )
        print(f"WebSocket notification sent to rider {rider.id} for order {order.id}")
    except Exception as e:
        print(f"Error sending WebSocket notification: {e}")


def notify_rider_of_timeout(order_id, rider_id):
    """
    Send WebSocket notification to rider that their order assignment timed out.

    Args:
        order_id: The Order ID
        rider_id: The Rider ID
    """
    try:
        rider = Rider.objects.get(id=rider_id)
        channel_layer = get_channel_layer()
        rider_group = f"rider_{rider.user_id}"

        async_to_sync(channel_layer.group_send)(
            rider_group,
            {
                'type': 'order_timeout',
                'order_id': order_id
            }
        )
        print(f"Timeout notification sent to rider {rider_id} for order {order_id}")
    except Exception as e:
        print(f"Error sending timeout notification: {e}")
