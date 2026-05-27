from django.db import models
from django.utils import timezone

class Currency(models.TextChoices):
    USD = 'USD', 'US Dollar'
    EUR = 'EUR', 'Euro'
    NGN = 'NGN', 'Nigerian Naira'
    GBP = 'GBP', 'British Pound'
    
class BaseModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']
    