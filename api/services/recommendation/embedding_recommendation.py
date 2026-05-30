# services/embedding_recommendation.py
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from api.models.meal import Meal
from api.models.recommendation import Recommendation
import logging

logger = logging.getLogger(__name__)


class EmbeddingRecommendationService:
    """
    Cost-optimized embedding-based meal recommendation system.

    Key features:
    - Uses cached embeddings (95%+ cost reduction vs LLM)
    - Multi-factor scoring: preferences, nutrition, budget, time-of-day
    - Avoids recent meals for variety
    - Ensures diversity in recommendations
    - Optimized for conversion
    """

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dimensions = 1536

    def get_recommendations(
        self,
        user,
        num_recommendations_per_period: int = 2,
        exclude_meal_ids: Optional[List[int]] = None
    ) -> Dict:
        """
        Get personalized meal recommendations for morning, afternoon, and evening.

        Returns:
            Dict with keys: morning, afternoon, evening (each containing meal IDs)
        """
        # Get eligible meals
        available_meals = self._get_eligible_meals(user, exclude_meal_ids)

        if not available_meals:
            return {
                "morning": [],
                "afternoon": [],
                "evening": []
            }

        # Ensure all meals have embeddings
        meals_needing_embeddings = [m for m in available_meals if not m.embedding]
        if meals_needing_embeddings:
            logger.info(f"Generating embeddings for {len(meals_needing_embeddings)} meals")
            self._generate_meal_embeddings(meals_needing_embeddings)
            # Refresh from DB to get updated embeddings
            meal_ids = [m.id for m in meals_needing_embeddings]
            Meal.objects.filter(id__in=meal_ids).update(embedding_generated_at=timezone.now())

        # Get meals that were recommended recently (for penalty)
        recent_meal_ids = self._get_recent_meal_ids(user, days=2)

        # Get user preferences
        liked_meal_ids = set(
            user.meal_preferences.filter(preference='like').values_list('meal__id', flat=True)
        )

        # Score all available meals
        scored_meals = []
        for meal in available_meals:
            if meal.embedding:  # Only score meals with embeddings
                score = self._score_meal(
                    meal=meal,
                    user=user,
                    liked_meal_ids=liked_meal_ids,
                    recent_meal_ids=recent_meal_ids
                )
                scored_meals.append((meal, score))

        # Sort by score
        scored_meals.sort(key=lambda x: x[1], reverse=True)

        # Select diverse meals for each time period
        recommendations = {
            "morning": self._select_for_time_period(
                scored_meals, "morning", num_recommendations_per_period
            ),
            "afternoon": self._select_for_time_period(
                scored_meals, "afternoon", num_recommendations_per_period
            ),
            "evening": self._select_for_time_period(
                scored_meals, "evening", num_recommendations_per_period
            )
        }

        return recommendations

    def _get_eligible_meals(self, user, exclude_meal_ids=None):
        """Get meals that match user's constraints."""
        queryset = Meal.objects.filter(
            available=True,
            city=user.city
        )

        # Budget filter - show meals within 30% over budget (allows discovery)
        if user.average_meal_budget:
            max_price = float(user.average_meal_budget) * 1.3
            queryset = queryset.filter(price__lte=max_price)

        # Exclude meals with restricted health conditions
        user_health_conditions = user.health_conditions.all()
        if user_health_conditions.exists():
            queryset = queryset.exclude(
                restricted_health_conditions__in=user_health_conditions
            )

        # Exclude meals with user's allergies
        user_allergies = user.allergies.all()
        if user_allergies.exists():
            queryset = queryset.exclude(
                restricted_allergies__in=user_allergies
            )

        # Exclude hated meals
        hated_meals = list(user.meal_preferences.filter(preference='hate').values_list('meal__id', flat=True))
        if hated_meals:
            queryset = queryset.exclude(id__in=hated_meals)

        # Exclude specific meals if provided
        if exclude_meal_ids:
            queryset = queryset.exclude(id__in=exclude_meal_ids)

        # Prefetch related data for efficiency
        queryset = queryset.prefetch_related(
            'fitness_goals',
            'cuisine',
            'meal_preferences',
        ).select_related('restaurant', 'city')

        return list(queryset[:150])  # Limit to avoid performance issues

    def _get_recent_meal_ids(self, user, days=2):
        """Get meal IDs recommended in the last N days."""
        cutoff_date = user.get_local_time().date() - timedelta(days=days)
        return set(
            user.recommendations.filter(
                day__gte=cutoff_date
            ).values_list('meal__id', flat=True)
        )

    def _generate_meal_embeddings(self, meals: List[Meal]):
        """Generate embeddings for meals that don't have them."""
        if not meals:
            return

        # Prepare text for embedding
        texts = []
        for meal in meals:
            text = self._create_meal_text(meal)
            texts.append(text)

        try:
            # Batch embedding generation (more efficient)
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )

            # Update meals with embeddings
            for i, meal in enumerate(meals):
                embedding = response.data[i].embedding
                meal.embedding = embedding
                meal.embedding_generated_at = timezone.now()
                meal.save(update_fields=['embedding', 'embedding_generated_at'])

            logger.info(f"Generated embeddings for {len(meals)} meals")

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")

    def _create_meal_text(self, meal: Meal) -> str:
        """Create text representation of meal for embedding."""
        parts = [
            f"Meal: {meal.name}",
            f"Description: {meal.description}",
            f"Price: {meal.price} {meal.city.currency.code if meal.city and meal.city.currency else ''}",
        ]

        # Add cuisines
        cuisines = list(meal.cuisine.values_list('name', flat=True))
        if cuisines:
            parts.append(f"Cuisine: {', '.join(cuisines)}")

        # Add fitness goals
        fitness_goals = list(meal.fitness_goals.values_list('name', flat=True))
        if fitness_goals:
            parts.append(f"Fitness goals: {', '.join(fitness_goals)}")

        # Add nutritional info if available
        if meal.calories:
            parts.append(f"Calories: {meal.calories}")
        if meal.protein:
            parts.append(f"Protein: {meal.protein}g")
        if meal.carbs:
            parts.append(f"Carbs: {meal.carbs}g")
        if meal.fats:
            parts.append(f"Fats: {meal.fats}g")

        # Add time of day
        if meal.times_of_day:
            parts.append(f"Best for: {', '.join(meal.times_of_day)}")

        return " | ".join(parts)

    def _score_meal(
        self,
        meal: Meal,
        user,
        liked_meal_ids: set,
        recent_meal_ids: set
    ) -> float:
        """
        Calculate comprehensive score for a meal.

        Factors:
        - User preference alignment (liked meals)
        - Fitness goal match
        - Cuisine preference match
        - Budget fit
        - Nutritional value
        - Recency penalty
        - Time-of-day appropriateness
        """
        score = 0.0

        # 1. Liked meal bonus (strong signal)
        if meal.id in liked_meal_ids:
            score += 30.0

        # 2. Fitness goal match
        if user.fitness_goals:
            meal_fitness_goals = set(meal.fitness_goals.values_list('id', flat=True))
            if user.fitness_goals.id in meal_fitness_goals:
                score += 20.0

        # 3. Cuisine preference match
        user_preferred_cuisines = set(user.preferred_cuisine.values_list('id', flat=True))
        if user_preferred_cuisines:
            meal_cuisines = set(meal.cuisine.values_list('id', flat=True))
            if meal_cuisines & user_preferred_cuisines:  # Intersection
                score += 15.0

        # 4. Budget optimization - prefer meals near budget
        if user.average_meal_budget:
            budget = float(user.average_meal_budget)
            price = float(meal.price)
            price_ratio = price / budget

            # Optimal: 80-100% of budget
            if 0.8 <= price_ratio <= 1.0:
                score += 10.0
            # Good: 60-80% or 100-120% of budget
            elif 0.6 <= price_ratio <= 1.2:
                score += 5.0
            # Penalty for much cheaper or more expensive
            else:
                score -= abs(price_ratio - 0.9) * 5

        # 5. Nutritional value (protein-to-calorie ratio for muscle gain, etc.)
        if meal.calories and meal.protein and user.fitness_goals:
            if user.fitness_goals.name == 'muscle_gain' and meal.protein:
                protein_ratio = float(meal.protein) / (float(meal.calories) / 100)
                score += protein_ratio * 2  # Higher protein = better for muscle gain
            elif user.fitness_goals.name == 'weight_loss' and meal.calories:
                # Prefer lower calorie meals for weight loss
                if meal.calories < 500:
                    score += 10.0
                elif meal.calories < 700:
                    score += 5.0

        # 6. Recency penalty (avoid meals from yesterday)
        if meal.id in recent_meal_ids:
            score -= 25.0  # Strong penalty to ensure variety

        # 7. Add small random factor for exploration (avoid always showing same meals)
        import random
        score += random.uniform(0, 3)

        return score

    def _select_for_time_period(
        self,
        scored_meals: List[Tuple[Meal, float]],
        time_period: str,
        num_recommendations: int
    ) -> List[int]:
        """
        Select meals appropriate for the time period, ensuring diversity.
        """
        # Filter meals appropriate for this time period
        period_appropriate = []
        period_flexible = []

        for meal, score in scored_meals:
            if not meal.times_of_day:  # No time restriction
                period_flexible.append((meal, score))
            elif time_period in meal.times_of_day:
                period_appropriate.append((meal, score))
            else:
                # Slight penalty but still consider
                period_flexible.append((meal, score * 0.8))

        # Prioritize period-appropriate meals, then flexible ones
        candidates = period_appropriate + period_flexible

        # Select diverse meals (avoid similar cuisines, names)
        selected = []
        selected_cuisines = set()
        selected_keywords = set()

        for meal, score in candidates:
            if len(selected) >= num_recommendations:
                break

            # Check diversity
            meal_cuisines = set(meal.cuisine.values_list('name', flat=True))
            meal_keywords = set(meal.name.lower().split()[:2])  # First 2 words

            # If we've selected many meals already, ensure diversity
            if len(selected) > 0:
                # Avoid too many meals with same cuisine
                cuisine_overlap = bool(meal_cuisines & selected_cuisines)
                keyword_overlap = bool(meal_keywords & selected_keywords)

                # Skip if too similar to already selected (only if we have enough candidates)
                if len(candidates) > num_recommendations * 2:
                    if cuisine_overlap and keyword_overlap:
                        continue

            selected.append(meal.id)
            selected_cuisines.update(meal_cuisines)
            selected_keywords.update(meal_keywords)

        # If we don't have enough, just take top scored regardless of diversity
        if len(selected) < num_recommendations:
            remaining = num_recommendations - len(selected)
            for meal, score in candidates:
                if meal.id not in selected:
                    selected.append(meal.id)
                    remaining -= 1
                    if remaining == 0:
                        break

        return selected[:num_recommendations]
