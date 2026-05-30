from django.db import models
from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.meal import Meal
from api.models.user import User
from django.contrib.gis.db import models as gis_models

from api.utils.generate import generate_unique_code


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
    pickup_point = gis_models.PointField(srid=4326, blank=True, null=True)
    
    dropoff_street_address = models.CharField(max_length=255, blank=True, null=True) # e.g. "123 Allen Avenue"
    dropoff_point = gis_models.PointField(srid=4326, blank=True, null=True)

    quantity = models.IntegerField(default=1)
    status = models.CharField(max_length=20, default=OrderStatus.PENDING, choices=OrderStatus.choices)
    ordered_via = models.CharField(max_length=20, default=OrderChannelChoices.WHATSAPP, choices=OrderChannelChoices.choices)
    
    note = models.CharField(max_length=250, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='orders')

    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    meal_price = models.DecimalField(max_digits=8, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2)
    paid = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)


    def save(self, *args, **kwargs):
        if not self.code:
            self.code = unique_order_code()

        super().save(*args, **kwargs)