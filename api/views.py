from ninja import Router
import json

router = Router(tags=["Webhook"])

@router.post('/whatsapp', auth=None)
def whatsapp_webhook(request):
    json_data = json.loads(request.body)
    return {"detail": "Done"}