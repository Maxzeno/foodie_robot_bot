from django.db import models
from api.models.base import BaseModel
from api.models.meal import Meal


class MealEmbedding(BaseModel):
    """
    Stores meal embeddings to enable semantic similarity.

    Embeddings are cached here to avoid repeated API calls:
    - Regenerate when meal attributes change (tracked via content_hash)
    """

    meal = models.OneToOneField(
        Meal,
        on_delete=models.CASCADE,
        related_name='embedding_cache',
        primary_key=True
    )

    # The embedding vector (1536 dimensions)
    embedding = models.JSONField(
        help_text="Embedding vector for semantic similarity (1536 floats)"
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
        help_text="The text that was sent for embedding (truncated)"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Meal Embedding"
        verbose_name_plural = "Meal Embeddings"

    def __str__(self):
        return f"Embedding for {self.meal.name}"
