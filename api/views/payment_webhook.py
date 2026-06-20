from ninja import Router
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.conf import settings
import json
import hmac
import hashlib
import base64
from django.http import HttpResponse
from decimal import Decimal
from api.models.message import Message
from api.models.order import Order

from api.models.settings import AppSettings
from api.models.user_balance import UserBalance
from api.tasks import assign_rider_to_order
import urllib.parse

router = Router(tags=["Webhook"])


@csrf_exempt
@router.post("/payment", auth=None)
@transaction.atomic
def payment_webhook(request):
    """
    Handle payment webhook from Vendy payment provider.

    Uses select_for_update() to prevent race conditions when processing
    duplicate webhooks for the same order. This ensures:
    - Only one webhook processes the payment
    - Referral bonuses are awarded exactly once
    - No duplicate payment confirmations
    """
    print("Payment Webhook", request.body)
    print("Payment Webhook Headers", request.headers)

    # Verify webhook signature from Vendy using HMAC SHA256
    signature_header = request.headers.get('X-Signature')

    if not signature_header:
        print("Missing X-Signature header in webhook request")
        return HttpResponse("Unauthorized: Missing signature", status=401)

    # Get the secret hash from settings
    secret_hash = settings.VENDY_SECRET_HASH

    if not secret_hash:
        print("VENDY_SECRET_HASH not configured in Django settings")
        return HttpResponse("Server configuration error", status=500)

    # Compute the expected signature using HMAC SHA256
    computed_signature = base64.b64encode(
        hmac.new(
            secret_hash.encode('utf-8'),
            request.body,
            hashlib.sha256
        ).digest()
    ).decode('utf-8')

    # Compare signatures using timing-safe comparison
    if not hmac.compare_digest(computed_signature, signature_header):
        print(f"Invalid webhook signature. Expected: {computed_signature}, Got: {signature_header}")
        return HttpResponse("Unauthorized: Invalid signature", status=401)

    print("Webhook signature verified successfully")

    try:
        # Parse the webhook payload
        payload = json.loads(request.body)
        
        # Extract relevant data
        event_type = payload.get("event.type")
        data = payload.get("data", {})
        currency = data.get("currency")
        
        # Check if transaction was successful
        if event_type != "transaction_success":
            print(f"Ignoring event type: {event_type}")
            return HttpResponse("Event ignored", status=200)
        
        # Extract order and payment information
        meta = data.get("meta", {})
        order_id = meta.get("orderId")
        
        if not order_id:
            print("No orderId found in webhook payload")
            return HttpResponse("No orderId", status=400)

        # Get the order with row-level lock to prevent race conditions
        # This blocks concurrent webhook calls for the same order
        try:
            order = Order.objects.select_for_update().get(id=order_id)
        except Order.DoesNotExist:
            print(f"Order {order_id} not found")
            return HttpResponse("Order not found", status=404)

        # Check if already paid AFTER acquiring lock (atomic check)
        # This prevents duplicate processing if two webhooks arrive simultaneously
        if order.paid:
            print(f"Order {order_id} is already marked as paid")
            return HttpResponse("Order already paid", status=200)
        
        if currency == None or order.currency.code.lower() != currency.lower():
            return HttpResponse("Currency mismatch", status=400)

        # Extract payment amounts
        request_amount = Decimal(data.get("requestamount", "0"))  # Original request amount (105.0)
        
        # Verify the payment amount matches the order total
        # You can choose to verify against either amount or requestamount
        # depending on whether you want to include processing fees
        expected_amount = order.total_price
        
        if request_amount < expected_amount:
            order.amount_paid = request_amount
            order.paid = False
            order.save()

            print(f"Payment amount below expected. Expected: {expected_amount}, Got: {request_amount}")
            return HttpResponse(f"Payment amount below expected. Expected: {expected_amount}, Got: {request_amount}", status=400)
        
        if (request_amount - order.delivery_fee) < order.meal.price:
            order.amount_paid = request_amount
            order.paid = False
            order.save()
            
            setting = AppSettings.get_settings()

            Message.bot_message(
                f"Your payment for order #{order.code} is less than the meal price. Please reach our support team at {setting.whatsapp_support_phone_number}.",
                user=order.user
            )
            return HttpResponse(f"Meal price has been update please contact admin", status=400)
        

        # Verify transaction status
        delivered = data.get("delivered") == "1"
        vended = data.get("vended") == "1"
        debited = data.get("debited") == "1"
        failed = data.get("failed") == "1"
        
        if failed == True or not (delivered and vended and debited):
            print(f"Transaction not successful. Delivered: {delivered}, Vended: {vended}, Debited: {debited}, Failed: {failed}")
            return HttpResponse("Transaction not completed", status=200)
        
        # Update order with payment information
        order.amount_paid = request_amount
        order.paid = True
        order.save()

        # Trigger auto-assignment of rider to the paid order
        assign_rider_to_order(order.id)

        # Check if first order paid for and if referred, give referral bonus
        # Use fresh query to avoid cached counts from related manager
        if order.user and order.user.referred_by:
            # Count paid orders with a fresh query AFTER marking this one as paid
            # This prevents race condition in first order detection
            paid_order_count = Order.objects.filter(
                user=order.user,
                paid=True
            ).count()

            # Only award bonus if this is the FIRST paid order
            if paid_order_count == 1:
                setting = AppSettings.get_settings()

                city = order.meal.city
                referrer = order.user.referred_by

                # Use the utility function to add referral earning
                # This automatically creates ReferralEarning, updates UserBalance, and legacy field
                UserBalance.add_referral_earning(
                    referred_by_user=referrer,
                    referred_user=order.user,
                    city=city
                )

                if city.referral_bonus > 0:
                    text = f"Hi, I was referred by a friend (Referral code: #{referrer.code})"
                    encoded_text = urllib.parse.quote(text)

                    link = f"https://wa.me/{setting.whatsapp_phone_number}?text={encoded_text}"

                    Message.bot_message(
                        f"🎉 You've earned a referral bonus of {city.currency.symbol}{city.referral_bonus} ({city.currency.code}) for referring a user who completed their first order! Keep sharing your referral link to earn more! 🚀 \n {link}",
                        user=referrer
                    )
        
        print(f"Order {order_id} confirmed. Request amount: {request_amount}")
        
        Message.bot_message(
            f"✅ Your payment for order #{order.code} has been received and your order is confirmed! Thank you for choosing FoodieRobot. 🍽️🚀",
            user=order.user
        )
        return HttpResponse("Payment confirmed", status=200)
        
    except json.JSONDecodeError as e:
        print(f"Invalid JSON payload: {e}")
        return HttpResponse("Invalid JSON", status=400)
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return HttpResponse("Internal error", status=500)
    