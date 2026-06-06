from django.db import models

from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.user import User


class WithdrawalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Withdrawal(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="withdrawals"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='withdrawals')
    
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=255)
    rejection_reason = models.CharField(max_length=255, null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=WithdrawalStatus.choices,
        default=WithdrawalStatus.PENDING
    )
    payment_reference = models.CharField(
        max_length=255, null=True, blank=True
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.code} withdrew {self.amount} ({self.status})"
