"""
Helper functions for generating WhatsApp messages when no meal recommendations are available.
"""
from typing import Dict, Tuple


def get_no_recommendation_message(filter_stats: Dict, currency_symbol: str = "₦") -> str:
    """
    Generate a user-friendly message explaining why no meal recommendations are available.

    Args:
        filter_stats: Dictionary containing filter statistics from MealRecommendationService
        currency_symbol: Currency symbol to use in budget messages (default: ₦)

    Returns:
        str: User-friendly message explaining the issue
    """
    primary_reason = filter_stats.get('primary_reason', 'unknown')

    if primary_reason == 'no_meals_in_city':
        return (
            "We don't have any restaurants available in your area yet. "
            "We're working hard to expand our coverage. Stay tuned!"
        )

    if primary_reason == 'budget':
        user_budget = filter_stats.get('user_budget')
        if user_budget:
            return (
                f"Your meal budget ({currency_symbol}{user_budget:,.0f}) is lower than most meals available. "
                "Consider updating your budget to see more options."
            )
        return (
            "Your meal budget seems too restrictive for available meals. "
            "Consider updating your budget in your profile."
        )

    if primary_reason == 'restaurant_hours':
        return (
            "No restaurants are currently open in your area right now. "
            "We'll send you recommendations when restaurants open."
        )

    if primary_reason == 'meal_hours':
        return (
            "The meals matching your preferences aren't available at this time. "
            "We'll send you recommendations when more options become available."
        )

    if primary_reason == 'hated':
        return (
            "You've marked most available meals as disliked. "
            "Consider updating your meal preferences to see more recommendations."
        )

    if primary_reason == 'stock':
        return (
            "All meals matching your preferences are currently out of stock. "
            "We'll notify you when more options become available."
        )

    # Default/unknown reason
    return (
        "We couldn't find meal recommendations for you right now. "
        "This might be due to your preferences or current availability."
    )


def should_show_profile_update_flow(primary_reason: str) -> bool:
    """
    Determine if the profile update flow should be shown based on the reason.

    Profile update can help with: budget, hated meals.
    Profile update won't help with: no_meals_in_city, restaurant_hours, meal_hours, stock.

    Args:
        primary_reason: The primary reason code for no recommendations

    Returns:
        bool: True if profile update flow should be shown
    """
    profile_fixable_reasons = {'budget', 'hated'}
    return primary_reason in profile_fixable_reasons


def get_no_recommendation_message_short(primary_reason: str) -> str:
    """
    Get a short version of the no-recommendation message for logging.

    Args:
        primary_reason: The primary reason code

    Returns:
        str: Short description of the reason
    """
    reason_descriptions = {
        'no_meals_in_city': 'No meals available in city',
        'budget': 'Budget too restrictive',
        'restaurant_hours': 'No restaurants open',
        'meal_hours': 'No meals available at this time',
        'hated': 'Too many meals disliked',
        'stock': 'All matching meals out of stock',
        'unknown': 'Unknown reason'
    }
    return reason_descriptions.get(primary_reason, f'Reason: {primary_reason}')
