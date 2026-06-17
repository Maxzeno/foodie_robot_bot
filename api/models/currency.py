from django.db import models
from api.models.base import BaseModel  # if you have a common base class

class Currency(BaseModel):
    code = models.CharField(
        max_length=3,
        unique=True,
        help_text="ISO 4217 currency code (e.g. NGN, USD, EUR, GBP)",
    )
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Full currency name (e.g. Nigerian Naira, US Dollar)"
    )
    symbol = models.CharField(
        max_length=5,
        help_text="Currency symbol (e.g. ₦, $, €, £)"
    )
    active = models.BooleanField(default=True)

    # minimum_withdrawal = models.DecimalField(max_digits=12, decimal_places=2) TODO: might be added and implemented later


    def __str__(self):
        return f"{self.code} ({self.symbol})"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()

        if self.symbol:
            self.symbol = self.symbol.strip()

        if self.name:
            self.name = self.name.strip()

        super().save(*args, **kwargs)
