from typing import Optional
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

from api.models.base import BaseModel
from api.models.meal import Allergy, FitnessGoal, HealthCondition, PreferredCuisine
from api.models.location import City
from api.models.message import CurrentIntentChoices, Message, RoleChoices
from api.utils.generate import generate_unique_code
import pytz
from django.utils import timezone


def unique_user_code():
    return generate_unique_code(User, field='code')


class GenderChoices(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'


class UserRole(models.TextChoices):
    CUSTOMER = 'customer', 'Customer'
    RIDER = 'rider', 'Rider'
    COMPANY = 'company', 'Company'


class User(AbstractUser, BaseModel):
    email = models.EmailField(unique=True, null=True, blank=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    username = models.CharField(unique=True, max_length=200, null=True, blank=True)

    code = models.CharField(max_length=100, unique=True, blank=True)
    def default_roles():
        return ["customer"]
    
    # Multiple roles support (customer, rider, company)
    roles = models.JSONField(
        default=default_roles,
        help_text="List of user roles: ['customer'], ['rider'], ['company'], or combinations"
    )
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='users', null=True, blank=True)
    # currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='users', null=True, blank=True)
    average_meal_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    gender = models.CharField(max_length=10, choices=GenderChoices.choices, null=True, blank=True)
    phone = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Enter a valid phone number (e.g., +2348044467208)."
            )
        ],
    )

    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    
    is_online = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)

    fitness_goals = models.ForeignKey(FitnessGoal, on_delete=models.PROTECT, related_name="users", null=True, blank=True)
    health_conditions = models.ManyToManyField(HealthCondition, blank=True, related_name="users")
    allergies = models.ManyToManyField(Allergy, blank=True, related_name="users")
    preferred_cuisine = models.ManyToManyField(PreferredCuisine, blank=True, related_name="user")

    referred_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals"
    )
    referral_message_sent = models.BooleanField(
        default=False,
        help_text="Whether the user has been sent the referral invitation message"
    )
    registration_reminder_sent = models.BooleanField(
        default=False,
        help_text="Whether the user has been sent the registration completion reminder"
    )

    class Meta:
        indexes = [
            # Phone number lookups (most frequent - user authentication)
            models.Index(fields=['phone'], name='user_phone_idx'),
            # User code lookups (referral system)
            models.Index(fields=['code'], name='user_code_idx'),
            # Filter users by city
            models.Index(fields=['city', 'is_active'], name='user_city_active_idx'),
            # Filter blocked users
            models.Index(fields=['is_blocked'], name='user_blocked_idx'),
            # Referral tracking
            models.Index(fields=['referred_by'], name='user_referred_by_idx'),
        ]

    def set_password(self, raw_password, user=None):
        if not user or user and user.password != self.password:
            super().set_password(raw_password)
        
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip()
        
        if self.password:
            self.password = self.password.strip()

        if self.username:
            self.username = self.username.strip()
        
        if not self.code:
            self.code = unique_user_code()


        if not self._password:
            user = None
            if self.pk:
                user = self.__class__.objects.filter(pk=self.pk).first()
            self.set_password(self.password, user)

        super().save(*args, **kwargs)

    def has_role(self, role):
        """Check if user has a specific role."""
        return role in self.roles

    def add_role(self, role):
        """Add a role to user."""
        if role not in self.roles:
            self.roles.append(role)
            self.save()

    def remove_role(self, role):
        """Remove a role from user."""
        if role in self.roles:
            self.roles.remove(role)
            self.save()

    def __str__(self):
        return f"{self.code} - {self.phone}"
    
    def get_intent(self, message_id:Optional[str]=None):
        if message_id:
            try:
                message = self.messages.filter(role=RoleChoices.BOT).get(message_id=message_id)
                return message.current_intent
            except Message.DoesNotExist:
                return None
            
        message = self.messages.filter(role=RoleChoices.BOT).exclude(current_intent=CurrentIntentChoices.NO_INTENT).first()
        if message:
            return message.current_intent
        return None
    
    def get_user_timezone(self):
        if self.city and self.city.timezone:
            try:
                return pytz.timezone(self.city.timezone)
            except pytz.UnknownTimeZoneError:
                return pytz.UTC
        return pytz.UTC
    
    def get_local_time(self):
        user_timezone = self.get_user_timezone()
        utc_now = timezone.now()  # Django's timezone-aware current time (UTC)
        return utc_now.astimezone(user_timezone)
    
    def get_time_period(self):
        local_time = self.get_local_time()
        hour = local_time.hour

        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 19:
            return 'evening'
        else:
            return 'night'
        
    def get_recommendation_day_number(self) -> int:
        """
        Calculate which day of recommendations this is for the user.
        Returns the number of unique days the user has received recommendations + 1 for today.
        """
        from api.models.recommendation import Recommendation

        today = self.get_local_time().date()

        # Count unique days with recommendations (excluding today)
        past_days = Recommendation.objects.filter(
            user=self,
            sent_to_user=True,
            day__lt=today
        ).values('day').distinct().count()

        return past_days + 1

    def get_recommendation_streak(self) -> int:
        """
        Calculate the user's current recommendation engagement streak.
        A streak is maintained when user receives recommendations on consecutive days.
        """
        from api.models.recommendation import Recommendation
        from datetime import timedelta

        today = self.get_local_time().date()

        # Get all unique days with recommendations, ordered descending
        recommendation_days = list(
            Recommendation.objects.filter(
                user=self,
                sent_to_user=True
            ).values_list('day', flat=True).distinct().order_by('-day')
        )

        if not recommendation_days:
            return 1  # First day

        streak = 1
        # Start from today or most recent day
        current_day = today

        # Check if today has a recommendation
        if recommendation_days and recommendation_days[0] == today:
            current_day = today
        elif recommendation_days:
            # If no recommendation today, check if yesterday had one
            yesterday = today - timedelta(days=1)
            if recommendation_days[0] != yesterday:
                return 1  # Streak broken
            current_day = yesterday
            streak = 1

        # Count consecutive days going backwards
        for rec_day in recommendation_days:
            if rec_day == current_day:
                continue
            expected_prev = current_day - timedelta(days=1)
            if rec_day == expected_prev:
                streak += 1
                current_day = rec_day
            elif rec_day < expected_prev:
                break

        return streak
