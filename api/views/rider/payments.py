"""Payment endpoints for Rider/Company API."""

from ninja import Router
from django.db import transaction
from django.utils import timezone

from api.schemas.rider_schemas import (
    VerifyAccountRequest, VerifyAccountResponse, SimpleResponse,
    RestaurantPaymentRequest, RestaurantPaymentResponse
)
from api.models.order import Order
from api.models.rider import Rider
from api.utils.permissions import require_rider
from api.utils.bank_verification import verify_bank_account
from ninja.errors import HttpError

router = Router(tags=["Rider Payments"])


@router.post("/verify-account", response={200: VerifyAccountResponse, 404: SimpleResponse})
@require_rider
def verify_account(request, payload: VerifyAccountRequest):
    """
    Verify bank account details and fetch account name (Mock implementation).

    In production, integrate with:
    - Paystack: https://paystack.com/docs/api/#verification-resolve-account-number
    - Flutterwave: https://developer.flutterwave.com/reference/account-verification
    """
    try:
        result = verify_bank_account(payload.bankName, payload.accountNumber)
        return result
    except ValueError as e:
        raise HttpError(404, str(e))


@router.post("/restaurant-payment", response={200: RestaurantPaymentResponse, 400: SimpleResponse, 404: SimpleResponse})
@require_rider
@transaction.atomic
def restaurant_payment(request, payload: RestaurantPaymentRequest):
    try:
        rider = request.user.rider_profile
    except Rider.DoesNotExist:
        raise HttpError(400, "Rider profile not found")

    try:
        # Get order
        order = Order.objects.select_for_update().get(
            code=payload.orderId,
            rider=rider
        )

        # Check if already paid to restaurant
        if order.restaurant_payment_completed:
            raise HttpError(400, "Restaurant payment already completed for this order")

        if order.restaurant_payment_completed:
            raise HttpError(400, "Restaurant payment already completed for this order")
        
        try:
            # TODO: Pay for the order via payment gateway (e.g., Paystack, Flutterwave)
            # check that the client had paid for the order and make sure you transfer the meal_price to the restaurant

            # Mark order as paid to restaurant
            order.restaurant_payment_completed = True
            order.restaurant_payment_transaction_id = f"TXN-{timezone.now().timestamp()}"
            order.restaurant_payment_completed_at = timezone.now()
            order.save()

            return {
                'transactionId': order.restaurant_payment_transaction_id,
                'orderId': order.id,
                'amount': float(order.meal_price),
                'status': 'completed',
                'paidAt': order.restaurant_payment_completed_at
            }

        except ValueError as e:
            raise HttpError(400, str(e))

    except Order.DoesNotExist:
        raise HttpError(404, "Order not found")
