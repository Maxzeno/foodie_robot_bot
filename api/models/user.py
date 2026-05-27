from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

from api.models.base import BaseModel, Currency
from api.models.location import City
from api.utils.generate import generate_unique_code


def unique_user_code():
    return generate_unique_code(User, field='code')


# Custom User Model
class Gender(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'


class User(AbstractUser, BaseModel):
    email = models.EmailField(unique=True, null=True, blank=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    username = models.CharField(unique=True, max_length=200, null=True, blank=True)
    code = models.CharField(max_length=100, unique=True, blank=True)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='users')

    gender = models.CharField(max_length=10, blank=True, null=True, choices=Gender.choices)
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

    health_conditions = models.ManyToManyField("HealthCondition", blank=True, related_name="users")
    fitness_goals = models.ManyToManyField("FitnessGoal", blank=True, related_name="users")
    allergies = models.ManyToManyField("Allergy", blank=True, related_name="users")

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip()
        
        if self.password:
            self.password = self.password.strip()

        if self.username:
            self.username = self.password.strip()
        
        if not self.code:
            self.code = unique_user_code()

        super().save(*args, **kwargs)
