from django.db import models
from api.models.base import BaseModel
from api.models.user import User


class Rider(BaseModel):
    """
    Rider profile - extends User with rider-specific fields.
    Can be independent or belong to a company.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='rider_profile'
    )

    # Company relationship - nullable for independent riders
    company = models.ForeignKey(
        'Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='riders'
    )

    # Rider status
    is_online = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    # Statistics (denormalized for performance)
    # total_deliveries = models.IntegerField(default=0)
    # completed_today = models.IntegerField(default=0)
    # average_rating = models.DecimalField(
    #     max_digits=3,
    #     decimal_places=2,
    #     default=0.00
    # )
    # total_earnings = models.DecimalField(
    #     max_digits=12,
    #     decimal_places=2,
    #     default=0.00
    # )

    class Meta:
        indexes = [
            models.Index(fields=['user'], name='rider_user_idx'),
            models.Index(fields=['company'], name='rider_company_idx'),
            models.Index(fields=['is_online'], name='rider_online_idx'),
            models.Index(fields=['is_online', 'company'], name='rider_online_company_idx'),
        ]

    def __str__(self):
        return f"Rider: {self.user.email or self.user.phone}"
