from django.db import models

from api.models.base import BaseModel
from api.models.user import User


class WithdrawalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class Withdrawal(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="referral_withdrawals"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=WithdrawalStatus.choices,
        default=WithdrawalStatus.PENDING
    )
    payment_reference = models.CharField(
        max_length=255, null=True, blank=True
    )  # Payment ref, bank ref, etc.
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.code} withdrew {self.amount} ({self.status})"
