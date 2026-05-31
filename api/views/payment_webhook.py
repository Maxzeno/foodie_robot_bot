from ninja import Router
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.db import transaction
import json

router = Router(tags=["Webhook"])

@csrf_exempt
@transaction.atomic
@router.post("/payment", auth=None)
def payment_webhook(request):
    json_data = json.loads(request.body)
    print("Payment Webhook", json_data)
    return HttpResponse("Done", status=200)
