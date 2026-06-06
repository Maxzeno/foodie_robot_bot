from django.db import models
from decimal import Decimal

from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.referral_earning import ReferralEarning
from api.models.user import User
from django.db import transaction


class UserBalance(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="balances"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Balance amount in the specified currency"
    )

    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name='user_balances'
    )

    class Meta:
        unique_together = ('user', 'currency')
        ordering = ['-created_at']
        verbose_name = "User Balance"
        verbose_name_plural = "User Balances"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user', 'currency']),
        ]

    def __str__(self):
        return f"{self.user.code}: {self.amount} {self.currency.code}"

    @classmethod
    def get_balance(cls, user, currency):
        balance, created = cls.objects.get_or_create(
            user=user,
            currency=currency,
            defaults={'amount': Decimal('0.00')}
        )
        return balance

    @classmethod
    def add_balance(cls, user, amount, currency):
        balance = cls.get_balance(user, currency)
        balance.amount += Decimal(str(amount))
        balance.save()
        return balance

    @classmethod
    def subtract_balance(cls, user, amount, currency):
        balance = cls.get_balance(user, currency)
        if balance.amount < Decimal(str(amount)):
            raise ValueError(
                f"Insufficient balance. "
                f"Available: {balance.amount} {currency.code}, "
                f"Required: {amount} {currency.code}"
            )
        balance.amount -= Decimal(str(amount))
        balance.save()
        return balance

    @classmethod
    def add_referral_earning(cls, referred_by_user, referred_user, city):
        with transaction.atomic():
            # Create the referral earning record
            referral_earning = ReferralEarning.objects.create(
                user=referred_by_user,
                referred_user=referred_user,
                amount=city.referral_bonus,
                currency=city.currency,
                city=city
            )

            # Update the user's balance
            balance = cls.add_balance(
                user=referred_by_user,
                amount=city.referral_bonus,
                currency=city.currency
            )

        return referral_earning, balance
