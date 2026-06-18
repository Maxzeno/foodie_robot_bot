
from django.db import models

from api.models.base import BaseModel
from api.models.order import Order
from api.models.user import User
from django.core.validators import MinValueValidator, MaxValueValidator


class SentimentChoices(models.TextChoices):
    LIKE = 'like', 'Like'
    NEUTRAL = 'neutral', 'Neutral'
    HATE = 'hate', 'Hate'

class Review(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reviews")
    meal_rating = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)], help_text="Meal rating from 1 to 5")
    sentiment = models.CharField(max_length=7, choices=SentimentChoices.choices)
    comment = models.TextField(blank=True)

    class Meta:
        indexes = [
            # User reviews history
            models.Index(fields=['user', '-created_at'], name='review_user_created_idx'),
            # Check if review exists for order
            models.Index(fields=['order'], name='review_order_idx'),
            # Filter by sentiment
            models.Index(fields=['sentiment', '-created_at'], name='review_sentiment_created_idx'),
            # User reviews by sentiment
            models.Index(fields=['user', 'sentiment'], name='review_user_sentiment_idx'),
        ]

    def __str__(self):
        return f"{self.user} - {self.order} ({self.sentiment}, {self.meal_rating} stars)"
