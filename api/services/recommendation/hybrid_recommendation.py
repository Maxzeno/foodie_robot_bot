# services/recommendation/hybrid_recommendation.py
"""
Hybrid Meal Recommendation Service - Balanced & Cost-Effective

This is the main recommendation service that combines:
1. Rule-based filtering (safety, availability) - KEEP from original
2. Semantic scoring via embeddings (personalization) - NEW
3. Decay-based diversity (smart repetition prevention) - IMPROVED

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: Hard Constraint Filtering (Availability)              │
│  - Hated meals                                                   │
│  - Availability, stock, restaurant status                       │
│  - Budget limits                                                 │
│  - Note: Allergies/health conditions removed for simplicity     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: Hybrid Scoring System                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ Taste Affinity  │  │ Explicit Signals │  │ Social Proof  │  │
│  │ (Embeddings)    │  │ (Orders/Likes)   │  │ (Popularity)  │  │
│  │     40%         │  │      35%         │  │     15%       │  │
│  └─────────────────┘  └──────────────────┘  └───────────────┘  │
│                    + Special Occasions (10%)                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Decay-Based Diversity                                 │
│  - Exponential decay for recency (soft, not hard cutoff)        │
│  - Semantic similarity penalty (via embeddings)                 │
│  - Cuisine variety within time periods                          │
└─────────────────────────────────────────────────────────────────┘

Cost Considerations:
- Embeddings are cached in DB (one-time cost ~$0.02 per 1000 meals)
- User profiles cached for 6 hours
- No per-request OpenAI calls for cached meals
"""

import logging
import random
import math
from typing import List, Dict, Optional, Set, Tuple
from datetime import timedelta
from collections import defaultdict
from django.db.models import Count, Q
from django.core.cache import cache

from api.models.meal import Meal
from api.models.meal_preference import MealPreference
from api.models.recommendation import Recommendation
from api.models.review import Review

logger = logging.getLogger(__name__)


class HybridMealRecommendationService:
    """
    Balanced recommendation service optimizing for:
    - User satisfaction (via semantic taste matching)
    - Diversity (via decay-based penalties, not hard blocks)
    - Cost efficiency (via aggressive caching)
    - Cold start handling (graceful degradation for new users)
    """

    # === SCORING WEIGHTS (Must sum to ~100 for interpretability) ===
    # These determine how much each factor influences the final score

    # Taste Affinity (from embeddings + profile)
    WEIGHT_TASTE_AFFINITY = 40.0

    # Explicit Signals (user's actual behavior)
    WEIGHT_EXPLICIT_POSITIVE = 25.0    # Ordered/liked before
    WEIGHT_EXPLICIT_NEGATIVE = -35.0   # Hated/negatively reviewed

    # Social Proof
    WEIGHT_POPULARITY = 10.0           # Orders + likes from all users
    WEIGHT_COLLABORATIVE = 10.0        # Similar users liked this

    # Context
    WEIGHT_TIME_OF_DAY = 5.0           # Time-appropriate meals
    WEIGHT_SPECIAL_OCCASION = 15.0     # Date-based boosts
    WEIGHT_BUDGET_FIT = 5.0            # Price alignment

    # === DIVERSITY DECAY PARAMETERS ===
    # Controls how quickly recency penalty decays
    RECENCY_DECAY_RATE = 0.7          # Per-day decay factor (0.7 = 30% reduction per day)
    RECENCY_MAX_PENALTY = 25.0        # Maximum penalty for same-day recommendation
    RECENCY_LOOKBACK_DAYS = 5         # Only consider last N days

    # Semantic similarity penalty (for similar-but-different meals)
    SIMILARITY_PENALTY_THRESHOLD = 0.75  # Only penalize if similarity > this
    SIMILARITY_MAX_PENALTY = 15.0        # Maximum penalty for highly similar meals
    SIMILARITY_LOOKBACK_DAYS = 3         # Check similarity against last N days

    # Frequency penalty (ordered too many times recently)
    FREQUENCY_PENALTY_THRESHOLD = 3   # Start penalizing after N recommendations
    FREQUENCY_MAX_PENALTY = 20.0      # Maximum frequency penalty
    FREQUENCY_LOOKBACK_DAYS = 10      # Window for frequency count

    # === EXPLORATION ===
    EPSILON_NEW_USER = 0.25           # 25% random exploration for new users
    EPSILON_REGULAR_USER = 0.15       # 15% for users with some history
    EPSILON_ESTABLISHED_USER = 0.10   # 10% for users with lots of history

    # === COLD START ===
    MIN_INTERACTIONS_FOR_PERSONALIZATION = 3
    COLD_START_POPULARITY_BOOST = 20.0  # Extra weight on popularity for new users

    # === QUERY LIMITS ===
    MAX_CANDIDATE_MEALS = 150

    def __init__(self):
        """Initialize services lazily."""
        self._embedding_service = None
        self._taste_profile_service = None
        logger.info("HybridMealRecommendationService initialized")

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            from api.services.recommendation.meal_embedding import MealEmbeddingService
            self._embedding_service = MealEmbeddingService()
        return self._embedding_service

    @property
    def taste_profile_service(self):
        if self._taste_profile_service is None:
            from api.services.recommendation.user_taste_profile import UserTasteProfileService
            self._taste_profile_service = UserTasteProfileService(self.embedding_service)
        return self._taste_profile_service

    def get_recommendations(
        self,
        user,
        num_recommendations_per_period: int = 2,
        exclude_meal_ids: Optional[List[int]] = None,
        exploration_rate: Optional[float] = None
    ) -> Dict[str, List[int]]:
        """
        Get personalized meal recommendations for morning, afternoon, and evening.

        Args:
            user: User instance
            num_recommendations_per_period: Number of meals per time period
            exclude_meal_ids: Additional meal IDs to exclude
            exploration_rate: Override epsilon for exploration (0.0-1.0)

        Returns:
            Dict with keys 'morning', 'afternoon', 'evening', each containing meal IDs
        """
        logger.info(f"Getting hybrid recommendations for user {user.id}")

        # === LAYER 1: HARD CONSTRAINT FILTERING ===
        today_meal_ids = self._get_today_recommended_meals(user)
        all_exclusions = set(today_meal_ids)
        if exclude_meal_ids:
            all_exclusions.update(exclude_meal_ids)

        available_meals = self._get_eligible_meals(user, list(all_exclusions))
        logger.info(f"Eligible meals after filtering: {len(available_meals)}")

        if not available_meals:
            logger.warning("No eligible meals found")
            return {"morning": [], "afternoon": [], "evening": []}

        # === PREPARE SCORING CONTEXT ===
        # Build user taste profile (cached)
        user_profile = self.taste_profile_service.build_taste_profile(user)
        is_cold_start = user_profile is None

        # Pre-fetch embeddings for all candidate meals
        embeddings = self.embedding_service.get_embeddings_batch(available_meals)

        # Gather explicit signals
        user_data = self._gather_user_data(user)

        # Get recent recommendation history for diversity
        recent_history = self._get_recent_recommendation_history(user)

        # Special occasions
        special_occasion_boosts = self._get_special_occasion_boosts(user)

        # === LAYER 2: HYBRID SCORING ===
        scored_meals = []
        for meal in available_meals:
            score = self._score_meal(
                meal=meal,
                user=user,
                user_profile=user_profile,
                meal_embedding=embeddings.get(meal.id),
                user_data=user_data,
                recent_history=recent_history,
                special_occasion_boosts=special_occasion_boosts,
                is_cold_start=is_cold_start
            )
            scored_meals.append((meal, score))

        # Sort by score
        scored_meals.sort(key=lambda x: x[1], reverse=True)

        if scored_meals:
            logger.info(f"Top score: {scored_meals[0][1]:.2f} ({scored_meals[0][0].name})")

        # === LAYER 3: DIVERSITY-AWARE SELECTION ===
        already_selected_ids = set()
        recommendations = {}

        for period in ['morning', 'afternoon', 'evening']:
            period_meals = self._select_diverse_meals(
                scored_meals=scored_meals,
                time_period=period,
                num_recommendations=num_recommendations_per_period,
                already_selected=already_selected_ids,
                embeddings=embeddings,
                recent_history=recent_history
            )
            recommendations[period] = period_meals
            already_selected_ids.update(period_meals)

        # === EXPLORATION ===
        epsilon = self._get_exploration_rate(user, user_profile, exploration_rate)
        if epsilon > 0:
            recommendations = self._apply_exploration(
                recommendations, available_meals, epsilon
            )

        logger.info(f"Final recommendations: {sum(len(v) for v in recommendations.values())} meals")
        return recommendations

    # =========================================================================
    # LAYER 1: HARD CONSTRAINT FILTERING (Same as original - these work well)
    # =========================================================================

    def _get_today_recommended_meals(self, user) -> List[int]:
        """Get meal IDs already recommended to user today."""
        today = user.get_local_time().date()
        return list(
            Recommendation.objects.filter(
                user=user,
                day=today
            ).values_list('meal_id', flat=True).distinct()
        )

    def _get_eligible_meals(self, user, exclude_meal_ids: Optional[List[int]] = None) -> List[Meal]:
        """
        Apply hard constraints to filter eligible meals.
        Note: Allergies and health conditions filtering removed for simplicity.
        """
        queryset = Meal.objects.filter(
            available=True,
            city=user.city,
            restaurant__inactive=False
        ).select_related('restaurant', 'city', 'city__currency')

        # === SAFETY FILTERS ===
        # Note: Allergies and health conditions filtering removed for simplicity
        # These may be re-added as the product matures

        hated_meal_ids = list(
            user.meal_preferences.filter(preference='hate').values_list('meal_id', flat=True)
        )
        if hated_meal_ids:
            queryset = queryset.exclude(id__in=hated_meal_ids)

        # === AVAILABILITY FILTERS ===
        queryset = queryset.filter(
            Q(daily_stock_limit__isnull=True) |
            Q(remaining_stock__isnull=True) |
            Q(remaining_stock__gt=0)
        )

        current_time = user.get_local_time().time()
        current_day = user.get_local_time().strftime('%A').lower()

        queryset = queryset.filter(
            Q(restaurant__available_days=[]) |
            Q(restaurant__available_days__contains=[current_day])
        ).filter(
            restaurant__open_time__lte=current_time,
            restaurant__close_time__gte=current_time
        )

        queryset = queryset.filter(
            Q(available_from_time__isnull=True) | Q(available_from_time__lte=current_time)
        ).filter(
            Q(available_to_time__isnull=True) | Q(available_to_time__gte=current_time)
        )

        # Budget filter (soft - allow 20% over)
        if user.average_meal_budget and user.average_meal_budget > 0:
            max_price = float(user.average_meal_budget) * 1.2
            queryset = queryset.filter(price__lte=max_price)

        if exclude_meal_ids:
            queryset = queryset.exclude(id__in=exclude_meal_ids)

        # Annotate with popularity
        queryset = queryset.annotate(
            total_order_count=Count('orders', distinct=True),
            total_like_count=Count(
                'meal_preferences',
                filter=Q(meal_preferences__preference='like'),
                distinct=True
            )
        )

        queryset = queryset.prefetch_related(
            'fitness_goals', 'cuisine', 'meal_preferences'
        )

        return list(queryset[:self.MAX_CANDIDATE_MEALS])

    # =========================================================================
    # LAYER 2: HYBRID SCORING SYSTEM
    # =========================================================================

    def _score_meal(
        self,
        meal: Meal,
        user,
        user_profile: Optional[Dict],
        meal_embedding: Optional[List[float]],
        user_data: Dict,
        recent_history: Dict,
        special_occasion_boosts: Dict[int, float],
        is_cold_start: bool
    ) -> float:
        """
        Compute hybrid score for a meal.

        Combines multiple scoring components with careful balancing.
        """
        score = 0.0

        # === TASTE AFFINITY (Embeddings-based) ===
        if user_profile and meal_embedding:
            affinity = self.taste_profile_service.get_meal_affinity_score(
                user_profile, meal, meal_embedding
            )
            # Scale 0-100 affinity to weight
            score += (affinity / 100) * self.WEIGHT_TASTE_AFFINITY
        elif is_cold_start:
            # For cold start, give neutral affinity score
            score += 0.5 * self.WEIGHT_TASTE_AFFINITY

        # === EXPLICIT SIGNALS ===
        score += self._score_explicit_signals(meal, user_data)

        # === SOCIAL PROOF ===
        popularity_score = self._score_popularity(meal, is_cold_start)
        score += popularity_score

        if meal.id in user_data['collaborative_meal_ids']:
            score += self.WEIGHT_COLLABORATIVE

        # === CONTEXT ===
        score += self._score_time_of_day(meal, user)
        score += self._score_budget_fit(meal, user)

        # === SPECIAL OCCASIONS ===
        if meal.id in special_occasion_boosts:
            score += special_occasion_boosts[meal.id]

        # === DIVERSITY PENALTIES (Decay-based) ===
        score -= self._calculate_recency_penalty(meal.id, recent_history)
        score -= self._calculate_frequency_penalty(meal.id, recent_history)

        # Semantic similarity penalty (if we have embeddings)
        if meal_embedding and recent_history.get('recent_embeddings'):
            score -= self._calculate_similarity_penalty(
                meal_embedding,
                recent_history['recent_embeddings']
            )

        return score

    def _score_explicit_signals(self, meal: Meal, user_data: Dict) -> float:
        """Score based on user's explicit interactions."""
        score = 0.0

        # Positive signals
        if meal.id in user_data['ordered_meal_ids']:
            score += self.WEIGHT_EXPLICIT_POSITIVE * 0.7  # Ordered before
        if meal.id in user_data['liked_meal_ids']:
            score += self.WEIGHT_EXPLICIT_POSITIVE * 0.5  # Explicitly liked

        # Positive reviews
        if meal.id in user_data['user_reviews_by_meal']:
            sentiment = user_data['user_reviews_by_meal'][meal.id]
            if sentiment == 'like':
                score += self.WEIGHT_EXPLICIT_POSITIVE * 0.3
            elif sentiment == 'hate':
                score += self.WEIGHT_EXPLICIT_NEGATIVE

        return score

    def _score_popularity(self, meal: Meal, is_cold_start: bool) -> float:
        """
        Score based on overall popularity.
        Boosted for cold start users who lack personal history.
        """
        try:
            order_count = getattr(meal, 'total_order_count', 0)
            like_count = getattr(meal, 'total_like_count', 0)

            popularity = order_count * 2 + like_count

            # Log scale to prevent outliers from dominating
            base_score = min(self.WEIGHT_POPULARITY, math.log(popularity + 1) * 2)

            # Cold start boost
            if is_cold_start:
                base_score += self.COLD_START_POPULARITY_BOOST * (base_score / self.WEIGHT_POPULARITY)

            return base_score
        except Exception:
            return 0.0

    def _score_time_of_day(self, meal: Meal, user) -> float:
        """Score based on time-of-day match."""
        current_period = user.get_time_period()
        if meal.times_of_day and current_period in meal.times_of_day:
            return self.WEIGHT_TIME_OF_DAY
        return 0.0

    def _score_budget_fit(self, meal: Meal, user) -> float:
        """Score based on budget alignment."""
        if not user.average_meal_budget or user.average_meal_budget <= 0:
            return 0.0

        budget = float(user.average_meal_budget)
        price = float(meal.price)

        if budget == 0:
            return 0.0

        ratio = price / budget

        # Sweet spot: 70-100% of budget
        if 0.7 <= ratio <= 1.0:
            return self.WEIGHT_BUDGET_FIT
        elif 0.5 <= ratio <= 1.1:
            return self.WEIGHT_BUDGET_FIT * 0.5
        else:
            return 0.0

    # =========================================================================
    # LAYER 3: DECAY-BASED DIVERSITY
    # =========================================================================

    def _calculate_recency_penalty(
        self,
        meal_id: int,
        recent_history: Dict
    ) -> float:
        """
        Calculate penalty using exponential decay.

        Penalty = MAX_PENALTY * (DECAY_RATE ^ days_ago)

        Day 0 (today): Would be max penalty but we exclude today's meals
        Day 1: ~18 points
        Day 2: ~12 points
        Day 3: ~8 points
        Day 4: ~6 points
        Day 5: ~4 points
        """
        days_ago = recent_history.get('meal_recency', {}).get(meal_id)

        if days_ago is None:
            return 0.0

        # Exponential decay
        penalty = self.RECENCY_MAX_PENALTY * (self.RECENCY_DECAY_RATE ** days_ago)

        return max(0, penalty)

    def _calculate_frequency_penalty(
        self,
        meal_id: int,
        recent_history: Dict
    ) -> float:
        """
        Calculate penalty for meals recommended too frequently.

        Uses soft penalty that increases with frequency.
        """
        count = recent_history.get('meal_frequency', {}).get(meal_id, 0)

        if count < self.FREQUENCY_PENALTY_THRESHOLD:
            return 0.0

        # Linear penalty above threshold
        excess = count - self.FREQUENCY_PENALTY_THRESHOLD
        penalty = min(self.FREQUENCY_MAX_PENALTY, excess * 5)

        return penalty

    def _calculate_similarity_penalty(
        self,
        meal_embedding: List[float],
        recent_embeddings: List[Tuple[List[float], int]]  # (embedding, days_ago)
    ) -> float:
        """
        Calculate penalty for meals semantically similar to recent recommendations.

        This catches cases like "Jollof Rice" after "Party Jollof" even if
        they're different meal IDs.
        """
        if not recent_embeddings:
            return 0.0

        max_penalty = 0.0

        for recent_emb, days_ago in recent_embeddings:
            similarity = self.embedding_service.cosine_similarity(
                meal_embedding, recent_emb
            )

            if similarity < self.SIMILARITY_PENALTY_THRESHOLD:
                continue

            # Penalty scaled by similarity and recency
            sim_factor = (similarity - self.SIMILARITY_PENALTY_THRESHOLD) / (1 - self.SIMILARITY_PENALTY_THRESHOLD)
            recency_factor = self.RECENCY_DECAY_RATE ** days_ago

            penalty = self.SIMILARITY_MAX_PENALTY * sim_factor * recency_factor
            max_penalty = max(max_penalty, penalty)

        return max_penalty

    def _select_diverse_meals(
        self,
        scored_meals: List[Tuple[Meal, float]],
        time_period: str,
        num_recommendations: int,
        already_selected: Set[int],
        embeddings: Dict[int, List[float]],
        recent_history: Dict
    ) -> List[int]:
        """
        Select diverse meals for a time period.

        Enforces:
        - No duplicates with other periods
        - Cuisine variety
        - Restaurant variety
        - Semantic variety (via embeddings)
        """
        # Filter and categorize candidates
        period_appropriate = []
        period_flexible = []

        for meal, score in scored_meals:
            if meal.id in already_selected:
                continue

            if not meal.times_of_day or time_period in meal.times_of_day:
                period_appropriate.append((meal, score))
            else:
                # Different time period - reduce score
                period_flexible.append((meal, score * 0.7))

        candidates = period_appropriate + period_flexible

        if not candidates:
            return []

        # Greedy selection with diversity constraints
        selected = []
        selected_cuisines = set()
        selected_restaurants = set()
        selected_embeddings = []

        for meal, score in candidates:
            if len(selected) >= num_recommendations:
                break

            # Diversity checks (soft - skip only if we have alternatives)
            if len(candidates) > num_recommendations * 2:
                # Check cuisine overlap
                meal_cuisines = set(meal.cuisine.values_list('name', flat=True))
                if selected_cuisines and meal_cuisines:
                    if meal_cuisines.issubset(selected_cuisines):
                        continue

                # Check restaurant overlap
                if meal.restaurant_id in selected_restaurants:
                    continue

                # Check embedding similarity
                meal_emb = embeddings.get(meal.id)
                if meal_emb and selected_embeddings:
                    max_sim = max(
                        self.embedding_service.cosine_similarity(meal_emb, se)
                        for se in selected_embeddings
                    )
                    if max_sim > 0.85:  # Very similar
                        continue

            # Add to selection
            selected.append(meal.id)
            selected_cuisines.update(meal.cuisine.values_list('name', flat=True))
            selected_restaurants.add(meal.restaurant_id)
            if meal.id in embeddings:
                selected_embeddings.append(embeddings[meal.id])

        # If we don't have enough, relax constraints
        if len(selected) < num_recommendations:
            for meal, score in candidates:
                if meal.id not in selected:
                    selected.append(meal.id)
                    if len(selected) >= num_recommendations:
                        break

        return selected[:num_recommendations]

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _gather_user_data(self, user) -> Dict:
        """Gather user's explicit signals for scoring."""
        liked_meal_ids = set(
            user.meal_preferences.filter(preference='like').values_list('meal_id', flat=True)
        )

        ordered_meal_ids = set(
            user.orders.values_list('meal_id', flat=True).distinct()
        )

        # Reviews with sentiment
        reviews = Review.objects.filter(
            user=user
        ).select_related('order__meal').values('order__meal__id', 'sentiment')

        user_reviews_by_meal = {}
        for review in reviews:
            meal_id = review['order__meal__id']
            if meal_id not in user_reviews_by_meal:
                user_reviews_by_meal[meal_id] = review['sentiment']

        # Collaborative filtering
        collaborative_meal_ids = self._get_collaborative_filtering_meals(
            user, liked_meal_ids
        )

        return {
            'liked_meal_ids': liked_meal_ids,
            'ordered_meal_ids': ordered_meal_ids,
            'user_reviews_by_meal': user_reviews_by_meal,
            'collaborative_meal_ids': collaborative_meal_ids,
        }

    def _get_recent_recommendation_history(self, user) -> Dict:
        """
        Get recent recommendation history for diversity calculations.

        Returns dict with:
        - meal_recency: {meal_id -> days_ago}
        - meal_frequency: {meal_id -> count}
        - recent_embeddings: [(embedding, days_ago), ...]
        """
        from api.models.meal_embedding import MealEmbedding

        today = user.get_local_time().date()
        lookback_date = today - timedelta(days=max(
            self.RECENCY_LOOKBACK_DAYS,
            self.FREQUENCY_LOOKBACK_DAYS,
            self.SIMILARITY_LOOKBACK_DAYS
        ))

        recommendations = Recommendation.objects.filter(
            user=user,
            day__gte=lookback_date,
            day__lt=today
        ).values('meal_id', 'day')

        meal_recency = {}
        meal_frequency = defaultdict(int)
        recent_meal_ids_with_days = []  # For embedding lookup

        for rec in recommendations:
            meal_id = rec['meal_id']
            days_ago = (today - rec['day']).days

            # Recency (keep earliest/most recent occurrence)
            if days_ago <= self.RECENCY_LOOKBACK_DAYS:
                if meal_id not in meal_recency or days_ago < meal_recency[meal_id]:
                    meal_recency[meal_id] = days_ago

            # Frequency
            if days_ago <= self.FREQUENCY_LOOKBACK_DAYS:
                meal_frequency[meal_id] += 1

            # For similarity checking
            if days_ago <= self.SIMILARITY_LOOKBACK_DAYS:
                recent_meal_ids_with_days.append((meal_id, days_ago))

        # Get embeddings for recent meals
        recent_embeddings = []
        if recent_meal_ids_with_days:
            meal_ids = list(set(mid for mid, _ in recent_meal_ids_with_days))
            cached_embeddings = MealEmbedding.objects.filter(
                meal_id__in=meal_ids
            ).values('meal_id', 'embedding')

            emb_by_meal = {e['meal_id']: e['embedding'] for e in cached_embeddings}

            for meal_id, days_ago in recent_meal_ids_with_days:
                if meal_id in emb_by_meal:
                    recent_embeddings.append((emb_by_meal[meal_id], days_ago))

        return {
            'meal_recency': meal_recency,
            'meal_frequency': dict(meal_frequency),
            'recent_embeddings': recent_embeddings,
        }

    def _get_collaborative_filtering_meals(
        self,
        user,
        user_liked_meal_ids: Set[int]
    ) -> Set[int]:
        """Find meals liked by users with similar taste."""
        if not user_liked_meal_ids:
            return set()

        try:
            similar_users = MealPreference.objects.filter(
                meal_id__in=user_liked_meal_ids,
                preference='like'
            ).exclude(
                user=user
            ).values('user').annotate(
                overlap_count=Count('id')
            ).order_by('-overlap_count')[:10]

            similar_user_ids = [item['user'] for item in similar_users]

            if not similar_user_ids:
                return set()

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

    def _get_special_occasion_boosts(self, user) -> Dict[int, float]:
        """Get meal boosts for today's special occasions."""
        try:
            from api.models.special_occasion import SpecialOccasion

            today = user.get_local_time().date()
            occasions = SpecialOccasion.get_active_occasions_for_date(
                date=today,
                city=user.city
            ).prefetch_related('meals')

            meal_boosts = {}
            for occasion in occasions:
                for meal in occasion.meals.all():
                    meal_boosts[meal.id] = meal_boosts.get(meal.id, 0.0) + occasion.boost_weight

            return meal_boosts

        except Exception as e:
            logger.error(f"Error fetching special occasions: {e}")
            return {}

    def _get_exploration_rate(
        self,
        user,
        user_profile: Optional[Dict],
        override: Optional[float]
    ) -> float:
        """Determine exploration rate based on user maturity."""
        if override is not None:
            return max(0.0, min(1.0, override))

        # Use order count as proxy for user maturity
        order_count = user.orders.count()

        if order_count < 5:
            return self.EPSILON_NEW_USER
        elif order_count < 20:
            return self.EPSILON_REGULAR_USER
        else:
            return self.EPSILON_ESTABLISHED_USER

    def _apply_exploration(
        self,
        recommendations: Dict[str, List[int]],
        available_meals: List[Meal],
        epsilon: float
    ) -> Dict[str, List[int]]:
        """Apply epsilon-greedy exploration."""
        if epsilon <= 0 or not available_meals:
            return recommendations

        all_selected = set()
        for meals in recommendations.values():
            all_selected.update(meals)

        exploration_pool = [m for m in available_meals if m.id not in all_selected]

        if not exploration_pool:
            return recommendations

        exploration_count = 0

        for period in ['morning', 'afternoon', 'evening']:
            meals = recommendations[period].copy()

            for i in range(len(meals)):
                if random.random() < epsilon and exploration_pool:
                    random_meal = random.choice(exploration_pool)

                    # Swap
                    old_id = meals[i]
                    meals[i] = random_meal.id

                    # Update pools
                    all_selected.discard(old_id)
                    all_selected.add(random_meal.id)
                    exploration_pool = [m for m in exploration_pool if m.id != random_meal.id]

                    exploration_count += 1

            recommendations[period] = meals

        if exploration_count > 0:
            logger.info(f"Exploration: replaced {exploration_count} meals (epsilon={epsilon:.2f})")

        return recommendations
