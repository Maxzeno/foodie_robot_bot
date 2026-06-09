import logging
from typing import Optional
from openai import OpenAI
from django.conf import settings
from api.schemas.meal_analysis import MealAnalysisResponse

logger = logging.getLogger(__name__)


class MealAnalyzer:

    def __init__(self, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model

    def analyze_meal(
        self,
        meal_name: str,
        image_url: Optional[str] = None,
        fitness_goals: Optional[list[str]] = None,
        health_conditions: Optional[list[str]] = None,
        allergies: Optional[list[str]] = None,
        cuisines: Optional[list[str]] = None,
    ) -> Optional[MealAnalysisResponse]:
        if not meal_name:
            logger.error("Meal name is required for analysis")
            return None

        if not image_url:
            logger.warning("No image provided. Analysis will be based on name only.")

        try:
            # Build the message content
            content = self._build_message_content(meal_name, image_url)

            # Call OpenAI API with structured output
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(
                            fitness_goals=fitness_goals,
                            health_conditions=health_conditions,
                            allergies=allergies,
                            cuisines=cuisines
                        )
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                response_format=MealAnalysisResponse,
                temperature=0.3,  # Lower temperature for more consistent results
            )

            # Extract the structured response
            meal_analysis = response.choices[0].message.parsed

            logger.info(f"Successfully analyzed meal: {meal_name}")
            logger.debug(f"Analysis result: {meal_analysis}")

            return meal_analysis

        except Exception as e:
            logger.error(f"Error analyzing meal '{meal_name}': {str(e)}", exc_info=True)
            return None

    def _build_message_content(
        self,
        meal_name: str,
        image_url: Optional[str],
    ) -> list:
        content = [
            {
                "type": "text",
                "text": f"Analyze this meal: **{meal_name}**"
            }
        ]

        # Add image if provided
        if image_url:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                    "detail": "high"  # Use high detail for better analysis
                }
            })

        return content

    def _get_system_prompt(
        self,
        fitness_goals: Optional[list[str]] = None,
        health_conditions: Optional[list[str]] = None,
        allergies: Optional[list[str]] = None,
        cuisines: Optional[list[str]] = None,
    ) -> str:
        # Build dynamic lists from database
        fitness_goals_str = ", ".join(fitness_goals) if fitness_goals else "weight_loss, muscle_gain, maintenance"
        health_conditions_str = ", ".join(health_conditions) if health_conditions else "diabetes, hypertension, high_cholesterol"
        allergies_str = ", ".join(allergies) if allergies else "peanuts, seafood, dairy, gluten"
        cuisines_str = ", ".join(cuisines) if cuisines else "italian, chinese, mexican, american"

        return f"""You are an expert nutritionist analyzing meal images. Provide accurate, realistic nutritional estimates based on what you actually see in the image.

**CRITICAL: Carefully examine the image provided and base your estimates on:**
1. The ACTUAL PORTION SIZE visible in the image (small, medium, large)
2. The SPECIFIC INGREDIENTS you can identify
3. The PREPARATION METHOD (fried, grilled, steamed, etc.)
4. The QUANTITY of each component on the plate

**DO NOT use generic or template values. Each meal is different - your calorie estimates should vary significantly based on what you see.**

**Analyze the meal image and return a JSON object with this exact structure:**

{{
  "calories": <realistic number based on actual portion>,
  "protein": <number in grams>,
  "carbs": <number in grams>,
  "fats": <number in grams>,
  "fiber": <number in grams>,
  "sugar": <number in grams>,
  "sodium": <number in mg>,
  "cholesterol": <number in mg>,
  "serving_amount_g": <total weight in grams - estimate from image>,
  "fitness_goals": [<list of goal names from available options>],
  "restricted_health_conditions": [<list of condition names that should AVOID this meal>],
  "restricted_allergies": [<list of allergen names PRESENT in meal>],
  "cuisine": [<list of cuisine names>],
  "times_of_day": [<list from: morning, afternoon, evening>],
  "confidence": "<high/medium/low>",
  "reasoning": "<explain your calorie estimate and portion size assessment>"
}}

**Available Options (use ONLY these exact values):**
- Fitness Goals: {fitness_goals_str}
- Health Conditions: {health_conditions_str}
- Allergies: {allergies_str}
- Cuisines: {cuisines_str}

**Guidelines:**
- Provide realistic estimates that match the ACTUAL portion size in the image
- A small salad might be 150-250 calories, a large pasta dish could be 800-1200 calories
- Consider visible ingredients AND typical preparation methods
- Only include health conditions/allergens that are clearly problematic
- Multiple times_of_day and cuisines are allowed
- Your reasoning should explain how you estimated the portion size and calories"""

    def analyze_from_cloudinary_url(
        self,
        meal_name: str,
        cloudinary_url: str,
        fitness_goals: Optional[list[str]] = None,
        health_conditions: Optional[list[str]] = None,
        allergies: Optional[list[str]] = None,
        cuisines: Optional[list[str]] = None,
    ) -> Optional[MealAnalysisResponse]:
        return self.analyze_meal(
            meal_name=meal_name,
            image_url=cloudinary_url,
            fitness_goals=fitness_goals,
            health_conditions=health_conditions,
            allergies=allergies,
            cuisines=cuisines
        )
