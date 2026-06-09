# services/recommendation/meal_embedding.py
"""
Meal Embedding Service - Semantic Understanding of Meals

This service generates and caches OpenAI embeddings for meals to enable:
1. Semantic similarity detection (e.g., "Jollof Rice" similar to "Party Rice")
2. User taste profile matching
3. Content-based recommendations

Cost Optimization:
- Embeddings are cached in database (MealEmbedding model)
- Only regenerate when meal attributes change
- Uses text-embedding-3-small (~$0.00002 per 1K tokens, ~$0.02 for 1000 meals)
"""

import logging
import hashlib
import json
from typing import List, Dict, Optional, Set, Tuple
from django.conf import settings
from django.core.cache import cache
from openai import OpenAI

logger = logging.getLogger(__name__)


class MealEmbeddingService:
    """
    Service for generating and managing meal embeddings.

    Embeddings capture semantic meaning of meals based on:
    - Name and description
    - Cuisine type
    - Nutritional profile
    - Fitness goals alignment
    - Price category
    """

    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536
    CACHE_KEY_PREFIX = "meal_emb_"
    CACHE_TIMEOUT = 60 * 60 * 24 * 30  # 30 days

    # Batch size for OpenAI API calls (max 2048)
    BATCH_SIZE = 100

    def __init__(self, openai_client: OpenAI = None):
        self.client = openai_client or OpenAI(api_key=settings.OPENAI_API_KEY)

    def _create_meal_text(self, meal) -> str:
        """
        Create rich text representation of a meal for embedding.

        Combines multiple attributes to capture the meal's semantic identity.
        The order and format matters for embedding quality.
        """
        parts = []

        # Core identity
        parts.append(f"Meal: {meal.name}")

        if meal.description:
            # Truncate long descriptions
            desc = meal.description[:500] if len(meal.description) > 500 else meal.description
            parts.append(f"Description: {desc}")

        # Cuisine (important for taste matching)
        cuisines = list(meal.cuisine.values_list('name', flat=True))
        if cuisines:
            cuisine_names = [c.replace('_', ' ').title() for c in cuisines]
            parts.append(f"Cuisine: {', '.join(cuisine_names)}")

        # Fitness goals (important for health-conscious users)
        fitness_goals = list(meal.fitness_goals.values_list('name', flat=True))
        if fitness_goals:
            goal_names = [g.replace('_', ' ').title() for g in fitness_goals]
            parts.append(f"Suitable for: {', '.join(goal_names)}")

        # Nutritional profile (condensed)
        nutrition_parts = []
        if meal.calories:
            nutrition_parts.append(f"{int(meal.calories)} cal")
        if meal.protein:
            nutrition_parts.append(f"{int(meal.protein)}g protein")
        if meal.carbs:
            nutrition_parts.append(f"{int(meal.carbs)}g carbs")
        if meal.fats:
            nutrition_parts.append(f"{int(meal.fats)}g fat")
        if nutrition_parts:
            parts.append(f"Nutrition: {', '.join(nutrition_parts)}")

        # Price category (helps match budget preferences)
        if meal.price:
            price = float(meal.price)
            if price < 2000:
                parts.append("Price: Budget-friendly")
            elif price < 4000:
                parts.append("Price: Mid-range")
            else:
                parts.append("Price: Premium")

        # Time of day (contextual relevance)
        if meal.times_of_day:
            times = [t.title() for t in meal.times_of_day]
            parts.append(f"Best for: {', '.join(times)}")

        return "\n".join(parts)

    def _compute_content_hash(self, meal) -> str:
        """
        Compute hash of meal attributes to detect changes.

        When this hash changes, we need to regenerate the embedding.
        """
        content = {
            'name': meal.name,
            'description': meal.description or '',
            'cuisines': sorted(list(meal.cuisine.values_list('name', flat=True))),
            'fitness_goals': sorted(list(meal.fitness_goals.values_list('name', flat=True))),
            'calories': str(meal.calories) if meal.calories else '',
            'protein': str(meal.protein) if meal.protein else '',
            'carbs': str(meal.carbs) if meal.carbs else '',
            'fats': str(meal.fats) if meal.fats else '',
            'price': str(meal.price) if meal.price else '',
            'times_of_day': sorted(meal.times_of_day or []),
        }
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()

    def get_embedding(self, meal, force_refresh: bool = False) -> Optional[List[float]]:
        """
        Get embedding for a single meal, using cache when possible.

        Args:
            meal: Meal instance
            force_refresh: If True, regenerate embedding even if cached

        Returns:
            List of floats (embedding vector) or None if error
        """
        from api.models.meal_embedding import MealEmbedding

        # Check database cache first
        content_hash = self._compute_content_hash(meal)

        if not force_refresh:
            try:
                cached = MealEmbedding.objects.filter(
                    meal=meal,
                    content_hash=content_hash
                ).first()

                if cached:
                    logger.debug(f"Cache hit for meal {meal.id}: {meal.name}")
                    return cached.embedding
            except Exception as e:
                logger.warning(f"Error checking embedding cache: {e}")

        # Generate new embedding
        try:
            meal_text = self._create_meal_text(meal)

            response = self.client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=meal_text
            )
            embedding = response.data[0].embedding

            # Cache in database
            MealEmbedding.objects.update_or_create(
                meal=meal,
                defaults={
                    'embedding': embedding,
                    'content_hash': content_hash,
                    'embedding_text': meal_text[:2000]  # Store truncated text for debugging
                }
            )

            logger.info(f"Generated embedding for meal {meal.id}: {meal.name}")
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding for meal {meal.id}: {e}")
            return None

    def get_embeddings_batch(
        self,
        meals: List,
        force_refresh: bool = False
    ) -> Dict[int, List[float]]:
        """
        Get embeddings for multiple meals efficiently.

        Uses batched API calls to minimize latency and cost.

        Args:
            meals: List of Meal instances
            force_refresh: If True, regenerate all embeddings

        Returns:
            Dict mapping meal_id -> embedding vector
        """
        from api.models.meal_embedding import MealEmbedding

        result = {}
        meals_to_generate = []
        meal_hashes = {}

        # Compute content hashes
        for meal in meals:
            meal_hashes[meal.id] = self._compute_content_hash(meal)

        if not force_refresh:
            # Batch fetch existing embeddings
            existing = MealEmbedding.objects.filter(
                meal_id__in=[m.id for m in meals]
            ).values('meal_id', 'content_hash', 'embedding')

            existing_by_meal = {e['meal_id']: e for e in existing}

            for meal in meals:
                cached = existing_by_meal.get(meal.id)
                if cached and cached['content_hash'] == meal_hashes[meal.id]:
                    result[meal.id] = cached['embedding']
                else:
                    meals_to_generate.append(meal)
        else:
            meals_to_generate = list(meals)

        if not meals_to_generate:
            logger.info(f"All {len(meals)} embeddings found in cache")
            return result

        logger.info(f"Generating embeddings for {len(meals_to_generate)} meals "
                   f"({len(meals) - len(meals_to_generate)} cached)")

        # Generate in batches
        for i in range(0, len(meals_to_generate), self.BATCH_SIZE):
            batch = meals_to_generate[i:i + self.BATCH_SIZE]

            try:
                # Prepare texts
                texts = [self._create_meal_text(meal) for meal in batch]

                # Call OpenAI API
                response = self.client.embeddings.create(
                    model=self.EMBEDDING_MODEL,
                    input=texts
                )

                # Process results
                embeddings_to_save = []
                for j, meal in enumerate(batch):
                    embedding = response.data[j].embedding
                    result[meal.id] = embedding

                    embeddings_to_save.append(MealEmbedding(
                        meal=meal,
                        embedding=embedding,
                        content_hash=meal_hashes[meal.id],
                        embedding_text=texts[j][:2000]
                    ))

                # Bulk upsert
                MealEmbedding.objects.bulk_create(
                    embeddings_to_save,
                    update_conflicts=True,
                    update_fields=['embedding', 'content_hash', 'embedding_text', 'updated_at'],
                    unique_fields=['meal']
                )

                logger.info(f"Generated batch {i // self.BATCH_SIZE + 1}: "
                           f"{len(batch)} embeddings")

            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}")
                # Fall back to individual generation
                for meal in batch:
                    embedding = self.get_embedding(meal, force_refresh=True)
                    if embedding:
                        result[meal.id] = embedding

        return result

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def find_similar_meals(
        self,
        target_meal,
        candidate_meals: List,
        top_k: int = 10,
        min_similarity: float = 0.5
    ) -> List[Tuple[int, float]]:
        """
        Find meals most similar to a target meal.

        Args:
            target_meal: Meal to find similar items for
            candidate_meals: List of Meal instances to search
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (meal_id, similarity_score) tuples, sorted by similarity
        """
        target_embedding = self.get_embedding(target_meal)
        if not target_embedding:
            return []

        # Get embeddings for candidates
        candidate_ids = [m.id for m in candidate_meals if m.id != target_meal.id]
        embeddings = self.get_embeddings_batch(
            [m for m in candidate_meals if m.id != target_meal.id]
        )

        # Calculate similarities
        similarities = []
        for meal_id, embedding in embeddings.items():
            if embedding:
                sim = self.cosine_similarity(target_embedding, embedding)
                if sim >= min_similarity:
                    similarities.append((meal_id, sim))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def compute_meal_similarity_matrix(
        self,
        meals: List,
        min_similarity: float = 0.6
    ) -> Dict[int, List[Tuple[int, float]]]:
        """
        Pre-compute similarity relationships between meals.

        Useful for diversity enforcement - knowing which meals are
        semantically similar helps avoid repetition.

        Args:
            meals: List of Meal instances
            min_similarity: Only store pairs above this threshold

        Returns:
            Dict mapping meal_id -> list of (similar_meal_id, similarity) tuples
        """
        embeddings = self.get_embeddings_batch(meals)

        similarity_matrix = {}
        meal_ids = list(embeddings.keys())

        for i, meal_id_1 in enumerate(meal_ids):
            similar_meals = []
            emb1 = embeddings.get(meal_id_1)

            if not emb1:
                continue

            for meal_id_2 in meal_ids[i + 1:]:
                emb2 = embeddings.get(meal_id_2)
                if not emb2:
                    continue

                sim = self.cosine_similarity(emb1, emb2)

                if sim >= min_similarity:
                    similar_meals.append((meal_id_2, sim))

                    # Also add reverse relationship
                    if meal_id_2 not in similarity_matrix:
                        similarity_matrix[meal_id_2] = []
                    similarity_matrix[meal_id_2].append((meal_id_1, sim))

            if similar_meals:
                similarity_matrix[meal_id_1] = similar_meals

        logger.info(f"Computed similarity matrix: {len(similarity_matrix)} meals "
                   f"have similar meals (threshold: {min_similarity})")

        return similarity_matrix
