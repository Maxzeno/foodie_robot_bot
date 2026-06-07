from django.db import models
from api.models.base import BaseModel
from api.models.meal import Meal
from api.models.location import City


class SpecialOccasion(BaseModel):
    """
    Represents special dates/occasions where certain meals should be recommended
    with higher probability.

    Example: Christmas Day (Dec 25) - Rice and Chicken in Nigeria
    """

    name = models.CharField(
        max_length=255,
        help_text="Name of the occasion (e.g., 'Christmas Day', 'New Year's Eve')"
    )

    # Date handling - supports both recurring and specific dates
    month = models.IntegerField(
        help_text="Month (1-12) for recurring annual occasions"
    )
    day = models.IntegerField(
        help_text="Day of month (1-31)"
    )
    year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Specific year (leave blank for recurring annual occasion)"
    )

    is_recurring = models.BooleanField(
        default=True,
        help_text="If True, this occasion repeats every year"
    )

    # Relationships
    meals = models.ManyToManyField(
        Meal,
        related_name='special_occasions',
        help_text="Meals to boost for this occasion"
    )

    cities = models.ManyToManyField(
        City,
        related_name='special_occasions',
        blank=True,
        help_text="Cities where this occasion applies (leave empty for all cities)"
    )

    # Boost configuration
    boost_weight = models.FloatField(
        default=50.0,
        help_text="Score boost to apply (e.g., 50.0 for strong boost, 20.0 for moderate)"
    )

    # Activation
    active = models.BooleanField(
        default=True,
        help_text="Enable/disable this occasion without deleting"
    )

    description = models.TextField(
        blank=True,
        help_text="Optional description or notes about this occasion"
    )

    class Meta:
        ordering = ['month', 'day']
        verbose_name = "Special Occasion"
        verbose_name_plural = "Special Occasions"
        indexes = [
            models.Index(fields=['month', 'day', 'active']),
            models.Index(fields=['year', 'active']),
        ]

    def __str__(self):
        date_str = f"{self.month}/{self.day}"
        if self.year and not self.is_recurring:
            date_str += f"/{self.year}"
        return f"{self.name} ({date_str})"

    @property
    def date_display(self):
        """Human-readable date display"""
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        month_name = months[self.month - 1] if 1 <= self.month <= 12 else str(self.month)

        if self.is_recurring:
            return f"{month_name} {self.day} (Annual)"
        elif self.year:
            return f"{month_name} {self.day}, {self.year}"
        else:
            return f"{month_name} {self.day}"

    @classmethod
    def get_active_occasions_for_date(cls, date, city=None):
        """
        Get all active special occasions for a given date and optional city.

        Args:
            date: datetime.date object
            city: City instance (optional)

        Returns:
            QuerySet of SpecialOccasion objects
        """
        from django.db.models import Q

        # Build query for date matching
        date_query = Q(
            month=date.month,
            day=date.day,
            active=True
        ) & (
            Q(is_recurring=True) |  # Recurring occasions
            Q(is_recurring=False, year=date.year)  # Specific year occasions
        )

        # Base queryset
        queryset = cls.objects.filter(date_query)

        # City filter: include occasions with no cities (global) or matching city
        if city:
            queryset = queryset.filter(
                Q(cities__isnull=True) | Q(cities=city)
            ).distinct()
        else:
            # If no city provided, only return global occasions
            queryset = queryset.filter(cities__isnull=True)

        return queryset
