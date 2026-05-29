from django.db import models
from api.models.base import BaseModel
from api.models.meal import Meal, TimeOfDayChoices
from api.models.user import User
from django.utils import timezone


class ChoiceOption(models.TextChoices):
    FIRST = 'first', 'First'
    SECOND = 'second', 'Second'


class Recommendation(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recommendations")
    meal = models.ForeignKey(Meal, on_delete=models.PROTECT, related_name="recommendations")
    time_of_day = models.CharField(max_length=20, choices=TimeOfDayChoices.choices)
    choice_option = models.CharField(max_length=20, choices=ChoiceOption.choices)
    day = models.DateField(default=timezone.now)
    sent_to_user = models.BooleanField(default=False)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=['user', 'day', 'time_of_day', 'choice_option'],
        #         name='unique_recommendation_per_slot'
        #     )
        # ]
        