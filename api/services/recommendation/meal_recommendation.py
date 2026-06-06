# services/meal_recommendation_service.py
import json
from typing import List, Dict, Optional
from openai import OpenAI
from django.conf import settings
from datetime import timedelta
from api.models.meal import Meal
import random
from api.services.recommendation.embedding_recommendation import EmbeddingRecommendationService


class MealRecommendationService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_service = EmbeddingRecommendationService()

    def get_recommendations(
        self,
        user,
        num_recommendations_per_period: int = 2,
        exclude_meal_ids: Optional[List[int]] = None
    ) -> Dict:
        """
        Get optimized meal recommendations using embedding-based approach.

        This is the RECOMMENDED method:
        - 95%+ cost reduction vs LLM
        - Highly personalized based on preferences, fitness goals, budget
        - Avoids recently recommended meals
        - Ensures diversity
        - Time-of-day appropriate

        Returns:
            Dict with keys: morning, afternoon, evening (each containing meal IDs)
        """
        return self.embedding_service.get_recommendations(
            user=user,
            num_recommendations_per_period=num_recommendations_per_period,
            exclude_meal_ids=exclude_meal_ids
        )

    def get_recommendations_by_llm(
        self, 
        user, 
        num_recommendations_per_period: int = 2,
        exclude_meal_ids: Optional[List[int]] = None
    ) -> Dict:
        # Get available meals filtered by user's constraints
        available_meals = self._get_eligible_meals(user, exclude_meal_ids)

        if not available_meals:
            return {
                "morning": [],
                "afternoon": [],
                "evening": []
            }
        
        # Prepare context for LLM
        user_context = self._build_user_context(user)
        meals_context = self._build_meals_context(available_meals)
        
        # Get recommendations from LLM
        recommendations = self._call_llm(user_context, meals_context, num_recommendations_per_period, user)
        
        return recommendations
    
    def get_recommendations_by_algo(
        self, 
        user, 
        num_recommendations_per_period: int = 2,
        exclude_meal_ids: Optional[List[int]] = None
    ) -> Dict:
        # TODO: available_meals = self._get_eligible_meals(user, exclude_meal_ids)
        # TODO: Remove this
        available_meals = list(Meal.objects.filter(
            available=True,
            city=user.city
        ))

        meal_weights = []
        selected = []

        if not available_meals:
            return {
                "morning": [],
                "afternoon": [],
                "evening": []
            }
        
        liked_meals = set(
            user.meal_preferences.filter(preference='like').values_list('meal__id', flat=True)
        )

        # do some filtering based on time of day
        for i, meal in enumerate(available_meals):
            if meal.id in liked_meals:
                meal_weights.append(0.2)
            else:
                meal_weights.append(0.1)

        for _ in range(num_recommendations_per_period):
            item = random.choices(available_meals, weights=meal_weights, k=1)[0]
            selected.append(item)
            # Remove the selected item to avoid duplicates
            idx = available_meals.index(item)
            available_meals.pop(idx)
            meal_weights.pop(idx)

        selected_ids = [meal.id for meal in selected]
        return {
                "morning": selected_ids,
                "afternoon": selected_ids,
                "evening": selected_ids
            }
    
    def _get_eligible_meals(self, user, exclude_meal_ids=None):
        from django.db.models import Q
        from datetime import datetime

        queryset = Meal.objects.filter(
            available=True,
            city=user.city,
            restaurant__inactive=False  # Exclude meals from inactive restaurants
        ).select_related('restaurant')

        # Stock filter - exclude meals with zero stock
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
        
        # # Exclude meals outside budget
        # if user.average_meal_budget:
        #     queryset = queryset.filter(price__lte=user.average_meal_budget)
        
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

        # # Exclude recently recommended meals
        # today = user.get_local_time().date()
        # yesterday = today - timedelta(days=1)
        # day_before_yesterday = today - timedelta(days=2)

        # recent_meal_ids = user.recommendations.filter(
        #     day__in=[yesterday, day_before_yesterday]
        # ).values_list('meal__id', flat=True)

        # if recent_meal_ids:
        #     queryset = queryset.exclude(id__in=recent_meal_ids)

        # Exclude specific meals if provided
        if exclude_meal_ids:
            queryset = queryset.exclude(id__in=exclude_meal_ids)

        #  # Filter by fitness goals: meals that match user's goal OR have no fitness goals
        # if user.fitness_goals:
        #     queryset = queryset.filter(
        #         models.Q(fitness_goals=user.fitness_goals) | 
        #         models.Q(fitness_goals__isnull=True)
        #     ).distinct()
        
        # # Filter by preferred cuisine: meals that match user's preferences OR have no cuisine set
        # user_preferred_cuisines = user.preferred_cuisine.all()
        # if user_preferred_cuisines.exists():
        #     queryset = queryset.filter(
        #         models.Q(cuisine__in=user_preferred_cuisines) | 
        #         models.Q(cuisine__isnull=True)
        #     ).distinct()
        
        # Prefetch related data for efficiency
        queryset = queryset.prefetch_related(
            'fitness_goals', 
            'cuisine',
            'meal_preferences',
        )
        
        return list(queryset[:100])  # Limit to avoid token limits
    
    def _build_user_context(self, user) -> Dict:
        today = user.get_local_time().date()
        yesterday = today - timedelta(days=1)

        # Get only unique recent meal names (deduplicate)
        recent_meals = list(set(user.recommendations.filter(
            day__in=[today, yesterday]
        ).values_list('meal__name', flat=True)))
        
        user_preferred_cuisines = list(user.preferred_cuisine.values_list('name', flat=True))
        liked_meals = list(
            user.meal_preferences.filter(preference='like').values_list('meal__name', flat=True)
        )
        hated_meals = list(
            user.meal_preferences.filter(preference='hate').values_list('meal__name', flat=True)
        )
        
        # Build compact context - only include non-empty values
        context = {}
        
        if user.fitness_goals:
            context["goal"] = user.fitness_goals.name
        if user_preferred_cuisines:
            context["cuisines"] = user_preferred_cuisines
        if liked_meals:
            context["liked"] = liked_meals
        if hated_meals:
            context["hated"] = hated_meals
        if recent_meals:
            context["recent"] = recent_meals
        if user.city:
            context["city"] = user.city.name
        if user.average_meal_budget:
            context["budget"] = float(user.average_meal_budget)
        if user.city:
            context["curr"] = user.city.currency.code

        return context
    
    def _build_meals_context(self, meals) -> List[Dict]:
        # Ultra-compact meal format: [id, name, price]
        return [[m.id, m.name, float(m.price)] for m in meals]
    
    def _call_llm(
        self, 
        user_context: Dict, 
        meals_context: List[Dict], 
        num_recommendations_per_period: int,
        user
    ) -> Dict:
        """
        Call the LLM API and parse the response to extract meal IDs for different times of day
        """
        prompt = self._build_prompt(user_context, meals_context, num_recommendations_per_period, user)
        print("LLM Prompt:", prompt)  # Debugging
        
        try:
            response = self.client.responses.create(
                model="gpt-5-nano",
                input=prompt,
                store=True,
            )
            
            # Parse the response
            content = response.output_text
            
            print("LLM Response:", content)  # Debugging
            recommendations = self._parse_llm_response(content, meals_context, num_recommendations_per_period)
            
            return recommendations
            
        except Exception as e:
            print(f"Error calling LLM: {e}")
            # Fallback: return random meals distributed across time periods
            total_needed = num_recommendations_per_period * 3
            available_ids = [m[0] for m in meals_context[:total_needed]]
            
            return {
                "morning": available_ids[:num_recommendations_per_period],
                "afternoon": available_ids[num_recommendations_per_period:num_recommendations_per_period*2],
                "evening": available_ids[num_recommendations_per_period*2:num_recommendations_per_period*3]
            }
    
    def _build_prompt(
        self, 
        user_context: Dict, 
        meals_context: List[Dict], 
        num_recommendations_per_period: int,
        user
    ) -> str:
        # Ultra-compact prompt with minified JSON
        prompt = f"""Meal recommendation expert.

Rules: Prioritize user prefs (liked,hated,cuisines,goal,budget,recent). Mix popular+uncommon. Diverse meals/cuisines per period. No dups. Avoid recent meals when possible. Respect budget.

Meals (id,name,price):
{json.dumps(meals_context,separators=(',',':'))}

User:
{json.dumps(user_context,separators=(',',':'))}

Recommend {num_recommendations_per_period} per period. Date: {user.get_local_time().date().strftime('%Y-%m-%d')}
Return: {{"morning":[id,id],"afternoon":[id,id],"evening":[id,id]}}"""
        
        return prompt
    
    def _parse_llm_response(
        self, 
        response_text: str, 
        meals_context: List[Dict],
        num_recommendations_per_period: int
    ) -> Dict:
        try:
            # Try to parse as JSON
            response_text = response_text.strip()
            
            # Handle markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            recommendations = json.loads(response_text)
            
            # Validate structure
            if not isinstance(recommendations, dict):
                raise ValueError("Response is not a dictionary")
            
            required_keys = ["morning", "afternoon", "evening"]
            if not all(key in recommendations for key in required_keys):
                raise ValueError("Missing required time period keys")
            
            # Validate and filter meal IDs
            valid_meal_ids = [m[0] for m in meals_context]
            
            result = {}
            for period in required_keys:
                period_ids = recommendations[period]
                if not isinstance(period_ids, list):
                    period_ids = []
                
                # Ensure all IDs are integers and valid
                validated_ids = []
                for mid in period_ids:
                    try:
                        meal_id = int(mid)
                        if meal_id in valid_meal_ids:
                            validated_ids.append(meal_id)
                    except (ValueError, TypeError):
                        continue
                
                result[period] = validated_ids[:num_recommendations_per_period]
            
            return result
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response was: {response_text}")
            
            # Return empty structure
            return {
                "morning": [],
                "afternoon": [],
                "evening": []
            }