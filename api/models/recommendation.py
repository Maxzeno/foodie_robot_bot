from django.db import models
from api.models.base import BaseModel
from api.models.meal import Meal
from api.models.user import User
from django.utils import timezone


class TimeOfDay(models.TextChoices):
    MORNING = 'morning', 'Morning'
    AFTERNOON = 'afternoon', 'Afternoon'
    EVENING = 'evening', 'Evening'

class ChoiceOption(models.TextChoices):
    FIRST = 'first', 'First'
    SECOND = 'second', 'Second'


class Recommendation(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recommendations")
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name="recommendations")
    time_of_day = models.CharField(max_length=20, choices=TimeOfDay.choices)
    choice_option = models.CharField(max_length=20, choices=ChoiceOption.choices)
    day = models.DateField(default=timezone.now)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'day', 'time_of_day', 'choice_option'],
                name='unique_recommendation_per_slot'
            )
        ]
        