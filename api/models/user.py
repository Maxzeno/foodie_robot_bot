from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.meal import Allergy, FitnessGoal, HealthCondition, PreferredCuisine
from api.models.location import City
from api.utils.generate import generate_unique_code


def unique_user_code():
    return generate_unique_code(User, field='code')


class GenderChoices(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'


class CurrentIntentChoices(models.TextChoices):
    REGISTERED = 'registered', 'Registered'
    SET_PREFERENCE = 'set_preference', 'Set Preference'
    UPDATE_PREFERENCE = 'update_preference', 'Update Preference'
    FIRST_LOCATION = 'first_location', 'First Location'
    FIRST_LOCATION_RETRY = 'first_location_retry', 'First Location Retry'
    RECOMMENDED_MEALS = 'recommended_meals', 'Recommended Meals'

    # def get_intent_summary(intent):
    #     summaries = {
    #         CurrentIntentChoices.REGISTERED: "User has registered",
    #         CurrentIntentChoices.SET_PREFERENCE: "Setting user preferences",
    #         CurrentIntentChoices.UPDATE_PREFERENCE: "Updating user preferences",
    #         CurrentIntentChoices.FIRST_LOCATION: "Setting user's first location",
    #         CurrentIntentChoices.FIRST_LOCATION_RETRY: "Retrying to set user's first location",
    #         CurrentIntentChoices.RECOMMENDED_MEALS: "Recommending meals to user",
    #     }
    #     return summaries.get(intent, "Unknown intent")


class User(AbstractUser, BaseModel):
    email = models.EmailField(unique=True, null=True, blank=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    username = models.CharField(unique=True, max_length=200, null=True, blank=True)
    current_intent = models.CharField(max_length=100, choices=CurrentIntentChoices.choices, null=True, blank=True)
    
    code = models.CharField(max_length=100, unique=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='users', null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='users', null=True, blank=True)
    average_meal_budget = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

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

    fitness_goals = models.ForeignKey(FitnessGoal, on_delete=models.PROTECT, related_name="users", null=True, blank=True)
    health_conditions = models.ManyToManyField(HealthCondition, blank=True, related_name="users")
    allergies = models.ManyToManyField(Allergy, blank=True, related_name="users")
    preferred_cuisine = models.ManyToManyField(PreferredCuisine, blank=True, related_name="user")

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip()
        
        if self.password:
            self.password = self.password.strip()

        if self.username:
            self.username = self.username.strip()
        
        if not self.code:
            self.code = unique_user_code()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.phone}"
    