from django.db import models
from api.models.address import DeliveryAddress
from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.meal import Meal
from api.models.user import User


class OrderStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    DISPATCHED = 'dispatched', 'Dispatched'
    ARRIVED = 'arrived', 'Arrived'
    RECEIVED = 'received', 'Received'


class OrderChannelChoices(models.TextChoices):
    WHATSAPP = 'whatsapp', 'Whatsapp'
    ONLINE = 'online', 'Online'


class Order(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    meal = models.ForeignKey(Meal, on_delete=models.PROTECT, related_name="orders")
    delivery_address = models.ForeignKey(DeliveryAddress, on_delete=models.PROTECT, related_name="orders")

    quantity = models.IntegerField(default=1)
    status = models.CharField(max_length=20, default=OrderStatus.PENDING, choices=OrderStatus.choices)
    ordered_via = models.CharField(max_length=20, default=OrderChannelChoices.WHATSAPP, choices=OrderChannelChoices.choices)
    
    note = models.CharField(max_length=250, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='orders')

    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=8, decimal_places=2)
    paid = models.BooleanField(default=False)
