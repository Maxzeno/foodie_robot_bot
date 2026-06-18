
from django.db import models

from api.models.base import BaseModel
from api.models.meal import Meal
from api.models.user import User


class MealPreferenceChoices(models.TextChoices):
    LIKE = 'like', 'Like'
    NEUTRAL = 'neutral', 'Neutral'
    HATE = 'hate', 'Hate'

class MealPreference(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="meal_preferences")
    meal = models.ForeignKey(Meal, on_delete=models.PROTECT, related_name="meal_preferences")
    preference = models.CharField(max_length=7, choices=MealPreferenceChoices.choices)
    comment = models.TextField(blank=True)
    
    class Meta:
        unique_together = ('user', 'meal')
        ordering = ['-created_at']
        indexes = [
            # Filter user preferences (like/hate meals)
            models.Index(fields=['user', 'preference'], name='pref_user_pref_idx'),
            # Collaborative filtering (find similar users)
            models.Index(fields=['meal', 'preference'], name='pref_meal_pref_idx'),
            # Recent preferences
            models.Index(fields=['user', '-created_at'], name='pref_user_created_idx'),
        ]

    def __str__(self):
        return f"{self.user} - {self.meal} ({self.preference})"
    