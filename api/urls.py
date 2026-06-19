from api.utils.auth_bearer import AuthBearer
from api.views.whatsapp_webhook import router as whatsapp_webhook_router
from api.views.whatsapp_flow_webhook import router as whatsapp_flow_webhook_router
from api.views.payment_webhook import router as payment_webhook_router
from api.views.rider.auth import router as rider_auth_router
from api.views.rider.orders import router as rider_orders_router
from api.views.rider.payments import router as rider_payments_router
from api.views.rider.rider import router as rider_profile_router
from api.views.rider.company import router as company_router
from api.views.rider.banks import router as banks_router
from ninja import NinjaAPI, Swagger

jwt_authentication = AuthBearer()

api = NinjaAPI(
    auth=jwt_authentication,
    title="FoodieRobot",
    description="FoodieRobot Backend API",
    # throttle=[
    #     AnonRateThrottle('10/s'),
    #     AuthRateThrottle('100/s'),
    # ],
    docs_url='docs/',
    docs=Swagger(settings={"persistAuthorization": True}),
)

# Webhooks (existing)
api.add_router("/webhook", whatsapp_webhook_router)
api.add_router("/webhook", whatsapp_flow_webhook_router)
api.add_router("/webhook", payment_webhook_router)

# Rider/Company API endpoints (new)
api.add_router("/auth", rider_auth_router)
api.add_router("/orders", rider_orders_router)
api.add_router("/payments", rider_payments_router)
api.add_router("/riders", rider_profile_router)
api.add_router("/company", company_router)
api.add_router("/banks", banks_router)
