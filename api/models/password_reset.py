from django.db import models
from django.utils import timezone
from datetime import timedelta
import random

from api.models.base import BaseModel
from api.models.user import User


class PasswordReset(BaseModel):
    """
    Store password reset codes (8-digit, 15-minute expiry).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_resets'
    )

    code = models.CharField(max_length=8)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)  # Track if code was verified

    class Meta:
        indexes = [
            models.Index(fields=['user', 'code'], name='pwd_reset_user_code_idx'),
            models.Index(fields=['expires_at'], name='pwd_reset_expires_idx'),
        ]

    def __str__(self):
        return f"PasswordReset for {self.user.email or self.user.phone} - {self.code}"

    @classmethod
    def generate_code(cls, user):
        """Generate 8-digit reset code, expires in 15 minutes."""
        code = str(random.randint(10000000, 99999999))
        expires_at = timezone.now() + timedelta(minutes=15)

        # Invalidate any existing codes for this user
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        return cls.objects.create(
            user=user,
            code=code,
            expires_at=expires_at
        )

    def is_valid(self):
        """Check if code is still valid."""
        return (
            not self.is_used and
            self.expires_at > timezone.now()
        )
