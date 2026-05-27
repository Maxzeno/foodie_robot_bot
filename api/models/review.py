
from django.db import models

from api.models.base import BaseModel
from api.models.meal import Meal
from api.models.user import User


class SentimentChoices(models.TextChoices):
    LIKE = 'like', 'Like'
    NEUTRAL = 'neutral', 'Neutral'
    HATE = 'hate', 'Hate'

class Review(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    meal = models.ForeignKey(Meal, on_delete=models.PROTECT, related_name="reviews")
    sentiment = models.CharField(max_length=7, choices=SentimentChoices.choices)
    like_but_dislike_preparation = models.BooleanField(
        default=False,
        help_text="Check if you like the meal itself but dislike how it was prepared this time."
    )
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user} - {self.meal} ({self.sentiment})"
    