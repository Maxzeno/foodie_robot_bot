from api.views.whatsapp_webhook import router as whatsapp_webhook_router
from api.views.whatsapp_flow_webhook import router as whatsapp_flow_webhook_router
from api.views.payment_webhook import router as payment_webhook_router
from ninja import NinjaAPI, Swagger

api = NinjaAPI(
    title="Foodie Robot",
    description="Foodie Robot Backend API",
    # throttle=[
    #     AnonRateThrottle('10/s'),
    #     AuthRateThrottle('100/s'),
    # ],
    docs_url='docs/',
    docs=Swagger(settings={"persistAuthorization": True}),
)

api.add_router("/webhook", whatsapp_webhook_router)
api.add_router("/webhook", whatsapp_flow_webhook_router)
api.add_router("/webhook", payment_webhook_router)
