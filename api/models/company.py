from django.db import models
from api.models.base import BaseModel
from api.models.user import User


class Company(BaseModel):
    """
    Delivery company that manages multiple riders.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='company_profile'
    )

    name = models.CharField(max_length=255)
    registration_number = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    # Statistics (denormalized for performance)
    # total_orders = models.IntegerField(default=0)
    # active_riders = models.IntegerField(default=0)
    # completed_today = models.IntegerField(default=0)
    # total_revenue = models.DecimalField(
    #     max_digits=12,
    #     decimal_places=2,
    #     default=0.00
    # )

    class Meta:
        indexes = [
            models.Index(fields=['user'], name='company_user_idx'),
        ]
        verbose_name_plural = 'Companies'

    def __str__(self):
        return f"{self.name} ({self.user.email or self.user.phone})"
