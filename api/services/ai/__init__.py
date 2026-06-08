# Avoid importing at module level to prevent circular imports
# Import when needed instead

__all__ = ['FoodBotAIHandler', 'MealAnalyzer']


def __getattr__(name):
    """Lazy import to avoid circular dependency issues."""
    if name == 'FoodBotAIHandler':
        from api.services.ai.orchestrator import FoodBotAIHandler
        return FoodBotAIHandler
    elif name == 'MealAnalyzer':
        from api.services.ai.meal_analyzer import MealAnalyzer
        return MealAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
