
from django.db import models

from api.models.base import BaseModel
from api.models.order import Order
from api.models.user import User


class SentimentChoices(models.TextChoices):
    LIKE = 'like', 'Like'
    NEUTRAL = 'neutral', 'Neutral'
    HATE = 'hate', 'Hate'

class Review(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="reviews")
    sentiment = models.CharField(max_length=7, choices=SentimentChoices.choices)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user} - {self.order} ({self.sentiment})"
    