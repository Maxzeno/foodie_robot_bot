from django.db import models

from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.location import City
from api.models.user import User


class ReferralEarning(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="referral_earnings"
    )
    referred_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referral_earning_source"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='referral_earnings')
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='referral_earnings')

    def __str__(self):
        return f"{self.user.code} earned {self.amount}"
