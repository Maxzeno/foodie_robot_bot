# services/meal_recommendation.py
"""
Meal Recommendation Service - 3-Layer Architecture

This service provides personalized meal recommendations using a three-layer approach:

Layer 1: Hard Constraint Filtering (Availability)
    - Filters out hated meals and unavailable meals
    - Ensures only available meals from active restaurants are considered

Layer 2: Smart Scoring System (Personalization)
    - Scores eligible meals based on multiple weighted factors
    - Considers user history, preferences, and social signals
    - Applies special occasion boosts for date-based cultural/seasonal recommendations

Layer 3: Diversity Enforcement (Preventing Duplicates)
    - Prevents same-day meal duplicates
    - Ensures variety across time periods and days
    - Enforces cuisine and restaurant diversity

Special Occasions Feature:
    - Configurable date-based meal boosting (e.g., Rice & Chicken on Dec 25 in Nigeria)
    - Supports recurring annual dates and specific one-time dates
    - City-specific or global occasions
    - Admin-configurable via Django admin interface
"""

import logging
import random
import math
from typing import List, Dict, Optional, Set, Tuple
from datetime import timedelta
from django.db.models import Count, Q

from api.models.meal import Meal
from api.models.meal_preference import MealPreference
from api.models.recommendation import Recommendation
from api.models.review import Review

logger = logging.getLogger(__name__)


class MealRecommendationService:
    """
    Intelligent meal recommendation system with 3-layer architecture.

    Scoring Weights (tune these to adjust behavior):
    - User History: 40% weight (strongest signal)
    - Preference Alignment: 30% weight
    - Diversity Factors: 20% weight (negative penalties)
    - Social Signals: 10% weight
    """

    # === USER HISTORY WEIGHTS (Strongest signals) ===
    WEIGHT_ORDERED_BEFORE = 35.0        # Previously ordered meals
    WEIGHT_LIKED = 30.0                 # Explicitly liked meals
    WEIGHT_REVIEWED_POSITIVELY = 25.0   # Meals with positive reviews
    WEIGHT_REVIEWED_NEGATIVELY = -40.0  # Meals with negative reviews (penalty)

    # === PREFERENCE ALIGNMENT WEIGHTS ===
    WEIGHT_FITNESS_GOAL = 20.0          # Matches user's fitness goal
    WEIGHT_BUDGET_OPTIMAL = 10.0        # Perfect budget fit (80-100%)
    WEIGHT_BUDGET_GOOD = 5.0            # Good budget fit (60-120%)
    WEIGHT_NUTRITION_MAX = 10.0         # Nutritional alignment bonus

    # === DIVERSITY PENALTIES (Prevent repetition) ===
    # Optimized for 30-40 meals per city - lighter penalties allow 2-day repeats occasionally
    PENALTY_RECENT_MAX = 20.0           # Maximum penalty for recent meals (relaxed from 30)
    PENALTY_FREQUENCY_MAX = 15.0        # Maximum penalty for frequent meals
    PENALTY_SEMANTIC_SIMILARITY_MAX = 12.0  # Penalty for similar meal names (relaxed from 20)

    # === SOCIAL SIGNALS ===
    WEIGHT_POPULARITY_MAX = 10.0        # Social proof (orders + likes)
    WEIGHT_COLLABORATIVE_FILTERING = 18.0  # Similar users' preferences
    WEIGHT_TIME_OF_DAY = 8.0            # Time-appropriate meals

    # === SPECIAL OCCASIONS ===
    WEIGHT_SPECIAL_OCCASION_DEFAULT = 50.0  # Default boost for special occasions (configurable per occasion)

    # === EXPLORATION ===
    WEIGHT_EXPLORATION_MAX = 8.0        # Random exploration bonus (scoring phase)

    # === EPSILON-GREEDY EXPLORATION ===
    # Controls exploration vs exploitation tradeoff
    EPSILON_NEW_USER = 0.20            # 20% exploration for new users (< 5 orders)
    EPSILON_REGULAR_USER = 0.15        # 15% exploration for regular users (5-20 orders)
    EPSILON_ESTABLISHED_USER = 0.10    # 10% exploration for established users (> 20 orders)

    # === QUERY LIMITS ===
    MAX_CANDIDATE_MEALS = 150           # Limit initial query size
    COLLABORATIVE_SIMILAR_USERS = 10    # Number of similar users to consider

    # === LOOKBACK WINDOWS ===
    # Optimized for cost/speed - shorter windows = less data queried
    RECENCY_LOOKBACK_DAYS = 7           # How far back to check for recent meals (reduced from 14)
    FREQUENCY_LOOKBACK_DAYS = 14        # Window for frequency calculation (reduced from 30)
    SEMANTIC_SIMILARITY_LOOKBACK_DAYS = 3  # How far back to check for similar meal names (reduced from 7)

    def __init__(self):
        """Initialize the meal recommendation service."""
        logger.info("MealRecommendationService initialized")

    def get_recommendations(
        self,
        user,
        num_recommendations_per_period: int = 2,
        exclude_meal_ids: Optional[List[int]] = None,
        exploration_rate: Optional[float] = None
    ) -> Dict:
        """
        Get personalized meal recommendations for morning, afternoon, and evening.
        Uses epsilon-greedy exploration to balance personalization with discovery.

        Args:
            user: User instance
            num_recommendations_per_period: Number of meals per time period (default: 2)
            exclude_meal_ids: Additional meal IDs to exclude (optional)
            exploration_rate: Override epsilon for exploration (0.0-1.0). If None, auto-determined
                             based on user's order history. Typical values:
                             - 0.20 (20%) for new users
                             - 0.15 (15%) for regular users
                             - 0.10 (10%) for established users

        Returns:
            Dict with keys 'morning', 'afternoon', 'evening', each containing meal IDs
            When no meals are available, includes 'no_results_reason' with filter stats
            Example success: {
                "morning": [1, 2],
                "afternoon": [3, 4],
                "evening": [5, 6]
            }
            Example no results: {
                "morning": [],
                "afternoon": [],
                "evening": [],
                "no_results_reason": {
                    "primary_reason": "budget",
                    "total_meals_in_city": 50,
                    "filtered_by_budget": 45,
                    ...
                }
            }
        """
        logger.info(f"Getting recommendations for user {user.id} ({num_recommendations_per_period} per period)")

        # === LAYER 1: HARD CONSTRAINT FILTERING ===
        # Get meals already recommended today to prevent same-day duplicates
        today_meal_ids = self._get_today_recommended_meals(user)
        logger.info(f"Already recommended today: {len(today_meal_ids)} meals")

        # Combine with additional exclusions
        all_exclusions = set(today_meal_ids)
        if exclude_meal_ids:
            all_exclusions.update(exclude_meal_ids)

        # Get eligible meals (safety + availability filters) with tracking
        available_meals, filter_stats = self._get_eligible_meals(
            user, list(all_exclusions), track_filter_reasons=True
        )
        logger.info(f"Eligible meals after filtering: {len(available_meals)}")

        if not available_meals:
            # Try fallback with minimal filtering - we want users to always get recommendations
            logger.info(f"No meals after strict filtering. Trying fallback for user {user.id}")
            available_meals = self._get_fallback_meals(user, list(all_exclusions))

            if not available_meals:
                logger.warning(f"No eligible meals found for user even with fallback. Reason: {filter_stats.get('primary_reason', 'unknown')}")
                return {
                    "morning": [],
                    "afternoon": [],
                    "evening": [],
                    "no_results_reason": filter_stats
                }

            logger.info(f"Fallback found {len(available_meals)} meals")

        # === LAYER 2: SMART SCORING SYSTEM ===
        # Gather user data for scoring
        user_data = self._gather_user_data(user)

        # Score all available meals
        scored_meals = []
        for meal in available_meals:
            score = self._score_meal(meal, user, user_data)
            scored_meals.append((meal, score))

        # Sort by score (highest first)
        scored_meals.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Scored {len(scored_meals)} meals. Top score: {scored_meals[0][1]:.2f}")

        # === LAYER 3: DIVERSITY ENFORCEMENT ===
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

        logger.info(f"Final recommendations (before exploration): {len(morning_meals)} morning, "
                   f"{len(afternoon_meals)} afternoon, {len(evening_meals)} evening")

        # === EPSILON-GREEDY EXPLORATION ===
        # Apply exploration to introduce serendipity and help discover new meals
        epsilon = self._get_exploration_rate(user, exploration_rate)
        if epsilon > 0:
            recommendations = self._apply_epsilon_greedy_exploration(
                recommendations, available_meals, epsilon
            )
        print("Final Recommendations with Exploration:", recommendations)
        return recommendations

    # ============================================================================
    # LAYER 1: HARD CONSTRAINT FILTERING
    # ============================================================================

    def _get_today_recommended_meals(self, user) -> List[int]:
        """
        Get meal IDs already recommended to user today.
        This prevents same-day duplicates across all time periods.
        """
        today = user.get_local_time().date()
        return list(
            Recommendation.objects.filter(
                user=user,
                day=today
            ).values_list('meal_id', flat=True).distinct()
        )

    def _get_eligible_meals(
        self,
        user,
        exclude_meal_ids: Optional[List[int]] = None,
        track_filter_reasons: bool = False
    ) -> List[Meal] | Tuple[List[Meal], Dict]:
        """
        Layer 1: Apply hard constraints to filter eligible meals.

        Filters applied:
        1. Safety filters (hated meals)
        2. Availability filters (stock, time, restaurant status)
        3. Exclusion lists (today's meals, custom exclusions)

        Args:
            user: User instance
            exclude_meal_ids: Meal IDs to exclude
            track_filter_reasons: If True, returns tuple of (meals, filter_stats)

        Returns:
            List of Meal objects that pass all constraints
            OR tuple of (List[Meal], Dict) if track_filter_reasons=True
        """
        filter_stats = {
            'total_meals_in_city': 0,
            'filtered_by_unavailable': 0,
            'filtered_by_inactive_restaurant': 0,
            'filtered_by_hated': 0,
            'filtered_by_stock': 0,
            'filtered_by_restaurant_hours': 0,
            'filtered_by_meal_hours': 0,
            'filtered_by_budget': 0,
            'filtered_by_exclusions': 0,
            'remaining_after_filters': 0,
            'user_budget': float(user.average_meal_budget) if user.average_meal_budget else None,
        }

        # Get total meals in city for context
        if track_filter_reasons:
            filter_stats['total_meals_in_city'] = Meal.objects.filter(city=user.city).count()

        # Start with base query
        queryset = Meal.objects.filter(
            available=True,
            city=user.city,
            restaurant__inactive=False  # Only active restaurants
        ).select_related('restaurant', 'city', 'city__currency')

        # === SAFETY FILTERS ===

        # Exclude hated meals (user preference)
        hated_meal_ids = list(
            user.meal_preferences.filter(preference='hate').values_list('meal_id', flat=True)
        )
        if hated_meal_ids:
            if track_filter_reasons:
                filter_stats['filtered_by_hated'] = queryset.filter(id__in=hated_meal_ids).count()
            queryset = queryset.exclude(id__in=hated_meal_ids)
            logger.debug(f"Excluding {len(hated_meal_ids)} hated meals")

        # === AVAILABILITY FILTERS ===

        # Stock filter - exclude out-of-stock meals
        if track_filter_reasons:
            before_stock = queryset.count()
        queryset = queryset.filter(
            Q(daily_stock_limit__isnull=True) |  # Unlimited stock
            Q(remaining_stock__isnull=True) |     # Stock not initialized
            Q(remaining_stock__gt=0)               # Has stock remaining
        )
        if track_filter_reasons:
            filter_stats['filtered_by_stock'] = before_stock - queryset.count()

        # Time-based filtering
        current_time = user.get_local_time().time()
        current_day = user.get_local_time().strftime('%A').lower()

        # Filter by restaurant operating hours and days
        if track_filter_reasons:
            before_restaurant_hours = queryset.count()
        queryset = queryset.filter(
            Q(restaurant__available_days=[]) |  # Open all days
            Q(restaurant__available_days__contains=[current_day])  # Open today
        ).filter(
            restaurant__open_time__lte=current_time,
            restaurant__close_time__gte=current_time
        )
        if track_filter_reasons:
            filter_stats['filtered_by_restaurant_hours'] = before_restaurant_hours - queryset.count()

        # Filter by meal availability times
        if track_filter_reasons:
            before_meal_hours = queryset.count()
        queryset = queryset.filter(
            Q(available_from_time__isnull=True) | Q(available_from_time__lte=current_time)
        ).filter(
            Q(available_to_time__isnull=True) | Q(available_to_time__gte=current_time)
        )
        if track_filter_reasons:
            filter_stats['filtered_by_meal_hours'] = before_meal_hours - queryset.count()

        # Budget filter (soft - allow 50% over budget)
        if user.average_meal_budget and user.average_meal_budget > 0:
            max_price = float(user.average_meal_budget) * 1.5
            if track_filter_reasons:
                before_budget = queryset.count()
            queryset = queryset.filter(price__lte=max_price)
            if track_filter_reasons:
                filter_stats['filtered_by_budget'] = before_budget - queryset.count()
            logger.debug(f"Budget filter: max price {max_price}")

        # === EXCLUSION FILTERS ===

        # Exclude specific meals (today's recommendations + custom)
        if exclude_meal_ids:
            if track_filter_reasons:
                filter_stats['filtered_by_exclusions'] = queryset.filter(id__in=exclude_meal_ids).count()
            queryset = queryset.exclude(id__in=exclude_meal_ids)
            logger.debug(f"Excluding {len(exclude_meal_ids)} specific meals")

        # === OPTIMIZATIONS ===

        # Annotate with popularity metrics (avoid N+1 queries later)
        queryset = queryset.annotate(
            total_order_count=Count('orders', distinct=True),
            total_like_count=Count(
                'meal_preferences',
                filter=Q(meal_preferences__preference='like'),
                distinct=True
            )
        )

        # Prefetch related data
        queryset = queryset.prefetch_related(
            'fitness_goals',
            'cuisine',
            'meal_preferences',
        )

        # Limit query size for performance
        result = list(queryset[:self.MAX_CANDIDATE_MEALS])

        if track_filter_reasons:
            filter_stats['remaining_after_filters'] = len(result)
            # Determine primary reason for no results
            if len(result) == 0:
                filter_stats['primary_reason'] = self._determine_primary_filter_reason(filter_stats)
            return result, filter_stats

        return result

    def _determine_primary_filter_reason(self, filter_stats: Dict) -> str:
        """
        Determine the primary reason why no meals are available.

        Priority order (most actionable first):
        1. No meals in city at all
        2. Budget too restrictive
        3. Restaurant hours (time-based)
        4. Hated meals

        Returns:
            str: Primary reason code
        """
        if filter_stats['total_meals_in_city'] == 0:
            return 'no_meals_in_city'

        # Check which filter eliminated the most meals (biggest impact)
        filter_counts = [
            ('budget', filter_stats.get('filtered_by_budget', 0)),
            ('restaurant_hours', filter_stats.get('filtered_by_restaurant_hours', 0)),
            ('meal_hours', filter_stats.get('filtered_by_meal_hours', 0)),
            ('hated', filter_stats.get('filtered_by_hated', 0)),
            ('stock', filter_stats.get('filtered_by_stock', 0)),
        ]

        # Sort by count (descending)
        filter_counts.sort(key=lambda x: x[1], reverse=True)

        # Return the biggest filter reason, or 'unknown' if all are 0
        if filter_counts[0][1] > 0:
            return filter_counts[0][0]

        return 'unknown'

    def _get_fallback_meals(
        self,
        user,
        exclude_meal_ids: Optional[List[int]] = None
    ) -> List[Meal]:
        """
        Fallback query with minimal filtering to ensure users always get recommendations.

        Only applies essential filters:
        - Available meals in user's city
        - Active restaurants
        - Excludes already recommended meals today

        Relaxes:
        - Budget constraints
        - Restaurant/meal hours
        - Stock limits
        - Hated meals (if user has hated too many)

        Returns:
            List of Meal objects
        """
        queryset = Meal.objects.filter(
            available=True,
            city=user.city,
            restaurant__inactive=False
        ).select_related('restaurant', 'city', 'city__currency')

        # Only apply exclusions for today's already recommended meals
        if exclude_meal_ids:
            queryset = queryset.exclude(id__in=exclude_meal_ids)

        # Annotate with popularity for scoring
        queryset = queryset.annotate(
            total_order_count=Count('orders', distinct=True),
            total_like_count=Count(
                'meal_preferences',
                filter=Q(meal_preferences__preference='like'),
                distinct=True
            )
        )

        queryset = queryset.prefetch_related(
            'fitness_goals',
            'cuisine',
            'meal_preferences',
        )

        return list(queryset[:self.MAX_CANDIDATE_MEALS])

    # ============================================================================
    # LAYER 2: SMART SCORING SYSTEM
    # ============================================================================

    def _gather_user_data(self, user) -> Dict:
        """
        Gather all user-related data needed for scoring.
        Organized in one place to minimize database queries.

        Returns:
            Dict containing user history, preferences, and signals
        """
        # User history signals
        liked_meal_ids = set(
            user.meal_preferences.filter(preference='like').values_list('meal_id', flat=True)
        )

        ordered_meal_ids = set(
            user.orders.values_list('meal_id', flat=True).distinct()
        )

        # Reviews with sentiment
        user_reviews_by_meal = self._get_user_reviews_by_meal(user)

        # OPTIMIZED: Combine 3 queries into 1 for recent recommendations data
        # This fetches recent_meal_history, meal_frequency, and recent_meal_keywords in one query
        recent_data = self._get_combined_recent_recommendations_data(user)

        # Collaborative filtering recommendations
        collaborative_meal_ids = self._get_collaborative_filtering_meals(
            user, liked_meal_ids
        )

        # Special occasions data
        special_occasion_boosts = self._get_special_occasion_boosts(user)

        return {
            'liked_meal_ids': liked_meal_ids,
            'ordered_meal_ids': ordered_meal_ids,
            'user_reviews_by_meal': user_reviews_by_meal,
            'recent_meal_history': recent_data['recent_meal_history'],
            'meal_frequency': recent_data['meal_frequency'],
            'collaborative_meal_ids': collaborative_meal_ids,
            'recent_meal_keywords': recent_data['recent_meal_keywords'],
            'special_occasion_boosts': special_occasion_boosts,
        }

    def _score_meal(self, meal: Meal, user, user_data: Dict) -> float:
        """
        Layer 2: Calculate comprehensive score for a meal.

        Scoring breakdown:
        - User History (40%): Orders, likes, reviews
        - Preferences (30%): Fitness goals, cuisine, budget, nutrition
        - Social Signals (10%): Popularity, collaborative filtering, time of day
        - Diversity (-20%): Recency and frequency penalties
        - Exploration (+random): Discovery bonus

        Args:
            meal: Meal instance to score
            user: User instance
            user_data: Pre-gathered user data from _gather_user_data()

        Returns:
            float: Total score for the meal
        """
        score = 0.0

        # === USER HISTORY SIGNALS (Strongest) ===
        score += self._score_user_history(meal, user_data)

        # === PREFERENCE ALIGNMENT ===
        score += self._score_preferences(meal, user)

        # === SOCIAL SIGNALS ===
        score += self._score_social_signals(meal, user, user_data)

        # === SPECIAL OCCASIONS ===
        score += self._score_special_occasion(meal, user_data)

        # === DIVERSITY PENALTIES ===
        score -= self._calculate_recency_penalty(meal, user_data['recent_meal_history'])
        score -= self._calculate_frequency_penalty(meal, user_data['meal_frequency'])
        score -= self._calculate_semantic_similarity_penalty(meal, user_data['recent_meal_keywords'])

        # === EXPLORATION BONUS ===
        score += self._score_exploration()

        return score

    def _score_user_history(self, meal: Meal, user_data: Dict) -> float:
        """
        Score based on user's historical interactions with this meal.
        This is the strongest signal for personalization.
        """
        score = 0.0

        # Previously ordered (strongest positive signal)
        if meal.id in user_data['ordered_meal_ids']:
            score += self.WEIGHT_ORDERED_BEFORE

        # Explicitly liked
        if meal.id in user_data['liked_meal_ids']:
            score += self.WEIGHT_LIKED

        # Review sentiment (very strong signal)
        if meal.id in user_data['user_reviews_by_meal']:
            sentiment = user_data['user_reviews_by_meal'][meal.id]
            if sentiment == 'like':
                score += self.WEIGHT_REVIEWED_POSITIVELY
            elif sentiment == 'hate':
                score += self.WEIGHT_REVIEWED_NEGATIVELY  # Negative weight

        return score

    def _score_preferences(self, meal: Meal, user) -> float:
        """
        Score based on user's stated preferences and constraints.
        """
        score = 0.0

        # Fitness goal match
        if user.fitness_goals:
            meal_fitness_goal_ids = set(meal.fitness_goals.values_list('id', flat=True))
            if user.fitness_goals.id in meal_fitness_goal_ids:
                score += self.WEIGHT_FITNESS_GOAL

        # Budget fit
        score += self._score_budget(meal, user)

        # Nutritional alignment
        score += self._score_nutrition(meal, user)

        return score

    def _score_social_signals(self, meal: Meal, user, user_data: Dict) -> float:
        """
        Score based on social proof and time appropriateness.
        """
        score = 0.0

        # Popularity (orders + likes from all users)
        score += self._score_popularity(meal)

        # Collaborative filtering (similar users liked this)
        if meal.id in user_data['collaborative_meal_ids']:
            score += self.WEIGHT_COLLABORATIVE_FILTERING

        # Time-of-day appropriateness
        score += self._score_time_of_day(meal, user)

        return score

    def _score_budget(self, meal: Meal, user) -> float:
        """
        Score based on how well meal price fits user's budget.

        Scoring:
        - 80-100% of budget: Optimal (+10 points)
        - 60-80% or 100-120%: Good (+5 points)
        - Outside range: Penalty
        """
        if not user.average_meal_budget or user.average_meal_budget <= 0:
            return 0.0

        budget = float(user.average_meal_budget)
        price = float(meal.price)

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
        """
        Score based on nutritional value aligned with fitness goals.

        - Muscle gain: High protein meals preferred
        - Weight loss: Lower calorie meals preferred
        - Maintenance: Balanced macros preferred
        """
        if not meal.calories or not user.fitness_goals:
            return 0.0

        score = 0.0
        fitness_goal_name = user.fitness_goals.name.lower()

        # Muscle gain: Prioritize high protein
        if 'muscle_gain' in fitness_goal_name or 'muscle gain' in fitness_goal_name:
            if meal.protein and meal.calories > 0:
                protein_ratio = float(meal.protein) / (float(meal.calories) / 100)
                score += min(self.WEIGHT_NUTRITION_MAX, protein_ratio * 2)

        # Weight loss: Prefer lower calorie meals
        elif 'weight_loss' in fitness_goal_name or 'weight loss' in fitness_goal_name:
            if meal.calories < 500:
                score += self.WEIGHT_NUTRITION_MAX
            elif meal.calories < 700:
                score += self.WEIGHT_NUTRITION_MAX / 2

        # Maintenance: Prefer balanced macros
        elif 'maintenance' in fitness_goal_name:
            if meal.protein and meal.carbs and meal.fats:
                total_cals = float(meal.calories)
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
        """
        Score based on time-of-day appropriateness.
        Meals tagged for current time period get a bonus.
        """
        current_period = user.get_time_period()
        if meal.times_of_day and current_period in meal.times_of_day:
            return self.WEIGHT_TIME_OF_DAY
        return 0.0

    def _score_popularity(self, meal: Meal) -> float:
        """
        Score based on social proof (popularity from other users).
        Uses annotated fields to avoid N+1 queries.
        """
        try:
            order_count = getattr(meal, 'total_order_count', 0)
            like_count = getattr(meal, 'total_like_count', 0)

            # Weight orders more than likes
            popularity = order_count * 2 + like_count

            # Logarithmic scaling (diminishing returns)
            popularity_score = min(
                self.WEIGHT_POPULARITY_MAX,
                math.log(popularity + 1) * 2
            )
            return popularity_score
        except Exception as e:
            logger.warning(f"Error calculating popularity for meal {meal.id}: {e}")
            return 0.0

    def _score_exploration(self) -> float:
        """
        Add random exploration factor for serendipitous discovery.
        Helps users discover new meals they might like.
        """
        return random.uniform(0, self.WEIGHT_EXPLORATION_MAX)

    def _calculate_recency_penalty(self, meal: Meal, recent_meal_history: Dict[int, int]) -> float:
        """
        Calculate penalty based on how recently the meal was recommended.

        Optimized for 30-40 meals - lighter penalties allow occasional 2-day repeats.

        Penalty decay curve (7-day window):
        - Day 1: -20 pts (max penalty)
        - Day 2: -14 pts (can still win if highly liked)
        - Day 3-4: -10 to -6 pts (moderate penalty)
        - Day 5-7: -3 to 0 pts (light penalty, fading out)
        """
        if meal.id not in recent_meal_history:
            return 0.0

        days_ago = recent_meal_history[meal.id]

        if days_ago == 1:
            # Day 1: Maximum penalty (but not impossible to recommend)
            return self.PENALTY_RECENT_MAX  # -20
        elif days_ago == 2:
            # Day 2: Strong penalty (allows repeats if meal is highly preferred)
            return 14.0
        elif days_ago <= 4:
            # Days 3-4: Moderate penalty
            return 10.0 - ((days_ago - 2) * 2)
        elif days_ago <= 7:
            # Days 5-7: Light penalty, fading out
            return max(0, 6.0 - ((days_ago - 4) * 2))
        else:
            return 0.0

    def _calculate_frequency_penalty(self, meal: Meal, meal_frequency: Dict[int, int]) -> float:
        """
        Calculate penalty based on how frequently meal was recommended.
        Prevents over-recommendation of the same meals.

        Penalty tiers:
        - 5+ times: Maximum penalty (-15)
        - 4 times: -10
        - 3 times: -7
        - 2 times: -4
        - 1 time: -2
        """
        if meal.id not in meal_frequency:
            return 0.0

        frequency = meal_frequency[meal.id]

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

    def _calculate_semantic_similarity_penalty(
        self,
        meal: Meal,
        recent_meal_keywords: Dict[str, int]
    ) -> float:
        """
        Calculate penalty based on semantic similarity to recently recommended meals.
        This prevents recommending similar meals (e.g., "Jollof Rice with Chicken" after
        "Party Jollof Rice") even if they're from different restaurants.

        Optimized for 30-40 meals - 3-day window balances diversity with flexibility.

        Algorithm:
        1. Extract keywords from current meal name
        2. Check if keywords appear in recent recommendations (last 3 days)
        3. Apply penalty based on keyword overlap and recency

        Example:
        - Recently recommended (1 day ago): "Jollof Rice with Chicken"
        - Candidate meal: "Party Jollof Rice"
        - Shared keywords: {"jollof", "rice"} = 2/3 keywords = 67% overlap
        - Penalty: ~8 pts (moderate, allows if meal is highly preferred)

        Args:
            meal: Meal to score
            recent_meal_keywords: Dict mapping keyword -> days_ago

        Returns:
            float: Penalty score (0 to PENALTY_SEMANTIC_SIMILARITY_MAX = 12 pts)
        """
        if not recent_meal_keywords:
            return 0.0

        # Extract keywords from current meal
        meal_keywords = self._extract_meal_keywords(meal.name)

        if not meal_keywords:
            return 0.0

        # Find overlapping keywords with recent recommendations
        overlapping_keywords = meal_keywords & recent_meal_keywords.keys()

        if not overlapping_keywords:
            return 0.0

        # Calculate penalty based on:
        # 1. Number of overlapping keywords (more overlap = higher penalty)
        # 2. Recency of the most recent overlapping keyword (more recent = higher penalty)

        overlap_count = len(overlapping_keywords)
        total_keywords = len(meal_keywords)

        # Get the most recent occurrence among overlapping keywords
        most_recent_days_ago = min(
            recent_meal_keywords[keyword] for keyword in overlapping_keywords
        )

        # Overlap ratio (0.0 to 1.0)
        # Example: "Jollof Rice" has 2 keywords, both overlap = 1.0
        overlap_ratio = overlap_count / total_keywords if total_keywords > 0 else 0.0

        # Recency factor (more recent = higher penalty)
        # Day 1: factor = 1.0, Day 7: factor = 0.0
        recency_factor = max(0, 1.0 - (most_recent_days_ago / self.SEMANTIC_SIMILARITY_LOOKBACK_DAYS))

        # Combined penalty
        # Maximum penalty when: high overlap + very recent
        penalty = self.PENALTY_SEMANTIC_SIMILARITY_MAX * overlap_ratio * recency_factor

        if penalty > 0:
            logger.debug(
                f"Semantic penalty for '{meal.name}': {penalty:.2f} "
                f"(overlap: {overlap_count}/{total_keywords}, {most_recent_days_ago}d ago)"
            )

        return penalty

    # ============================================================================
    # LAYER 3: DIVERSITY ENFORCEMENT
    # ============================================================================

    def _select_for_time_period(
        self,
        scored_meals: List[Tuple[Meal, float]],
        time_period: str,
        num_recommendations: int,
        already_selected_ids: Set[int]
    ) -> List[int]:
        """
        Layer 3: Select diverse meals for a specific time period.

        Diversity enforcement:
        1. Exclude meals already selected for other time periods
        2. Prefer meals tagged for this time period
        3. Limit same cuisine per period
        4. Limit same restaurant per period
        5. Avoid similar meal names

        Args:
            scored_meals: List of (Meal, score) tuples sorted by score
            time_period: 'morning', 'afternoon', or 'evening'
            num_recommendations: Number of meals to select
            already_selected_ids: Set of meal IDs already selected for other periods

        Returns:
            List of meal IDs selected for this time period
        """
        # Separate meals into time-appropriate and flexible
        period_appropriate = []
        period_flexible = []

        for meal, score in scored_meals:
            # Skip meals already selected for another time period
            if meal.id in already_selected_ids:
                continue

            if not meal.times_of_day:
                # No time restriction - flexible
                period_flexible.append((meal, score))
            elif time_period in meal.times_of_day:
                # Perfect match for this time period
                period_appropriate.append((meal, score))
            else:
                # Tagged for different time, but still consider with penalty
                period_flexible.append((meal, score * 0.7))

        # Prioritize period-appropriate, then flexible
        candidates = period_appropriate + period_flexible

        if not candidates:
            logger.warning(f"No candidates found for {time_period}")
            return []

        # Select diverse meals
        selected = []
        selected_cuisines = set()
        selected_keywords = set()
        selected_restaurants = {}  # restaurant_id -> count

        # Pre-fetch cuisine data to avoid N+1 queries
        meal_cuisines_map = {}
        for meal, score in candidates:
            cuisine_names = [c.name for c in meal.cuisine.all()]
            meal_cuisines_map[meal.id] = set(cuisine_names)

        for meal, score in candidates:
            if len(selected) >= num_recommendations:
                break

            # Get meal attributes for diversity checks
            meal_cuisines = meal_cuisines_map.get(meal.id, set())
            meal_keywords = set(meal.name.lower().split()[:2])  # First 2 words
            restaurant_id = meal.restaurant.id if meal.restaurant else None

            # Apply diversity constraints
            if len(selected) > 0:
                # Check cuisine overlap
                cuisine_overlap = bool(meal_cuisines & selected_cuisines)

                # Check keyword overlap (similar names)
                keyword_overlap = bool(meal_keywords & selected_keywords)

                # Check restaurant limit (max 1 per restaurant per period for diversity)
                if restaurant_id and selected_restaurants.get(restaurant_id, 0) >= 1:
                    # Skip if we have enough candidates
                    if len(candidates) > num_recommendations * 1.5:
                        continue

                # Skip if too similar (only if we have plenty of candidates)
                if len(candidates) > num_recommendations * 2:
                    if cuisine_overlap and keyword_overlap:
                        continue

            # Add to selection
            selected.append(meal.id)
            selected_cuisines.update(meal_cuisines)
            selected_keywords.update(meal_keywords)
            if restaurant_id:
                selected_restaurants[restaurant_id] = selected_restaurants.get(restaurant_id, 0) + 1

        # If we don't have enough, relax diversity constraints
        if len(selected) < num_recommendations:
            remaining = num_recommendations - len(selected)
            for meal, score in candidates:
                if meal.id not in selected:
                    selected.append(meal.id)
                    remaining -= 1
                    if remaining == 0:
                        break

        logger.info(f"Selected {len(selected)} meals for {time_period}")
        return selected[:num_recommendations]

    # ============================================================================
    # EPSILON-GREEDY EXPLORATION
    # ============================================================================

    def _get_exploration_rate(self, user, override_rate: Optional[float] = None) -> float:
        """
        Determine the exploration rate (epsilon) for epsilon-greedy algorithm.

        If override_rate is provided, use that. Otherwise, determine based on user's
        order history to balance exploration vs exploitation.

        Args:
            user: User instance
            override_rate: Manual override for epsilon (0.0-1.0)

        Returns:
            float: Exploration rate between 0.0 and 1.0
        """
        if override_rate is not None:
            # Clamp to valid range
            epsilon = max(0.0, min(1.0, override_rate))
            logger.debug(f"Using override exploration rate: {epsilon}")
            return epsilon

        # Determine epsilon based on user's order history
        order_count = user.orders.count()

        if order_count < 5:
            # New user: High exploration to learn preferences
            epsilon = self.EPSILON_NEW_USER
            user_type = "new"
        elif order_count < 20:
            # Regular user: Moderate exploration
            epsilon = self.EPSILON_REGULAR_USER
            user_type = "regular"
        else:
            # Established user: Low exploration (we know their preferences)
            epsilon = self.EPSILON_ESTABLISHED_USER
            user_type = "established"

        logger.debug(f"Auto-determined exploration rate: {epsilon} ({user_type} user, {order_count} orders)")
        return epsilon

    def _apply_epsilon_greedy_exploration(
        self,
        recommendations: Dict[str, List[int]],
        available_meals: List[Meal],
        epsilon: float
    ) -> Dict[str, List[int]]:
        """
        Apply epsilon-greedy exploration to recommendations.

        For each recommended meal, with probability epsilon, replace it with a random
        meal from the available pool (that's not already recommended).

        This helps:
        - Discover new meals that might become favorites
        - Avoid over-recommending the same meals
        - Learn user preferences faster for new users

        Args:
            recommendations: Dict with morning/afternoon/evening meal IDs
            available_meals: List of all eligible meals
            epsilon: Exploration rate (0.0-1.0)

        Returns:
            Dict: Updated recommendations with some random substitutions
        """
        if epsilon <= 0 or not available_meals:
            return recommendations

        # Track which meals are currently selected
        all_selected_ids = set()
        for period in ['morning', 'afternoon', 'evening']:
            all_selected_ids.update(recommendations[period])

        # Create a pool of exploration candidates (meals not currently selected)
        exploration_pool = [m for m in available_meals if m.id not in all_selected_ids]

        if not exploration_pool:
            logger.debug("No exploration pool available")
            return recommendations

        exploration_count = 0
        total_slots = 0

        # Apply exploration to each time period
        for period in ['morning', 'afternoon', 'evening']:
            meals = recommendations[period].copy()  # Copy to avoid modifying during iteration
            total_slots += len(meals)

            for i in range(len(meals)):
                # With probability epsilon, replace with random meal
                if random.random() < epsilon:
                    # Pick random meal from exploration pool
                    if exploration_pool:
                        random_meal = random.choice(exploration_pool)

                        # Replace the meal
                        old_meal_id = meals[i]
                        meals[i] = random_meal.id

                        # Update tracking
                        all_selected_ids.discard(old_meal_id)
                        all_selected_ids.add(random_meal.id)

                        # Remove from pool to avoid duplicates within same request
                        exploration_pool = [m for m in exploration_pool if m.id != random_meal.id]

                        exploration_count += 1
                        logger.debug(f"Exploration: Replaced meal {old_meal_id} with {random_meal.id} in {period}")

            recommendations[period] = meals

        logger.info(f"Epsilon-greedy exploration: {exploration_count}/{total_slots} meals randomized (ε={epsilon:.2f})")

        return recommendations

    # ============================================================================
    # HELPER METHODS - DATA GATHERING
    # ============================================================================

    def _get_combined_recent_recommendations_data(self, user) -> Dict:
        """
        OPTIMIZED: Combine 3 queries into 1 for better performance.

        Previously this was 3 separate queries:
        1. _get_recent_meal_history() - for recency penalty
        2. _get_meal_frequency() - for frequency penalty
        3. _get_recent_meal_keywords() - for semantic similarity penalty

        Now we fetch all recommendations once and process in memory (much faster).

        Args:
            user: User instance

        Returns:
            Dict containing:
            - recent_meal_history: {meal_id -> days_ago}
            - meal_frequency: {meal_id -> count}
            - recent_meal_keywords: {keyword -> days_ago}
        """
        today = user.get_local_time().date()

        # Use the longest lookback window to fetch all needed data
        max_lookback = max(
            self.RECENCY_LOOKBACK_DAYS,
            self.FREQUENCY_LOOKBACK_DAYS,
            self.SEMANTIC_SIMILARITY_LOOKBACK_DAYS
        )
        cutoff_date = today - timedelta(days=max_lookback)

        # Single query to fetch all recent recommendations with meal names
        recommendations = Recommendation.objects.filter(
            user=user,
            day__gte=cutoff_date,
            day__lt=today  # Exclude today
        ).select_related('meal').values('meal_id', 'meal__name', 'day').order_by('-day')

        # Process data in memory (fast)
        recent_meal_history = {}      # For recency penalty
        meal_frequency_counts = {}     # For frequency penalty
        keyword_history = {}           # For semantic penalty

        recency_cutoff = today - timedelta(days=self.RECENCY_LOOKBACK_DAYS)
        frequency_cutoff = today - timedelta(days=self.FREQUENCY_LOOKBACK_DAYS)
        semantic_cutoff = today - timedelta(days=self.SEMANTIC_SIMILARITY_LOOKBACK_DAYS)

        for rec in recommendations:
            meal_id = rec['meal_id']
            meal_name = rec['meal__name']
            rec_day = rec['day']
            days_ago = (today - rec_day).days

            # Build recent_meal_history (within recency window)
            if rec_day >= recency_cutoff:
                if meal_id not in recent_meal_history or days_ago < recent_meal_history[meal_id]:
                    recent_meal_history[meal_id] = days_ago

            # Build meal_frequency (within frequency window)
            if rec_day >= frequency_cutoff:
                meal_frequency_counts[meal_id] = meal_frequency_counts.get(meal_id, 0) + 1

            # Build keyword_history (within semantic window)
            if rec_day >= semantic_cutoff and meal_name:
                keywords = self._extract_meal_keywords(meal_name)
                for keyword in keywords:
                    if keyword not in keyword_history or days_ago < keyword_history[keyword]:
                        keyword_history[keyword] = days_ago

        logger.debug(
            f"Combined query: {len(recent_meal_history)} recent meals, "
            f"{len(meal_frequency_counts)} frequency entries, "
            f"{len(keyword_history)} keywords"
        )

        return {
            'recent_meal_history': recent_meal_history,
            'meal_frequency': meal_frequency_counts,
            'recent_meal_keywords': keyword_history,
        }

    def _get_user_reviews_by_meal(self, user) -> Dict[int, str]:
        """
        Get user's reviews organized by meal ID with sentiment.

        Returns:
            Dict mapping meal_id -> sentiment ('like' or 'hate')
        """
        reviews = Review.objects.filter(
            user=user
        ).select_related('order__meal').values('order__meal__id', 'sentiment')

        reviews_by_meal = {}
        for review in reviews:
            meal_id = review['order__meal__id']
            sentiment = review['sentiment']
            # Keep the first (most recent) sentiment for each meal
            if meal_id not in reviews_by_meal:
                reviews_by_meal[meal_id] = sentiment

        return reviews_by_meal

    def _get_collaborative_filtering_meals(self, user, user_liked_meal_ids: Set[int]) -> Set[int]:
        """
        Collaborative filtering: Find meals liked by users with similar taste.

        Algorithm:
        1. Find users who liked the same meals as this user
        2. Get meals those similar users liked
        3. Return meals this user hasn't tried yet

        Returns:
            Set of meal IDs recommended by similar users
        """
        if not user_liked_meal_ids:
            return set()

        try:
            # Find users with similar taste (liked same meals)
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

            # Get meals these similar users liked (that current user hasn't)
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

    def _get_recent_meal_history(self, user, lookback_days: int) -> Dict[int, int]:
        """
        Get meals recommended in the last N days with recency info.

        Args:
            user: User instance
            lookback_days: How many days to look back

        Returns:
            Dict mapping meal_id -> days_ago (for most recent occurrence)
        """
        today = user.get_local_time().date()
        cutoff_date = today - timedelta(days=lookback_days)

        recommendations = Recommendation.objects.filter(
            user=user,
            day__gte=cutoff_date,
            day__lt=today  # Exclude today
        ).values('meal_id', 'day')

        meal_history = {}
        for rec in recommendations:
            meal_id = rec['meal_id']
            days_ago = (today - rec['day']).days

            # Keep the most recent occurrence
            if meal_id not in meal_history or days_ago < meal_history[meal_id]:
                meal_history[meal_id] = days_ago

        return meal_history

    def _get_meal_frequency(self, user, lookback_days: int) -> Dict[int, int]:
        """
        Get how many times each meal was recommended in the last N days.

        Args:
            user: User instance
            lookback_days: How many days to look back

        Returns:
            Dict mapping meal_id -> frequency_count
        """
        today = user.get_local_time().date()
        cutoff_date = today - timedelta(days=lookback_days)

        frequency_data = Recommendation.objects.filter(
            user=user,
            day__gte=cutoff_date
        ).values('meal_id').annotate(
            count=Count('id')
        )

        return {item['meal_id']: item['count'] for item in frequency_data}

    def _get_recent_meal_keywords(self, user, lookback_days: int) -> Dict[str, int]:
        """
        Get keywords from recently recommended meal names with recency info.
        This enables semantic diversity - penalizing similar meals (e.g., different Jollof Rice variants).

        Args:
            user: User instance
            lookback_days: How many days to look back

        Returns:
            Dict mapping keyword -> days_ago (for most recent occurrence)
            Example: {"jollof": 2, "rice": 2, "chicken": 5, "pasta": 3}
        """
        today = user.get_local_time().date()
        cutoff_date = today - timedelta(days=lookback_days)

        # Get recent recommendations with meal names
        recommendations = Recommendation.objects.filter(
            user=user,
            day__gte=cutoff_date,
            day__lt=today  # Exclude today
        ).select_related('meal').values('meal__name', 'day')

        keyword_history = {}
        for rec in recommendations:
            meal_name = rec['meal__name']
            days_ago = (today - rec['day']).days

            # Extract keywords from meal name (lowercase, split by spaces/special chars)
            keywords = self._extract_meal_keywords(meal_name)

            # Track the most recent occurrence of each keyword
            for keyword in keywords:
                if keyword not in keyword_history or days_ago < keyword_history[keyword]:
                    keyword_history[keyword] = days_ago

        logger.debug(f"Recent meal keywords (last {lookback_days} days): {len(keyword_history)} unique keywords")
        return keyword_history

    def _extract_meal_keywords(self, meal_name: str) -> Set[str]:
        """
        Extract meaningful keywords from a meal name.
        Removes common stop words and extracts core food terms.

        Args:
            meal_name: Name of the meal (e.g., "Jollof Rice with Chicken")

        Returns:
            Set of keywords (e.g., {"jollof", "rice", "chicken"})
        """
        # Common stop words to ignore (expand as needed)
        stop_words = {
            'with', 'and', 'or', 'in', 'on', 'the', 'a', 'an', 'special',
            'deluxe', 'premium', 'fresh', 'homemade', 'traditional', 'authentic',
            'classic', 'original', 'served', 'hot', 'cold', 'large', 'small',
            'medium', 'regular', 'combo', 'platter', 'bowl', 'plate', 'dish'
        }

        # Lowercase and split by spaces and common separators
        words = meal_name.lower().replace('(', ' ').replace(')', ' ').replace('-', ' ').replace(',', ' ').split()

        # Filter out stop words and very short words
        keywords = {
            word.strip() for word in words
            if len(word) > 2 and word not in stop_words
        }

        return keywords

    # ============================================================================
    # SPECIAL OCCASIONS - DATE-BASED MEAL BOOSTING
    # ============================================================================

    def _get_special_occasion_boosts(self, user) -> Dict[int, float]:
        """
        Get meal ID to boost weight mapping for today's special occasions.

        This method fetches all active special occasions for the user's current date
        and city, then builds a dictionary mapping meal IDs to their boost weights.

        Args:
            user: User instance

        Returns:
            Dict mapping meal_id -> total_boost_weight
            Example: {123: 50.0, 456: 50.0} for Christmas rice and chicken
        """
        try:
            from api.models.special_occasion import SpecialOccasion

            # Get user's current date in their timezone
            today = user.get_local_time().date()

            # Fetch active occasions for today and user's city
            occasions = SpecialOccasion.get_active_occasions_for_date(
                date=today,
                city=user.city
            ).prefetch_related('meals')

            # Build meal_id -> boost mapping
            meal_boosts = {}
            for occasion in occasions:
                for meal in occasion.meals.all():
                    # If a meal appears in multiple occasions, sum the boosts
                    meal_boosts[meal.id] = meal_boosts.get(meal.id, 0.0) + occasion.boost_weight

                if occasion.meals.exists():
                    logger.info(
                        f"Special occasion '{occasion.name}' active: "
                        f"{occasion.meals.count()} meals boosted by {occasion.boost_weight} points"
                    )

            return meal_boosts

        except Exception as e:
            logger.error(f"Error fetching special occasion boosts: {e}")
            return {}

    def _score_special_occasion(self, meal: Meal, user_data: Dict) -> float:
        """
        Score based on special occasions.

        If this meal is associated with a special occasion happening today,
        apply a significant boost to increase its recommendation probability.

        Args:
            meal: Meal instance to score
            user_data: Pre-gathered user data from _gather_user_data()

        Returns:
            float: Boost score (0.0 if no special occasion, or the configured boost weight)
        """
        special_occasion_boosts = user_data.get('special_occasion_boosts', {})

        if meal.id in special_occasion_boosts:
            boost = special_occasion_boosts[meal.id]
            logger.debug(f"Meal '{meal.name}' gets special occasion boost: +{boost:.1f} points")
            return boost

        return 0.0
