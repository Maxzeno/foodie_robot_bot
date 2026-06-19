from django.db import models
from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.meal import Meal
from api.models.user import User

from api.utils.generate import generate_unique_code, generate_confirmation_code
from api.utils.validation import validate_geojson_point


class OrderStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'  # New order, not assigned
    ACCEPTED = 'accepted', 'Accepted'  # Rider accepted
    AT_RESTAURANT = 'atRestaurant', 'At Restaurant'  # Arrived at pickup
    ON_THE_WAY = 'onTheWay', 'On The Way'  # Picked up, en route
    DELIVERED = 'delivered', 'Delivered'  # Completed


class OrderChannelChoices(models.TextChoices):
    WHATSAPP = 'whatsapp', 'Whatsapp'
    ONLINE = 'online', 'Online'


def unique_order_code():
    return generate_unique_code(Order, field='code')


class Order(BaseModel):
    code = models.CharField(max_length=100, unique=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    meal = models.ForeignKey(Meal, on_delete=models.PROTECT, related_name="orders")
    
    pickup_street_address = models.CharField(max_length=255, blank=True, null=True) # e.g. "123 Allen Avenue"
    pickup_point = models.JSONField(blank=True, null=True, help_text="GeoJSON Point")

    dropoff_street_address = models.CharField(max_length=255, blank=True, null=True) # e.g. "123 Allen Avenue"
    dropoff_point = models.JSONField(blank=True, null=True, help_text="GeoJSON Point")

    quantity = models.IntegerField(default=1)
    status = models.CharField(max_length=20, default=OrderStatus.PENDING, choices=OrderStatus.choices)
    ordered_via = models.CharField(max_length=20, default=OrderChannelChoices.WHATSAPP, choices=OrderChannelChoices.choices)
    
    note = models.CharField(max_length=500, null=True, blank=True)

    # NEW: Rider assignment (replaces string fields)
    rider = models.ForeignKey(
        'Rider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )

    # Track when rider was assigned for timeout logic
    rider_assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when rider was assigned to this order"
    )

    # DEPRECATED: Old rider string fields (kept for backward compatibility)
    rider_note = models.CharField(max_length=500, null=True, blank=True)
    rider_name = models.CharField(max_length=250, null=True, blank=True)
    rider_company = models.CharField(max_length=250, null=True, blank=True)
    rider_phone = models.CharField(max_length=250, null=True, blank=True)

    # NEW: 4-digit confirmation code for delivery
    confirmation_code = models.CharField(
        max_length=5,
        null=True,
        blank=True
    )

    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='orders')

    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    meal_price = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    paid = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # NEW: Restaurant payment tracking
    restaurant_payment_completed = models.BooleanField(default=False)
    restaurant_payment_transaction_id = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    restaurant_payment_completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def pickup_point_link(self):
        if self.pickup_point:
            coordinates = self.pickup_point.get('coordinates', [])
            if len(coordinates) == 2:
                lng, lat = coordinates
                return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"
        return None
    

    def dropoff_point_link(self):
        if self.dropoff_point:
            coordinates = self.dropoff_point.get('coordinates', [])
            if len(coordinates) == 2:
                lng, lat = coordinates
                return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"
        return None

    class Meta:
        indexes = [
            # Order history queries (very frequent)
            models.Index(fields=['user', '-created_at'], name='order_user_created_idx'),
            # Referral bonus check (first paid order)
            models.Index(fields=['user', 'paid'], name='order_user_paid_idx'),
            # Combined index for paid orders history
            models.Index(fields=['user', 'paid', '-created_at'], name='order_user_paid_created_idx'),
            # Order code lookups
            models.Index(fields=['code'], name='order_code_idx'),
            # Status filtering
            models.Index(fields=['status', '-created_at'], name='order_status_created_idx'),
            # Rider assignment timeout queries
            models.Index(fields=['rider', 'status', 'rider_assigned_at'], name='order_rider_timeout_idx'),
        ]

    def clean(self):
        super().clean()
        validate_geojson_point(self.pickup_point, field_name="pickup_point")
        validate_geojson_point(self.dropoff_point, field_name="dropoff_point")

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = unique_order_code()

        if not self.confirmation_code:
            self.confirmation_code = generate_confirmation_code()

        self.full_clean()
        super().save(*args, **kwargs)
