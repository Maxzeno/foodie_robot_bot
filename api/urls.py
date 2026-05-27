from api.views.whatsapp_webhook import router as whatsapp_webhook_router
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
