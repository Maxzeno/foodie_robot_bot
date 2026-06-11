from django.db import models
from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.meal import Meal
from api.models.user import User

from api.utils.generate import generate_unique_code
from api.utils.validation import validate_geojson_point


class OrderStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    DISPATCHED = 'dispatched', 'Dispatched'
    ARRIVED = 'arrived', 'Arrived'
    RECEIVED = 'received', 'Received'


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
    
    rider_note = models.CharField(max_length=500, null=True, blank=True)
    rider_name = models.CharField(max_length=250, null=True, blank=True)
    rider_company = models.CharField(max_length=250, null=True, blank=True)
    rider_phone = models.CharField(max_length=250, null=True, blank=True)
    
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='orders')

    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    meal_price = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    paid = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)


    def clean(self):
        super().clean()
        validate_geojson_point(self.pickup_point, field_name="pickup_point")
        validate_geojson_point(self.dropoff_point, field_name="dropoff_point")

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = unique_order_code()

        self.full_clean()
        super().save(*args, **kwargs)
