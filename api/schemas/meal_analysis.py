from pydantic import BaseModel, Field
from typing import List, Optional


class MealAnalysisResponse(BaseModel):
    """
    Structured response from GPT Vision API for meal analysis.
    Maps to Django Meal model fields.
    """
    # Nutritional information
    calories: Optional[float] = Field(None, description="Estimated calories per serving")
    protein: Optional[float] = Field(None, description="Protein in grams")
    carbs: Optional[float] = Field(None, description="Carbohydrates in grams")
    fats: Optional[float] = Field(None, description="Fats in grams")
    fiber: Optional[float] = Field(None, description="Fiber in grams")
    sugar: Optional[float] = Field(None, description="Sugar in grams")
    sodium: Optional[float] = Field(None, description="Sodium in milligrams")
    cholesterol: Optional[float] = Field(None, description="Cholesterol in milligrams")
    serving_amount_g: Optional[float] = Field(None, description="Total serving weight in grams")

    # Fitness goals (values must match FitnessGoalChoices)
    fitness_goals: List[str] = Field(
        default_factory=list,
        description="Fitness goals this meal supports: weight_loss, muscle_gain, or maintenance"
    )

    # Restricted health conditions (values must match HealthConditionChoices)
    restricted_health_conditions: List[str] = Field(
        default_factory=list,
        description="Health conditions that should avoid this meal: diabetes, hypertension, high_cholesterol, anemia, celiac, lactose_intolerance"
    )

    # Allergens (values must match AllergyChoices)
    restricted_allergies: List[str] = Field(
        default_factory=list,
        description="Allergens present in this meal: peanuts, seafood, dairy, gluten, eggs, soy, tree_nuts"
    )

    # Cuisine types (values must match CuisineChoices)
    cuisine: List[str] = Field(
        default_factory=list,
        description="Cuisine types that best describe this meal"
    )

    # Times of day (values must match TimeOfDayChoices)
    times_of_day: List[str] = Field(
        default_factory=list,
        description="Times of day this meal is best suited for: morning, afternoon, evening"
    )

    # Additional metadata
    confidence: Optional[str] = Field(
        None,
        description="AI's confidence level in the analysis: high, medium, low"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Brief explanation of the analysis"
    )
