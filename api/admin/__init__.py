"""
Admin configuration for the API app.

This package organizes admin classes into separate modules for better maintainability:

- base.py: Common utilities, widgets, and mixins (GeoJSON support)
- user.py: User admin
- order.py: Order admin with map previews
- message.py: Message admin
- meal.py: Meal and MealEmbedding admin
- restaurant.py: Restaurant admin with map preview
- location.py: Country, State, City, DeliveryAddress admin with map previews
- recommendation.py: Recommendation and SpecialOccasion admin
- review.py: Review admin
- finance.py: ReferralEarning, UserBalance, Withdrawal admin
- preferences.py: HealthCondition, Allergy, FitnessGoal, PreferredCuisine, MealPreference admin
- settings.py: AppSettings, Currency admin
"""

# Import all admin classes to register them
from api.admin.user import UserAdmin
from api.admin.order import OrderAdmin
from api.admin.message import MessageAdmin
from api.admin.meal import MealAdmin, MealEmbeddingAdmin
from api.admin.restaurant import RestaurantAdmin
from api.admin.location import CountryAdmin, StateAdmin, CityAdmin, DeliveryAddressAdmin
from api.admin.recommendation import RecommendationAdmin, SpecialOccasionAdmin
from api.admin.review import ReviewAdmin
from api.admin.finance import ReferralEarningAdmin, UserBalanceAdmin, WithdrawalAdmin
from api.admin.preferences import (
    HealthConditionAdmin, AllergyAdmin, FitnessGoalAdmin,
    PreferredCuisineAdmin, MealPreferenceAdmin
)
from api.admin.settings import AppSettingsAdmin, CurrencyAdmin

# Export all admin classes
__all__ = [
    'UserAdmin',
    'OrderAdmin',
    'MessageAdmin',
    'MealAdmin',
    'MealEmbeddingAdmin',
    'RestaurantAdmin',
    'CountryAdmin',
    'StateAdmin',
    'CityAdmin',
    'DeliveryAddressAdmin',
    'RecommendationAdmin',
    'SpecialOccasionAdmin',
    'ReviewAdmin',
    'ReferralEarningAdmin',
    'UserBalanceAdmin',
    'WithdrawalAdmin',
    'HealthConditionAdmin',
    'AllergyAdmin',
    'FitnessGoalAdmin',
    'PreferredCuisineAdmin',
    'MealPreferenceAdmin',
    'AppSettingsAdmin',
    'CurrencyAdmin',
]
