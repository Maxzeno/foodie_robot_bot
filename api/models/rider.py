from django.db import models
from api.models.base import BaseModel
from api.models.user import User
from django.core.exceptions import ValidationError


class Rider(BaseModel):
    """
    Rider profile - extends User with rider-specific fields.
    Can be independent or belong to another rider who acts as a company.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='rider_profile'
    )

    # Self-referential FK: If set, this rider belongs to another rider (company)
    # The referenced rider is the company/manager for this rider
    company = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_riders',
        help_text="If set, this rider belongs to another rider who acts as their company"
    )

    # Company name - for riders who ARE companies (manage other riders)
    company_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Company name if this rider manages other riders"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='rider_user_idx'),
            models.Index(fields=['company'], name='rider_company_idx'),
        ]

    def __str__(self):
        return f"Rider: {self.user.email or self.user.phone}"

    @property
    def is_company(self):
        """Check if this rider acts as a company (has managed riders)."""
        return self.company is None


    def clean(self):
        """Validate business rules."""
        super().clean()
        
        # Rule: A rider that belongs to a company cannot have managed riders
        if self.company and self.managed_riders.exists():
            raise ValidationError(
                "A rider that belongs to a company cannot manage other riders. "
                "Only independent riders can act as companies."
            )
        
        # Rule: The company must not itself belong to another company (no chaining)
        if self.company and self.company.company:
            raise ValidationError(
                "Cannot assign a company that itself belongs to another company. "
                "Only independent riders can act as companies."
            )
    
    def save(self, *args, **kwargs):
        """Override save to always run validation."""
        # Run full_clean to trigger clean() method
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)