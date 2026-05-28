from typing import Optional
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.meal import Allergy, FitnessGoal, HealthCondition, PreferredCuisine
from api.models.location import City
from api.models.message import Message, RoleChoices
from api.utils.generate import generate_unique_code


def unique_user_code():
    return generate_unique_code(User, field='code')


class GenderChoices(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'


class User(AbstractUser, BaseModel):
    email = models.EmailField(unique=True, null=True, blank=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    username = models.CharField(unique=True, max_length=200, null=True, blank=True)
    
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
    
    def get_intent(self, message_id:Optional[str]=None):
        if message_id:
            try:
                message = self.messages.filter(role=RoleChoices.BOT).get(message_id=message_id)
                return message.current_intent
            except Message.DoesNotExist:
                return None
            
        message = self.messages.filter(role=RoleChoices.BOT).first()
        if message:
            return message.current_intent
        return None
    