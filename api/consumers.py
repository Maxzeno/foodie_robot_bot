"""WebSocket consumers for real-time updates."""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from api.models.order import Order, OrderStatus
from api.models.user import User
from api.utils.jwt_auth import JWTAuth


class RiderOrderConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for riders to receive real-time order assignments.

    Sends orders that are:
    - Assigned to the rider
    - Status is still 'pending' (not accepted yet)
    - Order is paid

    URL: ws://domain/ws/rider/orders/
    Authentication: Requires JWT token in query string (?token=xxx)
    """

    async def connect(self):
        """Handle WebSocket connection."""
        # Get token from query string
        query_string = self.scope['query_string'].decode()
        token = None

        for param in query_string.split('&'):
            if param.startswith('token='):
                token = param.split('=', 1)[1]
                break

        if not token:
            await self.close(code=4001)
            return

        # Verify JWT token and get user
        user = await self.verify_token(token)
        print(user, 'a')
        if not user:
            await self.close(code=4001)
            return

        # Check if user is a rider
        if not self.user_is_rider(user):
            await self.close(code=4003)
            return

        self.user = user
        print(self.user, 'c')
        self.rider_group = f"rider_{user.id}"

        print(self.rider_group, 'self.rider_group')

        # Join rider-specific group
        await self.channel_layer.group_add(
            self.rider_group,
            self.channel_name
        )

        await self.accept()

        # Send current pending orders to the rider
        await self.send_pending_orders()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'rider_group'):
            await self.channel_layer.group_discard(
                self.rider_group,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages (not used in this implementation)."""
        pass

    async def order_assigned(self, event):
        """
        Handle order assignment event from channel layer.

        Called when a new order is assigned to this rider.
        """
        order_data = event['order']
        await self.send(text_data=json.dumps({
            'type': 'order_assigned',
            'order': order_data
        }))

    async def order_timeout(self, event):
        """
        Handle order timeout event from channel layer.

        Called when an order is being reassigned due to timeout.
        """
        order_id = event['order_id']
        await self.send(text_data=json.dumps({
            'type': 'order_timeout',
            'order_id': order_id,
            'message': 'Order reassigned due to timeout'
        }))

    @database_sync_to_async
    def user_is_rider(self, user:User):
        print(user.is_rider, 'b')
        return user.is_rider

    @database_sync_to_async
    def verify_token(self, token):
        """Verify JWT token and return user."""
        print("Verifying token in WebSocket:", token)
        try:
            user_dict = JWTAuth.decode_access_token(token)

            user = User.objects.get(id=user_dict.get('user_id'))

            print("Verified user in WebSocket:", user)
            return user
        except (ValueError, User.DoesNotExist) as e:
            return None

    @database_sync_to_async
    def get_pending_orders(self):
        """Get all pending orders assigned to this rider."""
        try:
            rider_profile = self.user.rider_profile
            orders = Order.objects.filter(
                rider=rider_profile,
                status=OrderStatus.PENDING,
                paid=True
            ).select_related(
                'meal__restaurant',
                'meal__city',
                'currency',
                'user'
            ).order_by('-rider_assigned_at')
            print('orders in get_pending_orders', orders)
            return [self._serialize_order(order) for order in orders]
        except Exception as e:
            print(f"Error fetching pending orders: {e}")
            return []

    def _serialize_order(self, order: Order):
        """Serialize order object to dict."""
        return {
            'id': order.id,
            'code': order.code,
            'restaurantPaymentCompleted': order.restaurant_payment_completed,
            'restaurantPaymentTransactionId': order.restaurant_payment_transaction_id,
            'restaurantPaymentCompletedAt': order.restaurant_payment_completed_at.isoformat() if order.restaurant_payment_completed_at else None,
            'restaurantName': order.meal.restaurant.name,
            'restaurantPhone': order.meal.restaurant.phone,
            'pickupAddress': order.pickup_street_address or '',
            'dropoffAddress': order.dropoff_street_address or '',
            'pickupAddressLink': order.pickup_point_link(),
            'dropoffAddressLink': order.dropoff_point_link(),
            'customerName': order.user.get_full_name() or order.user.username or '',
            'customerPhone': order.user.phone or '',
            'deliveryFee': float(order.delivery_fee),
            'status': order.status,
            'mealName': order.meal.name,
            'mealQuantity': order.quantity,
            'mealPrice': float(order.meal_price),
            'paymentCompleted': order.paid,
            'createdAt': order.created_at.isoformat() if order.created_at else None,
            'completedAt': order.delivered_at.isoformat() if order.delivered_at else None
        }

    async def send_pending_orders(self):
        """Send all pending orders to the connected rider."""
        orders = await self.get_pending_orders()
        await self.send(text_data=json.dumps({
            'type': 'pending_orders',
            'orders': orders
        }))
