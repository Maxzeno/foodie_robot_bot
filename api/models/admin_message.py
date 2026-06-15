from django.db import models
from django.utils import timezone
from datetime import timedelta
from api.models.base import BaseModel
from api.models.location import City
from api.models.user import User


class MessageStatusChoices(models.TextChoices):
    PENDING = 'pending', 'Pending'
    SENDING = 'sending', 'Sending'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class BroadcastMessage(BaseModel):
    """
    Model to send messages to all active users in selected cities.
    Only sends to users within the 24-hour free service window.
    """
    content = models.TextField(
        help_text="The message content to send to users"
    )
    cities = models.ManyToManyField(
        City,
        blank=True,
        related_name='broadcast_messages',
        help_text="Select cities to send to. Leave empty to send to ALL cities."
    )
    image_url = models.URLField(
        max_length=1024,
        blank=True,
        null=True,
        help_text="Optional image URL to send with the message"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=MessageStatusChoices.choices,
        default=MessageStatusChoices.PENDING
    )
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    total_eligible = models.IntegerField(default=0)

    # Results
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Broadcast Message"
        verbose_name_plural = "Broadcast Messages"

    def __str__(self):
        cities_str = ", ".join(self.cities.values_list('name', flat=True)[:3])
        if self.cities.count() > 3:
            cities_str += f" +{self.cities.count() - 3} more"
        elif not cities_str:
            cities_str = "All Cities"
        return f"Broadcast to {cities_str}: {self.content[:50]}..."

    def get_eligible_users(self):
        """
        Get users who are:
        1. In the selected cities (or all cities if none selected)
        2. Within the 24-hour free service window (active in last 24 hours)
        3. Not blocked
        """
        from api.models.message import RoleChoices
        from django.db.models import Max, Q

        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)

        # Base queryset - active users within 24-hour window
        users = User.objects.annotate(
            last_user_message_time=Max(
                'messages__created_at',
                filter=Q(messages__role=RoleChoices.USER)
            )
        ).filter(
            last_user_message_time__isnull=False,
            last_user_message_time__gte=twenty_four_hours_ago,
            is_blocked=False,
            is_active=True
        )

        # Filter by cities if specified
        if self.cities.exists():
            users = users.filter(city__in=self.cities.all())

        return users


class SingleUserMessage(BaseModel):
    """
    Model to send a message to a single user.
    Only sends if the user is within the 24-hour free service window.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='admin_messages',
        help_text="Select the user to send the message to"
    )
    content = models.TextField(
        help_text="The message content to send"
    )
    image_url = models.URLField(
        max_length=1024,
        blank=True,
        null=True,
        help_text="Optional image URL to send with the message"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=MessageStatusChoices.choices,
        default=MessageStatusChoices.PENDING
    )
    error_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Single User Message"
        verbose_name_plural = "Single User Messages"

    def __str__(self):
        return f"Message to {self.user.code}: {self.content[:50]}..."

    def is_user_active(self):
        """
        Check if user is within the 24-hour free service window.
        """
        from api.models.message import RoleChoices, Message

        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)

        # Get user's last message time
        last_message = Message.objects.filter(
            user=self.user,
            role=RoleChoices.USER
        ).order_by('-created_at').first()

        if not last_message:
            return False

        return last_message.created_at >= twenty_four_hours_ago
