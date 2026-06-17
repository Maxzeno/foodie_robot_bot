from api.models.base import BaseModel
from django.db import models
from datetime import datetime, time
from api.utils.validation import validate_geojson_point

class DayOfWeekChoices(models.TextChoices):
    MONDAY = 'monday', 'Monday'
    TUESDAY = 'tuesday', 'Tuesday'
    WEDNESDAY = 'wednesday', 'Wednesday'
    THURSDAY = 'thursday', 'Thursday'
    FRIDAY = 'friday', 'Friday'
    SATURDAY = 'saturday', 'Saturday'
    SUNDAY = 'sunday', 'Sunday'


class Restaurant(BaseModel):
    name = models.CharField(max_length=250)
    phone = models.CharField(max_length=250)
    address = models.CharField(max_length=250)
    point = models.JSONField(blank=True, null=True, help_text="GeoJSON Point")

    email = models.CharField(max_length=250, blank=True, null=True)
    website = models.URLField(max_length=250, blank=True, null=True)
    social = models.URLField(max_length=250, blank=True, null=True)
    note = models.TextField(blank=True, null=True)

    # Business hours
    open_time = models.TimeField(
        default=time(6, 0),
        help_text="Restaurant opening time (default: 06:00)"
    )
    close_time = models.TimeField(
        default=time(22, 0),
        help_text="Restaurant closing time (default: 22:00)"
    )
    available_days = models.JSONField(
        default=list,
        blank=True,
        help_text="Days when restaurant is open (empty = open all days)"
    )

    # Status
    inactive = models.BooleanField(
        default=False,
        help_text="Set to True to disable this restaurant and all its meals"
    )

    inactive_but_still_recommend = models.BooleanField(
        default=False,
        help_text="Set to True to disable this restaurant and all its meals"
    )

    def __str__(self):
        return f"{self.name} - {self.phone} - {self.address} - {self.website} - {self.social}"

    def is_open_now(self, current_time=None, current_day=None):
        """
        Check if restaurant is currently open.

        Args:
            current_time: datetime.time object (defaults to current time)
            current_day: str lowercase day name (defaults to current day)

        Returns:
            bool: True if open, False otherwise
        """
        if self.inactive:
            return False

        # Use current time if not provided
        if current_time is None:
            current_time = datetime.now().time()

        if current_day is None:
            current_day = datetime.now().strftime('%A').lower()

        # Check if open on this day (if available_days is specified)
        if self.available_days and current_day not in self.available_days:
            return False

        # Check if within operating hours
        return self.open_time <= current_time <= self.close_time

    def clean(self):
        super().clean()
        validate_geojson_point(self.point, field_name="point")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
