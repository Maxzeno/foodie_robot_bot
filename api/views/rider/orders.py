"""Order management endpoints for Rider/Company API."""

from ninja import Router
from django.db import transaction
from django.utils import timezone

from api.schemas.rider_schemas import (
    OrderHistoryResponse, OrderItemResponse, SimpleResponse,
    NewOrderResponse, AcceptOrderResponse,
    UpdateStatusRequest, UpdateStatusResponse,
    ConfirmDeliveryRequest, ConfirmDeliveryResponse
)
from api.models.order import Order, OrderStatus
from api.models.rider import Rider
from api.utils.auth_bearer import jwt_auth
from api.utils.permissions import require_rider
from api.utils.pagination import paginate_queryset
from api.utils.rate_limit import check_rate_limit, RateLimitExceeded
from api.utils.order_validation import validate_status_transition
from api.utils.earnings import process_delivery_completion
from ninja.errors import HttpError

router = Router(tags=["Rider Orders"])


@router.get("/history", auth=jwt_auth, response={200: OrderHistoryResponse})
@require_rider
def order_history(request, page: int = 1, limit: int = 20, status: str = None):
    """
    Get rider's order history with pagination.
    Rate limit: 60 requests per minute.
    """
    try:
        check_rate_limit(request.user.email, max_requests=60, window_seconds=60)
    except RateLimitExceeded as e:
        raise HttpError(429, str(e))

    # Get rider profile
    try:
        rider = request.user.rider_profile
    except Rider.DoesNotExist:
        raise HttpError(400, "Rider profile not found")

    # Build query
    queryset = Order.objects.filter(rider=rider).select_related(
        'meal', 'meal__restaurant', 'user', 'currency'
    ).order_by('-created_at')

    if status:
        queryset = queryset.filter(status=status)

    # Paginate
    orders, pagination = paginate_queryset(queryset, page, limit)

    # Serialize
    order_items = [
        {
            'id': order.code,
            'restaurantName': order.meal.restaurant.name,
            'restaurantPhone': order.meal.restaurant.phone,
            'pickupAddress': order.pickup_street_address or '',
            'dropoffAddress': order.dropoff_street_address or '',
            'customerName': order.user.get_full_name() or order.user.username or '',
            'customerPhone': order.user.phone or '',
            'deliveryFee': float(order.delivery_fee),
            'status': order.status,
            'confirmationCode': order.confirmation_code,
            'mealName': order.meal.name,
            'mealQuantity': order.quantity,
            'mealPrice': float(order.meal_price),
            'paymentCompleted': order.paid,
            'createdAt': order.created_at,
            'completedAt': order.delivered_at
        }
        for order in orders
    ]

    return {
        'orders': order_items,
        'pagination': pagination
    }


@router.get("/{order_id}", auth=jwt_auth, response={200: OrderItemResponse, 404: SimpleResponse})
@require_rider
def order_detail(request, order_id: str):
    """Get detailed order information."""
    try:
        rider = request.user.rider_profile
    except Rider.DoesNotExist:
        raise HttpError(400, "Rider profile not found")

    try:
        order = Order.objects.select_related(
            'meal', 'meal__restaurant', 'user', 'currency'
        ).get(code=order_id, rider=rider)

        return {
            'id': order.code,
            'restaurantName': order.meal.restaurant.name,
            'restaurantPhone': order.meal.restaurant.phone,
            'pickupAddress': order.pickup_street_address or '',
            'dropoffAddress': order.dropoff_street_address or '',
            'customerName': order.user.get_full_name() or order.user.username or '',
            'customerPhone': order.user.phone or '',
            'deliveryFee': float(order.delivery_fee),
            'status': order.status,
            'confirmationCode': order.confirmation_code,
            'mealName': order.meal.name,
            'mealQuantity': order.quantity,
            'mealPrice': float(order.meal_price),
            'paymentCompleted': order.paid,
            'createdAt': order.created_at,
            'completedAt': order.delivered_at
        }

    except Order.DoesNotExist:
        raise HttpError(404, "Order not found")


@router.get("/new", auth=jwt_auth, response={200: NewOrderResponse | SimpleResponse})
@require_rider
def get_new_order(request):
    """
    Poll for new available orders (riders only).
    Rate limit: 1 request per 5 seconds.
    """
    try:
        check_rate_limit(request.user.email, max_requests=1, window_seconds=5)
    except RateLimitExceeded as e:
        raise HttpError(429, str(e))

    # Get rider profile
    try:
        rider = request.user.rider_profile
    except Rider.DoesNotExist:
        raise HttpError(400, "Rider profile not found")

    # Check if rider is online
    if not rider.is_online:
        raise HttpError(400, "You must be online to receive orders")

    # Get next available order
    order = Order.objects.filter(
        status=OrderStatus.PENDING,
        paid=True,
        rider__isnull=True
    ).select_related(
        'meal', 'meal__restaurant', 'user', 'currency'
    ).order_by('created_at').first()

    if not order:
        return {'details': 'No orders available at the moment'}

    # Calculate distance and duration (placeholder for now)
    estimated_distance = "2.5 km"
    estimated_duration = "15 minutes"

    return {
        'id': order.code,
        'restaurantName': order.meal.restaurant.name,
        'restaurantPhone': order.meal.restaurant.phone,
        'pickupAddress': order.pickup_street_address or '',
        'dropoffAddress': order.dropoff_street_address or '',
        'customerName': order.user.get_full_name() or order.user.username or '',
        'customerPhone': order.user.phone or '',
        'deliveryFee': float(order.delivery_fee),
        'confirmationCode': order.confirmation_code or '',
        'mealName': order.meal.name,
        'mealQuantity': order.quantity,
        'mealPrice': float(order.meal_price),
        'estimatedDistance': estimated_distance,
        'estimatedDuration': estimated_duration
    }


@router.post("/{order_id}/accept", auth=jwt_auth, response={200: AcceptOrderResponse, 409: SimpleResponse, 404: SimpleResponse})
@require_rider
@transaction.atomic
def accept_order(request, order_id: str):
    """Rider accepts a new order."""
    try:
        rider = request.user.rider_profile
    except Rider.DoesNotExist:
        raise HttpError(400, "Rider profile not found")

    try:
        # Lock order to prevent race condition
        order = Order.objects.select_for_update().get(
            code=order_id,
            status=OrderStatus.PENDING,
            paid=True
        )

        # Check if already assigned
        if order.rider is not None:
            raise HttpError(409, "This order has been accepted by another rider")

        # Assign to rider
        order.rider = rider
        order.status = OrderStatus.ACCEPTED
        order.save()

        return {
            'details': 'Order accepted successfully',
            'orderId': order.code,
            'status': order.status
        }

    except Order.DoesNotExist:
        raise HttpError(404, "Order not found or already assigned")


@router.put("/{order_id}/status", auth=jwt_auth, response={200: UpdateStatusResponse, 400: SimpleResponse, 404: SimpleResponse})
@require_rider
def update_order_status(request, order_id: str, payload: UpdateStatusRequest):
    """Update order status (atRestaurant, onTheWay, delivered)."""
    try:
        rider = request.user.rider_profile
    except Rider.DoesNotExist:
        raise HttpError(400, "Rider profile not found")

    try:
        order = Order.objects.get(code=order_id, rider=rider)

        # Validate status transition
        try:
            validate_status_transition(order.status, payload.status)
        except ValueError as e:
            raise HttpError(400, str(e))

        # Update status
        order.status = payload.status
        order.save()

        return {
            'details': 'Order status updated successfully',
            'orderId': order.code,
            'status': order.status,
            'updatedAt': timezone.now()
        }

    except Order.DoesNotExist:
        raise HttpError(404, "Order not found")


@router.post("/{order_id}/confirm-delivery", auth=jwt_auth, response={200: ConfirmDeliveryResponse, 400: SimpleResponse, 404: SimpleResponse})
@require_rider
@transaction.atomic
def confirm_delivery(request, order_id: str, payload: ConfirmDeliveryRequest):
    """Confirm delivery using customer's 4-digit confirmation code."""
    try:
        rider = request.user.rider_profile
    except Rider.DoesNotExist:
        raise HttpError(400, "Rider profile not found")

    try:
        order = Order.objects.select_for_update().get(code=order_id, rider=rider)

        # Verify confirmation code
        if order.confirmation_code != payload.confirmationCode:
            raise HttpError(400, "The confirmation code is incorrect")

        # Update order status
        order.status = OrderStatus.DELIVERED
        order.delivered_at = timezone.now()
        order.save()

        # Process earnings
        process_delivery_completion(order)

        return {
            'details': 'Delivery confirmed successfully',
            'orderId': order.code,
            'status': order.status,
            'deliveryFee': float(order.delivery_fee),
            'completedAt': order.delivered_at
        }

    except Order.DoesNotExist:
        raise HttpError(404, "Order not found")
