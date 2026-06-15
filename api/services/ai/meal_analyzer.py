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
    ) -> str:
        # Build dynamic lists from database
        fitness_goals_str = ", ".join(fitness_goals) if fitness_goals else "weight_loss, muscle_gain, maintenance"

        return f"""You are an expert nutritionist analyzing meal images. Provide accurate, realistic nutritional estimates.

**IMPORTANT IMAGE LIMITATION:**
The image provided is for reference only and does NOT represent the actual meal size or portion. Always assume a standard Nigerian restaurant portion size when estimating nutritional values.

**CRITICAL: Base your analysis on:**
1. The SPECIFIC INGREDIENTS you can identify in the image
2. The PREPARATION METHOD (fried, grilled, steamed, etc.)
3. A STANDARD PORTION SIZE (not what appears in the image)

**DO NOT use generic or template values. Each meal is different - your calorie estimates should vary significantly based on the ingredients and preparation method.**

**Analyze the meal image and return a JSON object with this exact structure:**

{{
  "calories": <realistic number based on actual portion>,
  "fitness_goals": [<list of goal names from available options>],
  "times_of_day": [<list from: morning, afternoon, evening>],
  "confidence": "<high/medium/low>",
  "reasoning": "<explain your calorie estimate and portion size assessment>"
}}

**Available Options (use ONLY these exact values):**
- Fitness Goals: {fitness_goals_str}

**Guidelines:**
- Consider visible ingredients AND typical preparation methods
- Multiple times_of_day are allowed
- Your reasoning should explain how you estimated the portion size and calories (note image does not reflect actual portion)"""

    def analyze_from_cloudinary_url(
        self,
        meal_name: str,
        cloudinary_url: str,
        fitness_goals: Optional[list[str]] = None,
    ) -> Optional[MealAnalysisResponse]:
        return self.analyze_meal(
            meal_name=meal_name,
            image_url=cloudinary_url,
            fitness_goals=fitness_goals,
        )
