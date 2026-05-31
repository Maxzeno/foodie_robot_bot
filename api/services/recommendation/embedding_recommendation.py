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

        # Get meals that were recommended recently (for decay-based penalty)
        # Returns dict: {meal_id: days_ago} for penalty calculation
        recent_meal_history = self._get_recent_meal_history(user, lookback_days=14)

        # Get long-term frequency for diversity (last 30 days)
        meal_frequency = self._get_meal_frequency(user, lookback_days=30)

        # Get user preferences
        liked_meal_ids = set(
            user.meal_preferences.filter(preference='like').values_list('meal__id', flat=True)
        )

        # Generate user preference embedding for semantic similarity
        user_embedding = self._generate_user_preference_embedding(user, available_meals, liked_meal_ids)

        # Get order history for stronger signal
        ordered_meal_ids = set(
            user.orders.values_list('meal__id', flat=True).distinct()
        )

        # Score all available meals
        scored_meals = []
        for meal in available_meals:
            if meal.embedding:  # Only score meals with embeddings
                score = self._score_meal(
                    meal=meal,
                    user=user,
                    liked_meal_ids=liked_meal_ids,
                    ordered_meal_ids=ordered_meal_ids,
                    recent_meal_history=recent_meal_history,
                    meal_frequency=meal_frequency,
                    user_embedding=user_embedding
                )
                scored_meals.append((meal, score))

        # Sort by score
        scored_meals.sort(key=lambda x: x[1], reverse=True)

        # Select diverse meals for each time period
        # Track selected meals to prevent duplicates across periods
        already_selected_ids = set()

        morning_meals = self._select_for_time_period(
            scored_meals, "morning", num_recommendations_per_period, already_selected_ids
        )
        already_selected_ids.update(morning_meals)

        afternoon_meals = self._select_for_time_period(
            scored_meals, "afternoon", num_recommendations_per_period, already_selected_ids
        )
        already_selected_ids.update(afternoon_meals)

        evening_meals = self._select_for_time_period(
            scored_meals, "evening", num_recommendations_per_period, already_selected_ids
        )

        recommendations = {
            "morning": morning_meals,
            "afternoon": afternoon_meals,
            "evening": evening_meals
        }

        return recommendations

    def _get_eligible_meals(self, user, exclude_meal_ids=None):
        """Get meals that match user's constraints."""
        queryset = Meal.objects.filter(
            available=True,
            city=user.city
        )

        # Budget filter - show meals within 20% over budget (more likely to convert)
        if user.average_meal_budget:
            max_price = float(user.average_meal_budget) * 1.2
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
            'orders',
            'reviews'
        ).select_related('restaurant', 'city', 'city__currency')

        return list(queryset[:150])  # Limit to avoid performance issues

    def _get_recent_meal_history(self, user, lookback_days=14) -> Dict[int, int]:
        """
        Get meals recommended in the last N days with timing info.
        Returns dict: {meal_id: days_ago} for decay-based penalty.
        Excludes today's recommendations.
        """
        today = user.get_local_time().date()
        cutoff_date = today - timedelta(days=lookback_days)

        recommendations = user.recommendations.filter(
            day__gte=cutoff_date,
            day__lt=today  # Exclude today
        ).values('meal__id', 'day')

        meal_history = {}
        for rec in recommendations:
            meal_id = rec['meal__id']
            days_ago = (today - rec['day']).days

            # Keep the most recent occurrence for each meal
            if meal_id not in meal_history or days_ago < meal_history[meal_id]:
                meal_history[meal_id] = days_ago

        return meal_history

    def _get_meal_frequency(self, user, lookback_days=30) -> Dict[int, int]:
        """
        Get how many times each meal was recommended in the last N days.
        Returns dict: {meal_id: frequency_count}
        """
        today = user.get_local_time().date()
        cutoff_date = today - timedelta(days=lookback_days)

        # Count recommendations per meal
        from django.db.models import Count
        frequency_data = user.recommendations.filter(
            day__gte=cutoff_date
        ).values('meal__id').annotate(
            count=Count('id')
        )

        return {item['meal__id']: item['count'] for item in frequency_data}

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
        ]

        # Add price with null-safe currency access
        if meal.city and meal.city.currency:
            parts.append(f"Price: {meal.price} {meal.city.currency.code}")
        else:
            parts.append(f"Price: {meal.price}")

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

    def _generate_user_preference_embedding(
        self,
        user,
        available_meals: List[Meal],
        liked_meal_ids: set
    ) -> Optional[List[float]]:
        """
        Generate an embedding representing user's preferences.
        Based on liked meals, fitness goals, and cuisine preferences.
        """
        # Build user preference text
        parts = []

        # Add fitness goal
        if user.fitness_goals:
            parts.append(f"Fitness goal: {user.fitness_goals.name}")

        # Add preferred cuisines
        preferred_cuisines = list(user.preferred_cuisine.values_list('name', flat=True))
        if preferred_cuisines:
            parts.append(f"Preferred cuisines: {', '.join(preferred_cuisines)}")

        # Add liked meal names/descriptions
        liked_meals = [m for m in available_meals if m.id in liked_meal_ids][:5]  # Top 5
        if liked_meals:
            liked_descriptions = [f"{m.name}: {m.description[:100]}" for m in liked_meals]
            parts.append(f"Liked meals: {' | '.join(liked_descriptions)}")

        if not parts:
            return None  # No preference data available

        user_text = " | ".join(parts)

        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=user_text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating user embedding: {e}")
            return None

    def _calculate_cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings."""
        if not embedding1 or not embedding2:
            return 0.0

        # Convert to ensure they're lists of floats
        vec1 = [float(x) for x in embedding1]
        vec2 = [float(x) for x in embedding2]

        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Calculate magnitudes
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Cosine similarity
        return dot_product / (magnitude1 * magnitude2)

    def _score_meal(
        self,
        meal: Meal,
        user,
        liked_meal_ids: set,
        ordered_meal_ids: set,
        recent_meal_history: Dict[int, int],
        meal_frequency: Dict[int, int],
        user_embedding: Optional[List[float]] = None
    ) -> float:
        """
        Calculate comprehensive score for a meal.

        Factors:
        - Order history (strongest signal)
        - Semantic similarity using embeddings
        - User preference alignment (liked meals)
        - Fitness goal match
        - Cuisine preference match
        - Budget fit
        - Nutritional value
        - Social proof (popularity)
        - Decay-based recency penalty (prevents immediate repetition)
        - Frequency penalty (encourages long-term diversity)
        - Time-of-day appropriateness
        - Exploration factor (randomness for discovery)
        """
        score = 0.0

        # 1. Previously ordered meal bonus (strongest signal)
        if meal.id in ordered_meal_ids:
            score += 35.0

        # 2. Semantic similarity bonus using embeddings
        if user_embedding and meal.embedding:
            similarity = self._calculate_cosine_similarity(user_embedding, meal.embedding)
            # Similarity ranges from -1 to 1, we scale to 0-20 points
            score += max(0, similarity * 20)

        # 3. Liked meal bonus (strong signal)
        if meal.id in liked_meal_ids:
            score += 30.0

        # 4. Fitness goal match
        if user.fitness_goals:
            meal_fitness_goals = set(meal.fitness_goals.values_list('id', flat=True))
            if user.fitness_goals.id in meal_fitness_goals:
                score += 20.0

        # 5. Cuisine preference match
        user_preferred_cuisines = set(user.preferred_cuisine.values_list('id', flat=True))
        if user_preferred_cuisines:
            meal_cuisines = set(meal.cuisine.values_list('id', flat=True))
            if meal_cuisines & user_preferred_cuisines:  # Intersection
                score += 15.0

        # 6. Budget optimization - prefer meals near budget
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

        # 7. Nutritional value based on fitness goals
        if meal.calories and user.fitness_goals:
            if user.fitness_goals.name == 'muscle_gain' and meal.protein:
                protein_ratio = float(meal.protein) / (float(meal.calories) / 100)
                score += protein_ratio * 2  # Higher protein = better for muscle gain
            elif user.fitness_goals.name == 'weight_loss' and meal.calories:
                # Prefer lower calorie meals for weight loss
                if meal.calories < 500:
                    score += 10.0
                elif meal.calories < 700:
                    score += 5.0
            elif user.fitness_goals.name == 'maintenance' and meal.protein and meal.carbs and meal.fats:
                # For maintenance, prefer balanced macros (40/30/30 carbs/protein/fats)
                total_cals = float(meal.calories)
                protein_cals = float(meal.protein) * 4
                carb_cals = float(meal.carbs) * 4
                fat_cals = float(meal.fats) * 9

                protein_pct = protein_cals / total_cals if total_cals > 0 else 0
                carb_pct = carb_cals / total_cals if total_cals > 0 else 0
                fat_pct = fat_cals / total_cals if total_cals > 0 else 0

                # Ideal: 40% carbs, 30% protein, 30% fats
                balance_score = 10 - (
                    abs(carb_pct - 0.40) +
                    abs(protein_pct - 0.30) +
                    abs(fat_pct - 0.30)
                ) * 20
                score += max(0, balance_score)

        # 8. Time-of-day appropriateness bonus
        current_period = user.get_time_period()
        if meal.times_of_day and current_period in meal.times_of_day:
            score += 8.0

        # 9. Social proof - popularity from other users (use prefetched data)
        # Count orders and likes from meal_preferences
        try:
            order_count = meal.orders.count()
            like_count = meal.meal_preferences.filter(preference='like').count()
            popularity = order_count * 2 + like_count  # Orders weighted more

            # Scale to max 10 points (diminishing returns)
            import math
            popularity_score = min(10, math.log(popularity + 1) * 2)
            score += popularity_score
        except Exception:
            pass  # Skip if data not available

        # 10. Decay-based recency penalty (graduated based on how recently recommended)
        if meal.id in recent_meal_history:
            days_ago = recent_meal_history[meal.id]

            # Aggressive decay curve for immediate diversity
            if days_ago <= 3:
                # Days 1-3: Very strong penalty to prevent immediate repetition
                penalty = 30.0 - (days_ago * 3)  # Day 1: -27, Day 2: -24, Day 3: -21
            elif days_ago <= 7:
                # Days 4-7: Strong penalty
                penalty = 21.0 - ((days_ago - 3) * 3)  # Day 4: -18, ..., Day 7: -9
            elif days_ago <= 10:
                # Days 8-10: Medium penalty
                penalty = 9.0 - ((days_ago - 7) * 2)  # Day 8: -7, Day 9: -5, Day 10: -3
            else:
                # Days 11-14: Light penalty (fading out)
                penalty = max(0, 3.0 - ((days_ago - 10) * 0.75))  # Gradual fade to 0

            score -= penalty

        # 11. Long-term frequency penalty (discourage over-recommendation)
        if meal.id in meal_frequency:
            frequency = meal_frequency[meal.id]
            # Penalty increases with frequency: 1x: -2, 2x: -4, 3x: -7, 4x: -10, 5+x: -15
            if frequency >= 5:
                score -= 15.0
            elif frequency == 4:
                score -= 10.0
            elif frequency == 3:
                score -= 7.0
            elif frequency == 2:
                score -= 4.0
            elif frequency == 1:
                score -= 2.0

        # 12. Exploration factor for discovery (increased randomness)
        import random
        score += random.uniform(0, 8)  # Increased from 0-3 to 0-8 for more variety

        return score

    def _select_for_time_period(
        self,
        scored_meals: List[Tuple[Meal, float]],
        time_period: str,
        num_recommendations: int,
        already_selected_ids: set = None
    ) -> List[int]:
        """
        Select meals appropriate for the time period, ensuring diversity.
        Excludes meals already selected for other time periods.
        """
        if already_selected_ids is None:
            already_selected_ids = set()

        # Filter meals appropriate for this time period
        period_appropriate = []
        period_flexible = []

        for meal, score in scored_meals:
            # Skip meals already selected for another time period
            if meal.id in already_selected_ids:
                continue

            if not meal.times_of_day:  # No time restriction
                period_flexible.append((meal, score))
            elif time_period in meal.times_of_day:
                period_appropriate.append((meal, score))
            else:
                # Slight penalty but still consider
                period_flexible.append((meal, score * 0.8))

        # Prioritize period-appropriate meals, then flexible ones
        candidates = period_appropriate + period_flexible

        # Select diverse meals (avoid similar cuisines, names, restaurants)
        selected = []
        selected_cuisines = set()
        selected_keywords = set()
        selected_restaurants = {}  # restaurant_id -> count

        for meal, score in candidates:
            if len(selected) >= num_recommendations:
                break

            # Check diversity
            meal_cuisines = set(meal.cuisine.values_list('name', flat=True))
            meal_keywords = set(meal.name.lower().split()[:2])  # First 2 words
            restaurant_id = meal.restaurant.id if meal.restaurant else None

            # If we've selected many meals already, ensure diversity
            if len(selected) > 0:
                # Avoid too many meals with same cuisine
                cuisine_overlap = bool(meal_cuisines & selected_cuisines)
                keyword_overlap = bool(meal_keywords & selected_keywords)

                # Avoid too many meals from same restaurant (max 2 per period)
                if restaurant_id and selected_restaurants.get(restaurant_id, 0) >= 2:
                    if len(candidates) > num_recommendations * 1.5:
                        continue

                # Skip if too similar to already selected (only if we have enough candidates)
                if len(candidates) > num_recommendations * 2:
                    if cuisine_overlap and keyword_overlap:
                        continue

            selected.append(meal.id)
            selected_cuisines.update(meal_cuisines)
            selected_keywords.update(meal_keywords)
            if restaurant_id:
                selected_restaurants[restaurant_id] = selected_restaurants.get(restaurant_id, 0) + 1

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
