from django.db import models
from api.models.base import BaseModel
from api.models.user import User
from api.models.location import City # adjust path to where you placed City
from djgeojson.fields import PointField


class DeliveryAddress(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="delivery_addresses"
    )
    city = models.ForeignKey(
        City, on_delete=models.PROTECT, related_name="delivery_addresses"
    )

    street_address = models.CharField(max_length=255) # e.g. "123 Allen Avenue"
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    point = PointField()

    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Delivery Address"
        verbose_name_plural = "Delivery Addresses"

    def __str__(self):
        return f"{self.street_address}, {self.city.name}"
