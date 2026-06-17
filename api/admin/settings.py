"""
Admin configuration for settings-related models:
AppSettings, Currency.
"""
from django.contrib import admin
from django.db.models import Count

from api.models.settings import AppSettings
from api.models.currency import Currency


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'whatsapp_phone_number', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('General', {
            'fields': ('whatsapp_phone_number', 'whatsapp_support_phone_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # Only allow one AppSettings instance
        if AppSettings.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'symbol', 'active_badge', 'city_count']
    list_filter = ['active']
    search_fields = ['name', 'code']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_city_count=Count('cities', distinct=True))

    def active_badge(self, obj):
        if obj.active:
            return '✓'
        return '✗'
    active_badge.short_description = 'Active'

    def city_count(self, obj):
        return obj._city_count
    city_count.short_description = 'Cities'
