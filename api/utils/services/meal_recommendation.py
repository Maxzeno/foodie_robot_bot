# services/meal_recommendation_service.py
import json
from typing import List, Dict, Optional
from openai import OpenAI
from django.conf import settings
from django.db import models
from datetime import timedelta
from api.models.meal import Meal
import random

class MealRecommendationService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API)
    
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
        recommendations = self._call_llm(user_context, meals_context, num_recommendations_per_period)
        
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
        queryset = Meal.objects.filter(
            available=True,
            city=user.city
        )
        
        # Exclude meals outside budget
        if user.average_meal_budget:
            queryset = queryset.filter(price__lte=user.average_meal_budget)
        
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

        # Exclude recently recommended meals
        today = user.get_local_time().date()
        yesterday = today - timedelta(days=1)
        day_before_yesterday = today - timedelta(days=2)

        recent_meal_ids = user.recommendations.filter(
            day__in=[yesterday, day_before_yesterday]
        ).values_list('meal__id', flat=True)

        if recent_meal_ids:
            queryset = queryset.exclude(id__in=recent_meal_ids)

        # yesterday = user.get_local_time().date() - timedelta(days=1)
        # recommended_yesterday = list(user.recommendations.filter(day=yesterday).values_list('meal__id', flat=True))
        # if recommended_yesterday:
        #     queryset = queryset.exclude(id__in=recommended_yesterday)


        # Exclude specific meals if provided
        if exclude_meal_ids:
            queryset = queryset.exclude(id__in=exclude_meal_ids)

         # Filter by fitness goals: meals that match user's goal OR have no fitness goals
        if user.fitness_goals:
            queryset = queryset.filter(
                models.Q(fitness_goals=user.fitness_goals) | 
                models.Q(fitness_goals__isnull=True)
            ).distinct()
        
        # Filter by preferred cuisine: meals that match user's preferences OR have no cuisine set
        user_preferred_cuisines = user.preferred_cuisine.all()
        if user_preferred_cuisines.exists():
            queryset = queryset.filter(
                models.Q(cuisine__in=user_preferred_cuisines) | 
                models.Q(cuisine__isnull=True)
            ).distinct()
        
        # Prefetch related data for efficiency
        queryset = queryset.prefetch_related(
            'fitness_goals', 
            'cuisine',
            'meal_preferences',
            'reviews'
        ).select_related('currency')
        
        return list(queryset[:100])  # Limit to avoid token limits
    
    def _build_user_context(self, user) -> Dict:
        user_health_conditions = list(user.health_conditions.values_list('name', flat=True))
        user_allergies = list(user.allergies.values_list('name', flat=True))
        user_preferred_cuisines = list(user.preferred_cuisine.values_list('name', flat=True))
        
        # Get user's meal preferences
        liked_meals = list(
            user.meal_preferences.filter(preference='like').values_list('meal__name', flat=True)
        )
        # hated_meals = list(
        #     user.meal_preferences.filter(preference='hate').values_list('meal__name', flat=True)
        # )
        
        return {
            "fitness_goal": user.fitness_goals.name if user.fitness_goals else None,
            "health_conditions": user_health_conditions,
            "allergies": user_allergies,
            "preferred_cuisines": user_preferred_cuisines,
            "liked_meals": liked_meals,
            # "hated_meals": hated_meals,
            # "gender": user.gender,
            # "budget": float(user.average_meal_budget) if user.average_meal_budget else None,
            # "currency": user.currency.code if user.currency else None,
        }
    
    def _build_meals_context(self, meals) -> List[Dict]:
        meals_data = []
        
        for meal in meals:
            meal_data = {
                "id": meal.id,
                "name": meal.name,
                # "description": meal.description,
                # "price": float(meal.price),

                "calories": float(meal.calories) if meal.calories else None,
                "protein": float(meal.protein) if meal.protein else None,
                "carbs": float(meal.carbs) if meal.carbs else None,
                "fats": float(meal.fats) if meal.fats else None,
                "fiber": float(meal.fiber) if meal.fiber else None,
                "cuisines": list(meal.cuisine.values_list('name', flat=True)),
                "fitness_goals": list(meal.fitness_goals.values_list('name', flat=True)),
            }
            meals_data.append(meal_data)
        
        return meals_data
    
    def _call_llm(
        self, 
        user_context: Dict, 
        meals_context: List[Dict], 
        num_recommendations_per_period: int
    ) -> Dict:
        """
        Call the LLM API and parse the response to extract meal IDs for different times of day
        """
        prompt = self._build_prompt(user_context, meals_context, num_recommendations_per_period)
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
            available_ids = [m['id'] for m in meals_context[:total_needed]]
            
            return {
                "morning": available_ids[:num_recommendations_per_period],
                "afternoon": available_ids[num_recommendations_per_period:num_recommendations_per_period*2],
                "evening": available_ids[num_recommendations_per_period*2:num_recommendations_per_period*3]
            }
    
    def _build_prompt(
        self, 
        user_context: Dict, 
        meals_context: List[Dict], 
        num_recommendations_per_period: int
    ) -> str:
        """
        Build the prompt for the LLM with structured output requirements
        """
        prompt = f"""You are a nutritionist and meal recommendation expert. Based on the user's profile and available meals, recommend the best meals for morning, afternoon, and evening.

USER PROFILE:
{json.dumps(user_context, indent=2)}

AVAILABLE MEALS:
{json.dumps(meals_context, indent=2)}

INSTRUCTIONS:
1. Consider the user's fitness goals, health conditions, allergies, and cuisine preferences
2. Prioritize meals the user has liked in the past
3. Consider nutritional balance based on fitness goals
4. Provide variety in cuisines and meal types
5. Morning meals should be lighter with good energy (higher carbs, moderate protein)
6. Afternoon meals should be balanced and substantial (balanced macros)
7. Evening meals should support recovery and be easier to digest (higher protein, moderate carbs)
8. Ensure no meal is recommended more than once across all time periods

RESPONSE FORMAT:
You must respond with ONLY valid JSON in this exact format:
{{
  "morning": [1, 2],
  "afternoon": [3, 4],
  "evening": [5, 6]
}}

Each time period must contain exactly {num_recommendations_per_period} valid meal IDs from the available meals list above.
Do not include any other text, explanations, or markdown formatting - just the raw JSON object.
"""
        return prompt
    
    def _parse_llm_response(
        self, 
        response_text: str, 
        meals_context: List[Dict],
        num_recommendations_per_period: int
    ) -> Dict:
        """
        Parse the LLM response to extract meal IDs for different times of day
        """
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
            valid_meal_ids = [m['id'] for m in meals_context]
            
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
            