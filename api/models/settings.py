from django.db import models
from django.core.exceptions import ValidationError

from api.models.base import BaseModel


class AppSettings(BaseModel):
    minimum_withdrawal = models.DecimalField(max_digits=12, decimal_places=2)
    whatsapp_support_phone_number = models.CharField(max_length=20)
    whatsapp_phone_number = models.CharField(max_length=20)

    # enforce only 1 row
    def save(self, *args, **kwargs):
        if not self.pk and AppSettings.objects.exists():
            raise ValidationError("Only one AppSettings instance is allowed.")
        return super().save(*args, **kwargs)
    
    @staticmethod
    def get_settings():
        defaults = {
            "minimum_withdrawal": 500,
            "whatsapp_support_phone_number": "+2349077745730",
            "whatsapp_phone_number": "+2349131860604"
        }

        obj = AppSettings.objects.first()
        if obj is None:
            obj = AppSettings.objects.create(**defaults)
        return obj

    def __str__(self):
        return "App Settings"
