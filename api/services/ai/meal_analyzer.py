import base64
import logging
from typing import Optional
from openai import OpenAI
from django.conf import settings
from api.schemas.meal_analysis import MealAnalysisResponse

logger = logging.getLogger(__name__)


class MealAnalyzer:
    """
    AI-powered meal analyzer using GPT-4 Vision to extract nutritional
    and dietary information from meal name and photo.
    """

    def __init__(self, model: str = "gpt-4o-2024-08-06"):
        """
        Initialize the meal analyzer.

        Args:
            model: OpenAI model to use (must support vision and structured outputs). Options:
                   - gpt-4o-2024-08-06 (recommended - supports structured outputs)
                   - gpt-4o-mini-2024-07-18 (faster, cheaper alternative)
        """
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model

    def analyze_meal(
        self,
        meal_name: str,
        image_url: Optional[str] = None,
        image_file: Optional[bytes] = None
    ) -> Optional[MealAnalysisResponse]:
        """
        Analyze a meal from its name and photo to extract nutritional info.

        Args:
            meal_name: Name/description of the meal
            image_url: URL to the meal image (e.g., Cloudinary URL)
            image_file: Raw image bytes (if not using URL)

        Returns:
            MealAnalysisResponse with extracted info, or None if analysis fails
        """
        if not meal_name:
            logger.error("Meal name is required for analysis")
            return None

        if not image_url and not image_file:
            logger.warning("No image provided. Analysis will be based on name only.")

        try:
            # Build the message content
            content = self._build_message_content(meal_name, image_url, image_file)

            # Call OpenAI API with structured output
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
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
        image_file: Optional[bytes]
    ) -> list:
        """
        Build the message content array for the API call.
        Supports both URL-based and base64-encoded images.
        """
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
        elif image_file:
            # Encode image to base64
            base64_image = base64.b64encode(image_file).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "high"
                }
            })

        return content

    def _get_system_prompt(self) -> str:
        """
        Return the system prompt that instructs the AI how to analyze meals.
        """
        return """You are a professional nutritionist and food analysis expert. Your task is to analyze meals and provide accurate nutritional and dietary information.

When analyzing a meal:

1. **Nutritional Information**: Estimate calories, macronutrients (protein, carbs, fats), and micronutrients (fiber, sugar, sodium, cholesterol) per serving. Be realistic and consider portion sizes visible in the image.

2. **Fitness Goals**: Determine which fitness goals this meal supports:
   - weight_loss: Low calorie, high protein/fiber, moderate portions
   - muscle_gain: High protein, moderate to high calories, good carbs
   - maintenance: Balanced macros, moderate calories

3. **Health Conditions**: Identify health conditions that should RESTRICT or AVOID this meal:
   - diabetes: High sugar, refined carbs, high glycemic index
   - hypertension: High sodium, processed meats
   - high_cholesterol: High saturated fats, trans fats, cholesterol
   - anemia: No iron-rich foods present (for tracking)
   - celiac: Contains gluten (wheat, barley, rye)
   - lactose_intolerance: Contains dairy/lactose

4. **Allergens**: Identify allergens PRESENT in the meal:
   - peanuts, seafood, dairy, gluten, eggs, soy, tree_nuts

5. **Cuisine**: Identify the cuisine type(s) based on ingredients, cooking style, and presentation. Use underscores for multi-word cuisines (e.g., vegan_vegetarian).

Available cuisines: vegan_vegetarian, nigerian, ghanaian, ethiopian, moroccan, italian, french, spanish, greek, british, chinese, japanese, korean, thai, indian, vietnamese, filipino, american, mexican, brazilian, argentinian, caribbean

6. **Times of Day**: Determine which times of day this meal is best suited for:
   - morning: Breakfast foods (eggs, pancakes, oatmeal, light meals, energy-boosting foods)
   - afternoon: Lunch foods (moderate portions, balanced meals, sandwiches, salads)
   - evening: Dinner foods (heavier meals, proteins, comfort foods, family-style dishes)

   Note: Some meals can be appropriate for multiple times of day (e.g., rice dishes, soups)

**Important Guidelines:**
- Be conservative with estimates - it's better to slightly underestimate than overestimate
- Only mark health conditions/allergens that are CLEARLY present or problematic
- Consider both visible ingredients AND typical preparation methods
- For serving_amount_g, estimate the total weight of the meal including all components
- Provide a confidence level (high/medium/low) and brief reasoning

Return your analysis in the structured format provided."""

    def analyze_from_cloudinary_url(self, meal_name: str, cloudinary_url: str) -> Optional[MealAnalysisResponse]:
        """
        Convenience method for analyzing meals with Cloudinary URLs.

        Args:
            meal_name: Name of the meal
            cloudinary_url: Cloudinary image URL

        Returns:
            MealAnalysisResponse or None
        """
        return self.analyze_meal(meal_name=meal_name, image_url=cloudinary_url)
