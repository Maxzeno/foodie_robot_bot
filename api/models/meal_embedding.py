from django.db import models
from django.contrib.postgres.fields import ArrayField
from api.models.base import BaseModel
from api.models.meal import Meal


class MealEmbedding(BaseModel):
    """
    Stores OpenAI embeddings for meals to enable semantic similarity.

    Embeddings are cached here to avoid repeated API calls:
    - Cost: ~$0.02 per 1000 meals (text-embedding-3-small)
    - Regenerate when meal attributes change (tracked via content_hash)
    """

    meal = models.OneToOneField(
        Meal,
        on_delete=models.CASCADE,
        related_name='embedding_cache',
        primary_key=True
    )

    # The embedding vector (1536 dimensions for text-embedding-3-small)
    embedding = ArrayField(
        models.FloatField(),
        size=1536,
        help_text="OpenAI embedding vector for semantic similarity"
    )

    # Hash of meal attributes used to generate embedding
    # When this changes, embedding needs to be regenerated
    content_hash = models.CharField(
        max_length=32,
        db_index=True,
        help_text="MD5 hash of meal attributes used for embedding"
    )

    # Store the text that was embedded (for debugging)
    embedding_text = models.TextField(
        blank=True,
        help_text="The text that was sent to OpenAI for embedding (truncated)"
    )

    class Meta:
        verbose_name = "Meal Embedding"
        verbose_name_plural = "Meal Embeddings"

    def __str__(self):
        return f"Embedding for {self.meal.name}"
