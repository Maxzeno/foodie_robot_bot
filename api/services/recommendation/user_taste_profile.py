# services/recommendation/user_taste_profile.py
"""
User Taste Profile Service - Learning User Preferences

This service builds a semantic taste profile for each user by:
1. Analyzing their order history (what they actually eat)
2. Incorporating explicit preferences (likes/hates)
3. Weighting reviews and ratings
4. Considering recency (recent behavior matters more)

The taste profile is a weighted average of meal embeddings that represents
what the user likes to eat. This enables semantic matching against new meals.
"""

import logging
import math
from typing import List, Dict, Optional, Tuple
from datetime import timedelta
from collections import defaultdict
from django.db.models import Count, Avg, Q, F
from django.utils import timezone

logger = logging.getLogger(__name__)


class UserTasteProfileService:
    """
    Builds and manages user taste profiles for personalized recommendations.

    The taste profile is a weighted embedding vector computed from:
    - Ordered meals (strongest signal - actual behavior)
    - Liked meals (explicit positive preference)
    - Positively reviewed meals (validated satisfaction)
    - Negatively reviewed meals (negative signal)
    - Hated meals (strong negative signal)

    Weighting factors:
    - Recency: Recent interactions weighted more heavily
    - Frequency: Repeated orders indicate strong preference
    - Sentiment: Reviews modify the weight positively or negatively
    """

    # Weight multipliers for different signal types
    WEIGHT_ORDER = 1.0          # Base weight for ordered meals
    WEIGHT_LIKE = 0.8           # Explicit like (slightly lower than order)
    WEIGHT_POSITIVE_REVIEW = 1.2  # Order + positive review
    WEIGHT_NEGATIVE_REVIEW = -0.5  # Negative contribution
    WEIGHT_HATE = -1.0          # Strong negative signal

    # Recency decay (half-life in days)
    RECENCY_HALF_LIFE_DAYS = 30

    # Minimum interactions to build profile
    MIN_INTERACTIONS_FOR_PROFILE = 3

    # Profile cache timeout (rebuild periodically)
    PROFILE_CACHE_HOURS = 6

    def __init__(self, embedding_service=None):
        """
        Initialize with optional embedding service.

        Args:
            embedding_service: MealEmbeddingService instance (lazy loaded if not provided)
        """
        self._embedding_service = embedding_service

    @property
    def embedding_service(self):
        """Lazy load embedding service."""
        if self._embedding_service is None:
            from api.services.recommendation.meal_embedding import MealEmbeddingService
            self._embedding_service = MealEmbeddingService()
        return self._embedding_service

    def _compute_recency_weight(self, days_ago: int) -> float:
        """
        Compute recency weight using exponential decay.

        More recent interactions have higher weight.
        Half-life determines how quickly old interactions lose influence.

        Args:
            days_ago: Number of days since interaction

        Returns:
            Weight between 0 and 1
        """
        if days_ago <= 0:
            return 1.0

        # Exponential decay: weight = 0.5^(days_ago / half_life)
        decay = math.pow(0.5, days_ago / self.RECENCY_HALF_LIFE_DAYS)
        return max(0.1, decay)  # Minimum weight of 0.1

    def _gather_user_meal_interactions(self, user) -> Dict[int, Dict]:
        """
        Gather all user interactions with meals.

        Collects data from:
        - Orders (with timestamps and quantities)
        - MealPreferences (likes/hates)
        - Reviews (ratings and sentiment)

        Returns:
            Dict mapping meal_id -> interaction data
        """
        from api.models.order import Order
        from api.models.meal_preference import MealPreference
        from api.models.review import Review

        today = timezone.now().date()
        interactions = defaultdict(lambda: {
            'orders': [],
            'preference': None,
            'reviews': [],
            'total_weight': 0.0
        })

        # === ORDERS ===
        orders = Order.objects.filter(
            user=user,
            status='received'  # Only completed orders
        ).values('meal_id', 'quantity', 'created_at')

        for order in orders:
            meal_id = order['meal_id']
            days_ago = (today - order['created_at'].date()).days
            quantity = order['quantity'] or 1

            interactions[meal_id]['orders'].append({
                'days_ago': days_ago,
                'quantity': quantity
            })

        # === PREFERENCES (like/hate) ===
        preferences = MealPreference.objects.filter(
            user=user
        ).values('meal_id', 'preference')

        for pref in preferences:
            meal_id = pref['meal_id']
            interactions[meal_id]['preference'] = pref['preference']

        # === REVIEWS ===
        reviews = Review.objects.filter(
            user=user
        ).select_related('order').values(
            'order__meal_id', 'meal_rating', 'sentiment', 'created_at'
        )

        for review in reviews:
            meal_id = review['order__meal_id']
            days_ago = (today - review['created_at'].date()).days

            interactions[meal_id]['reviews'].append({
                'rating': review['meal_rating'],
                'sentiment': review['sentiment'],
                'days_ago': days_ago
            })

        return dict(interactions)

    def _compute_meal_weight(self, interaction_data: Dict) -> float:
        """
        Compute final weight for a meal based on all interactions.

        Combines:
        - Order frequency and recency
        - Explicit preferences
        - Review sentiment

        Args:
            interaction_data: Dict with 'orders', 'preference', 'reviews'

        Returns:
            Float weight (can be negative for disliked meals)
        """
        weight = 0.0

        # === ORDER WEIGHT ===
        for order in interaction_data['orders']:
            recency = self._compute_recency_weight(order['days_ago'])
            # Quantity matters but with diminishing returns
            quantity_factor = math.log(order['quantity'] + 1) + 1
            weight += self.WEIGHT_ORDER * recency * quantity_factor

        # === PREFERENCE WEIGHT ===
        preference = interaction_data['preference']
        if preference == 'like':
            weight += self.WEIGHT_LIKE
        elif preference == 'hate':
            weight += self.WEIGHT_HATE

        # === REVIEW WEIGHT ===
        for review in interaction_data['reviews']:
            recency = self._compute_recency_weight(review['days_ago'])

            if review['sentiment'] == 'like':
                weight += self.WEIGHT_POSITIVE_REVIEW * recency
            elif review['sentiment'] == 'hate':
                weight += self.WEIGHT_NEGATIVE_REVIEW * recency
            else:
                # Neutral - small positive (they ordered it)
                weight += 0.1 * recency

            # Rating bonus/penalty (1-5 scale, 3 is neutral)
            rating_modifier = (review['rating'] - 3) * 0.1 * recency
            weight += rating_modifier

        return weight

    def build_taste_profile(
        self,
        user,
        force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        Build a taste profile for the user.

        The profile contains:
        - embedding: Weighted average of meal embeddings
        - positive_meals: Meals with positive weight (for boosting)
        - negative_meals: Meals with negative weight (for penalizing)
        - cuisine_preferences: Derived cuisine weights
        - confidence: How confident we are in this profile

        Args:
            user: User instance
            force_refresh: Bypass cache if True

        Returns:
            Dict with profile data, or None if insufficient data
        """
        from api.models.meal import Meal
        from django.core.cache import cache

        cache_key = f"user_taste_profile_{user.id}"

        # Check cache
        if not force_refresh:
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Taste profile cache hit for user {user.id}")
                return cached

        # Gather interactions
        interactions = self._gather_user_meal_interactions(user)

        if len(interactions) < self.MIN_INTERACTIONS_FOR_PROFILE:
            logger.info(f"User {user.id} has insufficient interactions "
                       f"({len(interactions)}) for taste profile")
            return None

        # Compute weights for each meal
        meal_weights = {}
        positive_meals = []
        negative_meals = []

        for meal_id, data in interactions.items():
            weight = self._compute_meal_weight(data)
            meal_weights[meal_id] = weight

            if weight > 0:
                positive_meals.append((meal_id, weight))
            elif weight < 0:
                negative_meals.append((meal_id, abs(weight)))

        # Sort by weight
        positive_meals.sort(key=lambda x: x[1], reverse=True)
        negative_meals.sort(key=lambda x: x[1], reverse=True)

        # Get meal embeddings for weighted average
        meal_ids = [mid for mid, w in meal_weights.items() if w > 0]

        if not meal_ids:
            logger.info(f"User {user.id} has no positive meal interactions")
            return None

        meals = list(Meal.objects.filter(id__in=meal_ids))
        embeddings = self.embedding_service.get_embeddings_batch(meals)

        # Compute weighted average embedding
        embedding_dim = 1536
        weighted_embedding = [0.0] * embedding_dim
        total_weight = 0.0

        for meal_id, weight in meal_weights.items():
            if weight <= 0 or meal_id not in embeddings:
                continue

            embedding = embeddings[meal_id]
            for i in range(embedding_dim):
                weighted_embedding[i] += embedding[i] * weight
            total_weight += weight

        if total_weight > 0:
            weighted_embedding = [v / total_weight for v in weighted_embedding]

        # Compute cuisine preferences from interactions
        cuisine_weights = self._compute_cuisine_preferences(meals, meal_weights)

        # Compute profile confidence (based on data quality)
        confidence = self._compute_profile_confidence(interactions, meal_weights)

        profile = {
            'embedding': weighted_embedding,
            'positive_meal_ids': [mid for mid, _ in positive_meals[:50]],
            'negative_meal_ids': [mid for mid, _ in negative_meals[:50]],
            'meal_weights': meal_weights,
            'cuisine_preferences': cuisine_weights,
            'confidence': confidence,
            'interaction_count': len(interactions),
        }

        # Cache the profile
        cache.set(cache_key, profile, self.PROFILE_CACHE_HOURS * 3600)

        logger.info(f"Built taste profile for user {user.id}: "
                   f"{len(positive_meals)} positive, {len(negative_meals)} negative, "
                   f"confidence: {confidence:.2f}")

        return profile

    def _compute_cuisine_preferences(
        self,
        meals: List,
        meal_weights: Dict[int, float]
    ) -> Dict[str, float]:
        """
        Derive cuisine preferences from meal interactions.

        Args:
            meals: List of Meal instances
            meal_weights: Dict mapping meal_id -> weight

        Returns:
            Dict mapping cuisine_name -> preference score
        """
        cuisine_weights = defaultdict(float)
        cuisine_counts = defaultdict(int)

        for meal in meals:
            weight = meal_weights.get(meal.id, 0)
            if weight <= 0:
                continue

            cuisines = list(meal.cuisine.values_list('name', flat=True))
            for cuisine in cuisines:
                cuisine_weights[cuisine] += weight
                cuisine_counts[cuisine] += 1

        # Normalize by count
        result = {}
        for cuisine, total_weight in cuisine_weights.items():
            count = cuisine_counts[cuisine]
            result[cuisine] = total_weight / count if count > 0 else 0

        return dict(result)

    def _compute_profile_confidence(
        self,
        interactions: Dict,
        meal_weights: Dict[int, float]
    ) -> float:
        """
        Compute confidence score for the taste profile.

        Higher confidence when:
        - More interactions
        - More recent interactions
        - More consistent signals (not many hates after orders)

        Returns:
            Float between 0 and 1
        """
        if not interactions:
            return 0.0

        # Factor 1: Interaction count (log scale)
        count_factor = min(1.0, math.log(len(interactions) + 1) / math.log(50))

        # Factor 2: Positive vs negative ratio
        positive_count = sum(1 for w in meal_weights.values() if w > 0)
        total_count = len(meal_weights)
        ratio_factor = positive_count / total_count if total_count > 0 else 0

        # Factor 3: Has reviews (stronger signal)
        has_reviews = any(data['reviews'] for data in interactions.values())
        review_factor = 1.2 if has_reviews else 1.0

        confidence = count_factor * 0.5 + ratio_factor * 0.5
        confidence = min(1.0, confidence * review_factor)

        return confidence

    def get_meal_affinity_score(
        self,
        user_profile: Dict,
        meal,
        meal_embedding: Optional[List[float]] = None
    ) -> float:
        """
        Compute how well a meal matches the user's taste profile.

        Uses cosine similarity between meal embedding and profile embedding,
        plus explicit signals (positive/negative meal lists).

        Args:
            user_profile: Profile from build_taste_profile()
            meal: Meal instance
            meal_embedding: Pre-computed embedding (optional)

        Returns:
            Affinity score (0-100 scale, higher = better match)
        """
        if not user_profile:
            return 50.0  # Neutral score for users without profile

        # Check explicit positive/negative lists
        if meal.id in user_profile.get('negative_meal_ids', []):
            # Explicitly disliked - strong penalty
            return 10.0

        if meal.id in user_profile.get('positive_meal_ids', []):
            # Explicitly liked - boost
            explicit_weight = user_profile.get('meal_weights', {}).get(meal.id, 0)
            return min(95.0, 70.0 + explicit_weight * 5)

        # Compute semantic similarity
        if meal_embedding is None:
            meal_embedding = self.embedding_service.get_embedding(meal)

        if not meal_embedding or not user_profile.get('embedding'):
            return 50.0

        similarity = self.embedding_service.cosine_similarity(
            user_profile['embedding'],
            meal_embedding
        )

        # Convert similarity (-1 to 1) to affinity score (0-100)
        # Typical similarities range from 0.3 to 0.9
        # Map 0.3 -> 30, 0.7 -> 70, 0.9 -> 90
        base_score = (similarity - 0.2) * 100  # 0.2-1.0 -> 0-80
        base_score = max(20, min(85, base_score))

        # Apply cuisine preference boost
        cuisine_boost = self._compute_cuisine_boost(meal, user_profile)
        base_score += cuisine_boost

        # Apply confidence factor (less confident profiles get scores closer to 50)
        confidence = user_profile.get('confidence', 0.5)
        final_score = 50 + (base_score - 50) * confidence

        return max(0, min(100, final_score))

    def _compute_cuisine_boost(self, meal, user_profile: Dict) -> float:
        """
        Compute cuisine preference boost for a meal.

        Args:
            meal: Meal instance
            user_profile: User taste profile

        Returns:
            Boost value (-10 to +10)
        """
        cuisine_prefs = user_profile.get('cuisine_preferences', {})
        if not cuisine_prefs:
            return 0.0

        meal_cuisines = list(meal.cuisine.values_list('name', flat=True))
        if not meal_cuisines:
            return 0.0

        # Average preference for meal's cuisines
        total_pref = 0.0
        count = 0
        for cuisine in meal_cuisines:
            if cuisine in cuisine_prefs:
                total_pref += cuisine_prefs[cuisine]
                count += 1

        if count == 0:
            return 0.0

        avg_pref = total_pref / count

        # Scale to -10 to +10
        max_pref = max(cuisine_prefs.values()) if cuisine_prefs else 1
        normalized = (avg_pref / max_pref) if max_pref > 0 else 0

        return normalized * 10
