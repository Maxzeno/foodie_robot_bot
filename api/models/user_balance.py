from django.db import models
from decimal import Decimal

from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.user import User


class BalanceType(models.TextChoices):
    REFERRAL = 'referral', 'Referral Earnings'
    WALLET = 'wallet', 'Wallet Balance'
    BONUS = 'bonus', 'Bonus Balance'

    @classmethod
    def list_values(cls):
        return [choice.value.replace('_', ' ') for choice in cls]

class UserBalance(BaseModel):
    """
    Tracks user balances by type and currency.

    This model allows users to have multiple balances in different currencies.
    For example:
    - Referral earnings in NGN
    - Referral earnings in USD
    - Wallet balance in NGN
    - Wallet balance in USD

    This design is scalable and allows for easy addition of new balance types.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="balances"
    )
    balance_type = models.CharField(
        max_length=20,
        choices=BalanceType.choices,
        help_text="Type of balance (referral, wallet, bonus, etc.)"
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
        unique_together = ('user', 'balance_type', 'currency')
        ordering = ['-created_at']
        verbose_name = "User Balance"
        verbose_name_plural = "User Balances"
        indexes = [
            models.Index(fields=['user', 'balance_type']),
            models.Index(fields=['user', 'balance_type', 'currency']),
        ]

    def __str__(self):
        return f"{self.user.code} - {self.balance_type}: {self.amount} {self.currency.code}"

    @classmethod
    def get_balance(cls, user, balance_type, currency):
        """
        Get a specific balance for a user by type and currency.
        Creates the balance record if it doesn't exist.

        Args:
            user: User instance
            balance_type: BalanceType choice
            currency: Currency instance

        Returns:
            UserBalance instance
        """
        balance, created = cls.objects.get_or_create(
            user=user,
            balance_type=balance_type,
            currency=currency,
            defaults={'amount': Decimal('0.00')}
        )
        return balance

    @classmethod
    def get_balances_by_type(cls, user, balance_type):
        """
        Get all balances for a user by type, grouped by currency.

        Args:
            user: User instance
            balance_type: BalanceType choice

        Returns:
            QuerySet of UserBalance instances
        """
        return cls.objects.filter(
            user=user,
            balance_type=balance_type
        ).select_related('currency').order_by('currency__code')

    @classmethod
    def add_balance(cls, user, balance_type, amount, currency):
        """
        Add to a user's balance of a specific type and currency.

        Args:
            user: User instance
            balance_type: BalanceType choice
            amount: Decimal amount to add
            currency: Currency instance

        Returns:
            Updated UserBalance instance
        """
        balance = cls.get_balance(user, balance_type, currency)
        balance.amount += Decimal(str(amount))
        balance.save()
        return balance

    @classmethod
    def subtract_balance(cls, user, balance_type, amount, currency):
        """
        Subtract from a user's balance of a specific type and currency.

        Args:
            user: User instance
            balance_type: BalanceType choice
            amount: Decimal amount to subtract
            currency: Currency instance

        Returns:
            Updated UserBalance instance

        Raises:
            ValueError: If insufficient balance
        """
        balance = cls.get_balance(user, balance_type, currency)
        if balance.amount < Decimal(str(amount)):
            raise ValueError(
                f"Insufficient {balance_type} balance. "
                f"Available: {balance.amount} {currency.code}, "
                f"Required: {amount} {currency.code}"
            )
        balance.amount -= Decimal(str(amount))
        balance.save()
        return balance

    @classmethod
    def get_total_balance_by_type(cls, user, balance_type):
        """
        Get total balance for a user by type across all currencies.
        Note: This returns a dict of currency codes to amounts.

        Args:
            user: User instance
            balance_type: BalanceType choice

        Returns:
            dict: {currency_code: total_amount}
        """
        balances = cls.get_balances_by_type(user, balance_type)
        return {
            balance.currency.code: balance.amount
            for balance in balances
            if balance.amount > 0
        }
