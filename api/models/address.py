from django.db import models
from api.models.base import BaseModel
from api.models.user import User


class DeliveryAddress(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="delivery_addresses"
    )

    name = models.CharField(max_length=255, blank=True, null=True) # e.g. "Shoprite"
    street_address = models.CharField(max_length=255, blank=True, null=True) # e.g. "123 Allen Avenue"
    point = models.JSONField(blank=True, null=True, help_text="GeoJSON Point")

    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Delivery Address"
        verbose_name_plural = "Delivery Addresses"

    def __str__(self):
        return f"{self.point} - {self.name}"
