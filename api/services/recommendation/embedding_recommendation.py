# services/embedding_recommendation.py
from typing import List, Dict, Optional, Tuple, Set
from openai import OpenAI
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
from api.models.meal import Meal
from api.models.meal_preference import MealPreference
from api.models.review import Review
import logging
import math
import random

logger = logging.getLogger(__name__)


class EmbeddingRecommendationService:
    """
    Cost-optimized embedding-based meal recommendation system.

    Key features:
    - Uses cached embeddings (95%+ cost reduction vs LLM)
    - Multi-factor scoring: preferences, nutrition, budget, time-of-day
    - Collaborative filtering for social proof
    - Review sentiment analysis
    - Avoids recent meals for variety
    - Ensures diversity in recommendations
    - Optimized for conversion
    """

    # Scoring weight constants - tune these to adjust recommendation behavior
    WEIGHT_ORDERED_BEFORE = 35.0
    WEIGHT_SEMANTIC_SIMILARITY = 20.0
    WEIGHT_LIKED = 30.0
    WEIGHT_REVIEWED_POSITIVELY = 25.0
    WEIGHT_REVIEWED_NEGATIVELY = -40.0
    WEIGHT_FITNESS_GOAL = 20.0
    WEIGHT_CUISINE_MATCH = 15.0
    WEIGHT_BUDGET_OPTIMAL = 10.0
    WEIGHT_BUDGET_GOOD = 5.0
    WEIGHT_TIME_OF_DAY = 8.0
    WEIGHT_COLLABORATIVE_FILTERING = 18.0
    WEIGHT_EXPLORATION_MAX = 8.0

    # Nutritional scoring weights
    WEIGHT_NUTRITION_MAX = 10.0

    # Popularity scoring
    WEIGHT_POPULARITY_MAX = 10.0

    # Recency penalty weights
    PENALTY_RECENT_MAX = 30.0
    PENALTY_FREQUENCY_MAX = 15.0

    # Query limits
    MAX_CANDIDATE_MEALS = 150
    COLLABORATIVE_SIMILAR_USERS = 10

    # Fitness goal slugs (should match database values)
    FITNESS_GOAL_MUSCLE_GAIN = 'muscle_gain'
    FITNESS_GOAL_WEIGHT_LOSS = 'weight_loss'
    FITNESS_GOAL_MAINTENANCE = 'maintenance'

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
        # Get eligible meals with optimized annotations
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
        recent_meal_history = self._get_recent_meal_history(user, lookback_days=14)

        # Get long-term frequency for diversity (last 30 days)
        meal_frequency = self._get_meal_frequency(user, lookback_days=30)

        # Get user preferences
        liked_meal_ids = set(
            user.meal_preferences.filter(preference='like').values_list('meal__id', flat=True)
        )

        # Generate user preference embedding for semantic similarity
        user_embedding = self._generate_user_preference_embedding(user, available_meals, liked_meal_ids)

        # Get order history for stronger signal - OPTIMIZED to single query
        ordered_meal_ids = self._get_user_ordered_meals(user)

        # Get user's reviewed meals with sentiment
        user_reviews_by_meal = self._get_user_reviews_by_meal(user)

        # Get collaborative filtering recommendations
        collaborative_meal_ids = self._get_collaborative_filtering_meals(user, liked_meal_ids)

        # Pre-compute user's preferred cuisines to avoid N+1 queries
        user_preferred_cuisine_ids = set(
            user.preferred_cuisine.values_list('id', flat=True)
        )

        # Pre-compute meal-to-cuisines and meal-to-fitness-goals maps to avoid N+1 queries
        meal_cuisines_map = {}
        meal_fitness_goals_map = {}
        for meal in available_meals:
            meal_cuisines_map[meal.id] = set(c.id for c in meal.cuisine.all())
            meal_fitness_goals_map[meal.id] = set(g.id for g in meal.fitness_goals.all())

        # Score all available meals
        scored_meals = []
        for meal in available_meals:
            if not meal.embedding:
                logger.warning(f"Meal {meal.id} ({meal.name}) has no embedding, skipping")
                continue

            score = self._score_meal(
                meal=meal,
                user=user,
                liked_meal_ids=liked_meal_ids,
                ordered_meal_ids=ordered_meal_ids,
                user_reviews_by_meal=user_reviews_by_meal,
                collaborative_meal_ids=collaborative_meal_ids,
                recent_meal_history=recent_meal_history,
                meal_frequency=meal_frequency,
                user_embedding=user_embedding,
                user_preferred_cuisine_ids=user_preferred_cuisine_ids,
                meal_cuisines_map=meal_cuisines_map,
                meal_fitness_goals_map=meal_fitness_goals_map
            )
            scored_meals.append((meal, score))

        # Sort by score
        scored_meals.sort(key=lambda x: x[1], reverse=True)

        # Select diverse meals for each time period
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
        """Get meals that match user's constraints with optimized queries."""
        from datetime import datetime

        queryset = Meal.objects.filter(
            available=True,
            city=user.city,
            restaurant__inactive=False  # Exclude meals from inactive restaurants
        ).select_related('restaurant')  # Optimize restaurant queries

        # Stock filter - exclude meals with zero stock
        # Only apply if meal has stock tracking enabled (daily_stock_limit is set)
        queryset = queryset.filter(
            Q(daily_stock_limit__isnull=True) |  # Unlimited stock
            Q(remaining_stock__isnull=True) |     # Stock not initialized
            Q(remaining_stock__gt=0)               # Has stock remaining
        )

        # Time-based filtering - only include meals available at current time
        current_time = user.get_local_time().time()
        current_day = user.get_local_time().strftime('%A').lower()

        # Filter by restaurant operating hours and days
        queryset = queryset.filter(
            Q(restaurant__available_days=[]) |  # Restaurant open all days
            Q(restaurant__available_days__contains=[current_day])  # Restaurant open today
        ).filter(
            restaurant__open_time__lte=current_time,
            restaurant__close_time__gte=current_time
        )

        # Filter by meal availability times
        queryset = queryset.filter(
            Q(available_from_time__isnull=True) | Q(available_from_time__lte=current_time)
        ).filter(
            Q(available_to_time__isnull=True) | Q(available_to_time__gte=current_time)
        )

        # Budget filter - show meals within 20% over budget (more likely to convert)
        # FIXED: Add validation for budget
        if user.average_meal_budget and user.average_meal_budget > 0:
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

        # FIXED: Add annotations for popularity to avoid N+1 queries
        queryset = queryset.annotate(
            total_order_count=Count('orders', distinct=True),
            total_like_count=Count(
                'meal_preferences',
                filter=Q(meal_preferences__preference='like'),
                distinct=True
            )
        )

        # Prefetch related data for efficiency
        # REMOVED: orders__reviews - we only need user's reviews, not all reviews
        queryset = queryset.prefetch_related(
            'fitness_goals',
            'cuisine',
            'meal_preferences',
            'orders'
        ).select_related('restaurant', 'city', 'city__currency')

        return list(queryset[:self.MAX_CANDIDATE_MEALS])

    def _get_user_ordered_meals(self, user) -> Set[int]:
        """Get set of meal IDs the user has ordered. Single optimized query."""
        return set(
            user.orders.values_list('meal__id', flat=True).distinct()
        )

    def _get_user_reviews_by_meal(self, user) -> Dict[int, str]:
        """
        Get user's reviews organized by meal ID with sentiment.
        Returns: {meal_id: sentiment} for meals user has reviewed.
        """
        # Get all user's reviews with meal info through order
        reviews = Review.objects.filter(
            user=user
        ).select_related('order__meal').values('order__meal__id', 'sentiment')

        # Build map: meal_id -> sentiment (most recent if multiple)
        reviews_by_meal = {}
        for review in reviews:
            meal_id = review['order__meal__id']
            sentiment = review['sentiment']
            # Keep the first (most recent) sentiment for each meal
            if meal_id not in reviews_by_meal:
                reviews_by_meal[meal_id] = sentiment

        return reviews_by_meal

    def _get_collaborative_filtering_meals(
        self,
        user,
        user_liked_meal_ids: Set[int]
    ) -> Set[int]:
        """
        Collaborative filtering: Find meals liked by users with similar taste.
        Returns set of meal IDs recommended by similar users.
        """
        if not user_liked_meal_ids:
            return set()

        try:
            # Find users who liked the same meals as this user
            similar_users = MealPreference.objects.filter(
                meal_id__in=user_liked_meal_ids,
                preference='like'
            ).exclude(
                user=user
            ).values('user').annotate(
                overlap_count=Count('id')
            ).order_by('-overlap_count')[:self.COLLABORATIVE_SIMILAR_USERS]

            similar_user_ids = [item['user'] for item in similar_users]

            if not similar_user_ids:
                return set()

            # Get meals these similar users liked that current user hasn't tried
            collaborative_meals = MealPreference.objects.filter(
                user_id__in=similar_user_ids,
                preference='like'
            ).exclude(
                meal_id__in=user_liked_meal_ids
            ).values_list('meal_id', flat=True).distinct()

            return set(collaborative_meals)

        except Exception as e:
            logger.error(f"Error in collaborative filtering: {e}")
            return set()

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
        liked_meal_ids: Set[int],
        ordered_meal_ids: Set[int],
        user_reviews_by_meal: Dict[int, str],
        collaborative_meal_ids: Set[int],
        recent_meal_history: Dict[int, int],
        meal_frequency: Dict[int, int],
        user_embedding: Optional[List[float]] = None,
        user_preferred_cuisine_ids: Optional[Set[int]] = None,
        meal_cuisines_map: Optional[Dict[int, Set[int]]] = None,
        meal_fitness_goals_map: Optional[Dict[int, Set[int]]] = None
    ) -> float:
        """
        Calculate comprehensive score for a meal.
        Refactored into smaller component functions for maintainability.
        """
        score = 0.0

        # User history signals
        score += self._score_user_history(
            meal, liked_meal_ids, ordered_meal_ids, user_reviews_by_meal
        )

        # Semantic similarity
        score += self._score_semantic_similarity(meal, user_embedding)

        # Collaborative filtering
        score += self._score_collaborative_filtering(meal, collaborative_meal_ids)

        # User preferences alignment
        score += self._score_preferences(
            meal, user, user_preferred_cuisine_ids,
            meal_cuisines_map, meal_fitness_goals_map
        )

        # Budget fit
        score += self._score_budget(meal, user)

        # Nutritional value
        score += self._score_nutrition(meal, user)

        # Time of day appropriateness
        score += self._score_time_of_day(meal, user)

        # Popularity (social proof) - FIXED: Use annotated fields
        score += self._score_popularity(meal)

        # Recency and frequency penalties
        score -= self._calculate_recency_penalty(meal, recent_meal_history)
        score -= self._calculate_frequency_penalty(meal, meal_frequency)

        # Exploration factor
        score += self._score_exploration()

        return score

    def _score_user_history(
        self,
        meal: Meal,
        liked_meal_ids: Set[int],
        ordered_meal_ids: Set[int],
        user_reviews_by_meal: Dict[int, str]
    ) -> float:
        """Score based on user's historical interactions with this meal."""
        score = 0.0

        # Previously ordered meal bonus (strongest signal)
        if meal.id in ordered_meal_ids:
            score += self.WEIGHT_ORDERED_BEFORE

        # Liked meal bonus (strong signal)
        if meal.id in liked_meal_ids:
            score += self.WEIGHT_LIKED

        # Review sentiment (very strong signal)
        if meal.id in user_reviews_by_meal:
            sentiment = user_reviews_by_meal[meal.id]
            if sentiment == 'like':
                score += self.WEIGHT_REVIEWED_POSITIVELY
            elif sentiment == 'hate':
                score += self.WEIGHT_REVIEWED_NEGATIVELY  # This is negative

        return score

    def _score_semantic_similarity(
        self,
        meal: Meal,
        user_embedding: Optional[List[float]]
    ) -> float:
        """Score based on semantic similarity between user preferences and meal."""
        if not user_embedding or not meal.embedding:
            return 0.0

        similarity = self._calculate_cosine_similarity(user_embedding, meal.embedding)
        # Similarity ranges from -1 to 1, we scale to 0-WEIGHT_SEMANTIC_SIMILARITY points
        return max(0, similarity * self.WEIGHT_SEMANTIC_SIMILARITY)

    def _score_collaborative_filtering(
        self,
        meal: Meal,
        collaborative_meal_ids: Set[int]
    ) -> float:
        """Score based on collaborative filtering (users like you also liked)."""
        if meal.id in collaborative_meal_ids:
            return self.WEIGHT_COLLABORATIVE_FILTERING
        return 0.0

    def _score_preferences(
        self,
        meal: Meal,
        user,
        user_preferred_cuisine_ids: Optional[Set[int]],
        meal_cuisines_map: Optional[Dict[int, Set[int]]],
        meal_fitness_goals_map: Optional[Dict[int, Set[int]]]
    ) -> float:
        """Score based on user's stated preferences (fitness goals, cuisines)."""
        score = 0.0

        # Fitness goal match
        if user.fitness_goals and meal_fitness_goals_map:
            meal_fitness_goals = meal_fitness_goals_map.get(meal.id, set())
            if user.fitness_goals.id in meal_fitness_goals:
                score += self.WEIGHT_FITNESS_GOAL

        # Cuisine preference match
        if user_preferred_cuisine_ids and meal_cuisines_map:
            meal_cuisines = meal_cuisines_map.get(meal.id, set())
            if meal_cuisines & user_preferred_cuisine_ids:  # Intersection
                score += self.WEIGHT_CUISINE_MATCH

        return score

    def _score_budget(self, meal: Meal, user) -> float:
        """Score based on how well meal price fits user's budget."""
        if not user.average_meal_budget or user.average_meal_budget <= 0:
            return 0.0

        budget = float(user.average_meal_budget)
        price = float(meal.price)

        # Avoid division by zero
        if budget == 0:
            return 0.0

        price_ratio = price / budget

        # Optimal: 80-100% of budget
        if 0.8 <= price_ratio <= 1.0:
            return self.WEIGHT_BUDGET_OPTIMAL
        # Good: 60-80% or 100-120% of budget
        elif 0.6 <= price_ratio <= 1.2:
            return self.WEIGHT_BUDGET_GOOD
        # Penalty for much cheaper or more expensive
        else:
            return -abs(price_ratio - 0.9) * 5

    def _score_nutrition(self, meal: Meal, user) -> float:
        """Score based on nutritional value aligned with fitness goals."""
        if not meal.calories or not user.fitness_goals:
            return 0.0

        score = 0.0
        fitness_goal_name = user.fitness_goals.name.lower()

        # FIXED: Use safer string comparisons with lower()
        if self.FITNESS_GOAL_MUSCLE_GAIN in fitness_goal_name and meal.protein:
            # Avoid division by zero
            if meal.calories > 0:
                protein_ratio = float(meal.protein) / (float(meal.calories) / 100)
                score += min(self.WEIGHT_NUTRITION_MAX, protein_ratio * 2)

        elif self.FITNESS_GOAL_WEIGHT_LOSS in fitness_goal_name:
            # Prefer lower calorie meals for weight loss
            if meal.calories < 500:
                score += self.WEIGHT_NUTRITION_MAX
            elif meal.calories < 700:
                score += self.WEIGHT_NUTRITION_MAX / 2

        elif self.FITNESS_GOAL_MAINTENANCE in fitness_goal_name:
            # For maintenance, prefer balanced macros
            if meal.protein and meal.carbs and meal.fats:
                total_cals = float(meal.calories)

                # Avoid division by zero
                if total_cals > 0:
                    protein_cals = float(meal.protein) * 4
                    carb_cals = float(meal.carbs) * 4
                    fat_cals = float(meal.fats) * 9

                    protein_pct = protein_cals / total_cals
                    carb_pct = carb_cals / total_cals
                    fat_pct = fat_cals / total_cals

                    # Ideal: 40% carbs, 30% protein, 30% fats
                    balance_score = self.WEIGHT_NUTRITION_MAX - (
                        abs(carb_pct - 0.40) +
                        abs(protein_pct - 0.30) +
                        abs(fat_pct - 0.30)
                    ) * 20
                    score += max(0, balance_score)

        return score

    def _score_time_of_day(self, meal: Meal, user) -> float:
        """Score based on time-of-day appropriateness."""
        current_period = user.get_time_period()
        if meal.times_of_day and current_period in meal.times_of_day:
            return self.WEIGHT_TIME_OF_DAY
        return 0.0

    def _score_popularity(self, meal: Meal) -> float:
        """
        Score based on social proof (popularity from other users).
        FIXED: Use annotated fields instead of .count() to avoid N+1 queries.
        """
        try:
            # Use the annotated fields from queryset
            order_count = getattr(meal, 'total_order_count', 0)
            like_count = getattr(meal, 'total_like_count', 0)

            popularity = order_count * 2 + like_count  # Orders weighted more

            # Scale to max WEIGHT_POPULARITY_MAX points (diminishing returns)
            popularity_score = min(
                self.WEIGHT_POPULARITY_MAX,
                math.log(popularity + 1) * 2
            )
            return popularity_score
        except Exception as e:
            logger.warning(f"Error calculating popularity for meal {meal.id}: {e}")
            return 0.0

    def _calculate_recency_penalty(
        self,
        meal: Meal,
        recent_meal_history: Dict[int, int]
    ) -> float:
        """Calculate penalty based on how recently the meal was recommended."""
        if meal.id not in recent_meal_history:
            return 0.0

        days_ago = recent_meal_history[meal.id]

        # Aggressive decay curve for immediate diversity
        if days_ago <= 3:
            # Days 1-3: Very strong penalty to prevent immediate repetition
            return self.PENALTY_RECENT_MAX - (days_ago * 3)
        elif days_ago <= 7:
            # Days 4-7: Strong penalty
            return 21.0 - ((days_ago - 3) * 3)
        elif days_ago <= 10:
            # Days 8-10: Medium penalty
            return 9.0 - ((days_ago - 7) * 2)
        else:
            # Days 11-14: Light penalty (fading out)
            return max(0, 3.0 - ((days_ago - 10) * 0.75))

    def _calculate_frequency_penalty(
        self,
        meal: Meal,
        meal_frequency: Dict[int, int]
    ) -> float:
        """Calculate penalty based on how frequently meal was recommended."""
        if meal.id not in meal_frequency:
            return 0.0

        frequency = meal_frequency[meal.id]

        # Penalty increases with frequency
        if frequency >= 5:
            return self.PENALTY_FREQUENCY_MAX
        elif frequency == 4:
            return 10.0
        elif frequency == 3:
            return 7.0
        elif frequency == 2:
            return 4.0
        elif frequency == 1:
            return 2.0

        return 0.0

    def _score_exploration(self) -> float:
        """Add random exploration factor for discovery."""
        return random.uniform(0, self.WEIGHT_EXPLORATION_MAX)

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

        # Pre-compute cuisine names for all candidates to avoid N+1 queries
        meal_cuisines_map = {}
        for meal, score in candidates:
            cuisine_names = [c.name for c in meal.cuisine.all()]
            meal_cuisines_map[meal.id] = set(cuisine_names)

        for meal, score in candidates:
            if len(selected) >= num_recommendations:
                break

            # Check diversity
            meal_cuisines = meal_cuisines_map[meal.id]
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
