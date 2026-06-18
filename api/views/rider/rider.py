"""Rider profile and status endpoints."""

from ninja import Router
from django.utils import timezone

from api.schemas.rider_schemas import (
    OnlineStatusRequest, OnlineStatusResponse, SimpleResponse,
    RiderProfileResponse
)
from api.models.rider import Rider
from api.models.user_balance import UserBalance
from api.models.currency import Currency
from api.utils.auth_bearer import jwt_auth
from api.utils.permissions import require_rider
from ninja.errors import HttpError

router = Router(tags=["Rider Status & Profile"])


@router.put("/online-status", auth=jwt_auth, response={200: OnlineStatusResponse})
@require_rider
def toggle_online_status(request, payload: OnlineStatusRequest):
    """Toggle rider's online/offline status for receiving orders."""
    try:
        rider = request.user.rider_profile
    except Rider.DoesNotExist:
        raise HttpError(400, "Rider profile not found")

    # Update online status
    rider.is_online = payload.isOnline
    rider.save()

    return {
        'isOnline': rider.is_online,
        'updatedAt': timezone.now()
    }


@router.get("/profile", auth=jwt_auth, response={200: RiderProfileResponse})
@require_rider
def get_rider_profile(request):
    """Get rider's profile information and statistics."""
    try:
        rider = request.user.rider_profile
    except Rider.DoesNotExist:
        raise HttpError(400, "Rider profile not found")

    user = request.user

    # Get rider balance
    currency = Currency.objects.filter(code='NGN').first()
    if not currency:
        currency = Currency.objects.first()

    balance = 0
    if currency:
        user_balance = UserBalance.get_balance(user, currency)
        balance = float(user_balance.amount)

    return {
        'id': user.id,
        'name': user.get_full_name() or user.username or '',
        'email': user.email,
        'phone': user.phone or '',
        'balance': balance,
        'isOnline': rider.is_online,
        'stats': {
            'totalDeliveries': rider.total_deliveries,
            'completedToday': rider.completed_today,
            'averageRating': float(rider.average_rating),
            'totalEarnings': float(rider.total_earnings)
        }
    }
