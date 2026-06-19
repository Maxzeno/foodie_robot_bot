"""WebSocket routing configuration."""

from django.urls import path
from api.consumers import RiderOrderConsumer

websocket_urlpatterns = [
    path('ws/rider/orders/', RiderOrderConsumer.as_asgi()),
]
