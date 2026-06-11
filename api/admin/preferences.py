"""
Admin configuration for preference/diet-related models:
HealthCondition, Allergy, FitnessGoal, PreferredCuisine, MealPreference.
"""
from django.contrib import admin
from django.utils.html import format_html

from api.models.meal import HealthCondition, Allergy, FitnessGoal, PreferredCuisine
from api.models.meal_preference import MealPreference


@admin.register(HealthCondition)
class HealthConditionAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'user_count']
    search_fields = ['name']

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = 'Users'


@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'user_count']
    search_fields = ['name']

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = 'Users'


@admin.register(FitnessGoal)
class FitnessGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'user_count', 'meal_count']
    search_fields = ['name']

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = 'Users'

    def meal_count(self, obj):
        return obj.meals.count()
    meal_count.short_description = 'Meals'


@admin.register(PreferredCuisine)
class PreferredCuisineAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'user_count', 'meal_count']
    search_fields = ['name']

    def user_count(self, obj):
        return obj.user.count()
    user_count.short_description = 'Users'

    def meal_count(self, obj):
        return obj.meals.count()
    meal_count.short_description = 'Meals'


@admin.register(MealPreference)
class MealPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'meal_name', 'preference_badge', 'created_at']
    list_filter = ['preference', 'created_at']
    search_fields = ['user__phone', 'user__code', 'meal__name']
    raw_id_fields = ['user', 'meal']

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/api/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.phone or obj.user.code
        )
    user_link.short_description = 'User'

    def meal_name(self, obj):
        return obj.meal.name
    meal_name.short_description = 'Meal'

    def preference_badge(self, obj):
        colors = {
            'like': '#28a745',
            'neutral': '#6c757d',
            'hate': '#dc3545'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.preference, '#6c757d'),
            obj.preference.upper()
        )
    preference_badge.short_description = 'Preference'
