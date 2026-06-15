from pydantic import BaseModel, Field
from typing import List, Optional


class MealAnalysisResponse(BaseModel):
    """
    Structured response from GPT Vision API for meal analysis.
    Maps to Django Meal model fields.
    """
    # Nutritional information
    calories: Optional[float] = Field(None, description="Estimated calories per serving")

    # Fitness goals (values must match FitnessGoalChoices)
    fitness_goals: List[str] = Field(
        default_factory=list,
        description="Fitness goals this meal supports: weight_loss, muscle_gain, or maintenance"
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
