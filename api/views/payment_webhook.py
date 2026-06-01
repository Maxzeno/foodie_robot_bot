from ninja import Router
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
from django.http import HttpResponse
from decimal import Decimal
from api.models.message import Message
from api.models.order import Order
from django.conf import settings

router = Router(tags=["Webhook"])


@csrf_exempt
@transaction.atomic
@router.post("/payment", auth=None)
def payment_webhook(request):
    # TODO: confirm request is from Vendy using the secret hash in the header
    # if settings.VENDY_SECRET_HASH == None or settings.VENDY_SECRET_HASH != request.headers.get('secretHash'):
    #     print("Invalid secret hash in webhook request")
    #     return HttpResponse("Unauthorized", status=401)
    try:
        print("Payment Webhook", request.body)
        print("Payment Webhook Headers", request.headers)
        
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
        
        # Get the order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            print(f"Order {order_id} not found")
            return HttpResponse("Order not found", status=404)
        
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

            Message.bot_message(
                f"Your payment for order #{order.code} is less than the meal price. Please reach our support team at {settings.CUSTOMER_SUPPORT_NUMBER}.",
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
        
        print(f"Order {order_id} confirmed. Request amount: {request_amount}")
        
        Message.bot_message(
            f"✅ Your payment for order #{order.code} has been received and your order is confirmed! Thank you for choosing Foodie Robot. 🍽️🚀",
            user=order.user
        )
        return HttpResponse("Payment confirmed", status=200)
        
    except json.JSONDecodeError as e:
        print(f"Invalid JSON payload: {e}")
        return HttpResponse("Invalid JSON", status=400)
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return HttpResponse("Internal error", status=500)
    