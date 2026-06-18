"""Rider profile and status endpoints."""

from ninja import Router
from django.utils import timezone

from api.models.user import User
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
def toggle_online_status(request, payload: OnlineStatusRequest):
    # Update online status
    user = request.user
    user.is_online = payload.isOnline
    user.save()

    return {
        'isOnline': user.is_online,
        'updatedAt': timezone.now()
    }


@router.get("/profile", auth=jwt_auth, response={200: RiderProfileResponse})
def get_rider_profile(request):
    user: User = request.user

    currency_code = 'NGN'
    currency_symbol = "₦"
    if user.city and user.city.currency:
        currency_code = user.city.currency.code
    
    # Get rider balance
    currency = Currency.objects.filter(code=currency_code).first()
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
        'isOnline': user.is_online,
        'city': user.city.name if user.city else None,
        'city_id': user.city.id if user.city else None,
        'currency': currency_code,
        'currency_symbol': currency_symbol,
        'role': 'company' if 'company' in user.roles else 'rider' if 'rider' in user.roles else 'customer'
    }
