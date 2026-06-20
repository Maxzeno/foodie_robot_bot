from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets

from api.models.base import BaseModel
from api.models.user import User


class RefreshToken(BaseModel):
    """
    Store refresh tokens for JWT authentication.
    Allows token invalidation on logout.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='refresh_tokens'
    )

    token = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)

    # Track device/session
    device_info = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token'], name='refresh_token_idx'),
            models.Index(fields=['user', 'is_revoked'], name='refresh_user_revoked_idx'),
            models.Index(fields=['expires_at'], name='refresh_expires_idx'),
        ]

    def __str__(self):
        return f"RefreshToken for {self.user.email or self.user.phone}"

    @classmethod
    def generate_token(cls, user, expires_days=30):
        """Generate a new refresh token."""
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=expires_days)

        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )

    def is_valid(self):
        """Check if token is valid."""
        return not self.is_revoked and self.expires_at > timezone.now()
