"""
Admin configuration for Recommendation and SpecialOccasion models.
"""
from django.contrib import admin
from django.utils.html import format_html

from api.models.recommendation import Recommendation
from api.models.special_occasion import SpecialOccasion


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_link', 'meal_name', 'time_of_day', 'choice_option',
        'day', 'sent_badge', 'accepted_badge', 'created_at'
    ]
    list_display_links = ['id', 'meal_name']  # Click ID or Meal to go to detail page
    list_filter = ['time_of_day', 'choice_option', 'sent_to_user', 'accepted', 'day', 'created_at']
    search_fields = ['user__phone', 'user__code', 'meal__name']
    raw_id_fields = ['user', 'meal']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 100
    date_hierarchy = 'day'

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/api/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.phone or obj.user.code
        )
    user_link.short_description = 'User'

    def meal_name(self, obj):
        name = obj.meal.name
        return name[:30] + '...' if len(name) > 30 else name
    meal_name.short_description = 'Meal'

    def sent_badge(self, obj):
        if obj.sent_to_user:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">SENT</span>'
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">PENDING</span>'
        )
    sent_badge.short_description = 'Sent'

    def accepted_badge(self, obj):
        if obj.accepted:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">YES</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">NO</span>'
        )
    accepted_badge.short_description = 'Accepted'


@admin.register(SpecialOccasion)
class SpecialOccasionAdmin(admin.ModelAdmin):
    list_display = ['name', 'date_display', 'boost_weight', 'is_recurring', 'active', 'meal_count', 'city_count']
    list_filter = ['active', 'is_recurring', 'month', 'cities']
    search_fields = ['name', 'description']
    filter_horizontal = ['meals', 'cities']

    fieldsets = (
        ('Occasion Details', {
            'fields': ('name', 'description', 'active')
        }),
        ('Date Configuration', {
            'fields': ('month', 'day', 'year', 'is_recurring'),
            'description': 'Set month (1-12) and day (1-31). Leave year blank for recurring annual occasions.'
        }),
        ('Boost Configuration', {
            'fields': ('boost_weight',),
            'description': 'Higher values = stronger recommendation. Typical: 50.0 for main dishes, 30.0 for sides.'
        }),
        ('Target Configuration', {
            'fields': ('meals', 'cities'),
            'description': 'Select meals to boost. Leave cities empty to apply globally.'
        }),
    )

    def date_display(self, obj):
        if obj.year:
            return f"{obj.month}/{obj.day}/{obj.year}"
        return f"{obj.month}/{obj.day} (yearly)"
    date_display.short_description = 'Date'

    def meal_count(self, obj):
        return obj.meals.count()
    meal_count.short_description = 'Meals'

    def city_count(self, obj):
        count = obj.cities.count()
        return 'Global' if count == 0 else count
    city_count.short_description = 'Cities'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('meals', 'cities')
