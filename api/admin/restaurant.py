"""
Admin configuration for Restaurant model.
"""
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from api.models.restaurant import Restaurant
from api.admin.base import (
    GeoJSONFieldMixin,
    render_point_map_preview,
)


@admin.register(Restaurant)
class RestaurantAdmin(GeoJSONFieldMixin, admin.ModelAdmin):
    list_display = ['name', 'phone', 'address', 'has_location', 'hours_display', 'inactive_badge', 'meal_count']
    list_filter = ['inactive', 'created_at']
    search_fields = ['name', 'phone', 'address', 'email']
    readonly_fields = ['point_preview', 'created_at', 'updated_at']
    ordering = ['name']

    geojson_point_fields = ['point']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'phone', 'address')
        }),
        ('Location (GeoJSON Point)', {
            'fields': ('point', 'point_preview'),
            'description': 'Set the restaurant location as a GeoJSON Point: {"type": "Point", "coordinates": [longitude, latitude]}'
        }),
        ('Contact', {
            'fields': ('email', 'website', 'social'),
            'classes': ('collapse',)
        }),
        ('Business Hours', {
            'fields': ('open_time', 'close_time', 'available_days'),
            'description': 'available_days: ["monday", "tuesday", ...] or empty for all days'
        }),
        ('Status', {
            'fields': ('inactive',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_meal_count=Count('meals', distinct=True))

    def hours_display(self, obj):
        return f"{obj.open_time.strftime('%H:%M')} - {obj.close_time.strftime('%H:%M')}"
    hours_display.short_description = 'Hours'

    def has_location(self, obj):
        try:
            if obj.point:
                coords = obj.point.get('coordinates', [])
                if len(coords) >= 2:
                    lng_str = f"{coords[0]:.4f}"
                    lat_str = f"{coords[1]:.4f}"
                    return format_html(
                        '<span style="background: #28a745; color: white; padding: 3px 8px; '
                        'border-radius: 3px; font-size: 11px;" title="{}, {}">'
                        '{}, {}</span>',
                        coords[0], coords[1], lng_str, lat_str
                    )
        except:
            pass
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">NOT SET</span>'
        )
    has_location.short_description = 'Location'

    def inactive_badge(self, obj):
        if obj.inactive:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">INACTIVE</span>'
            )
        return format_html(
            '<span style="background: #28a745; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">ACTIVE</span>'
        )
    inactive_badge.short_description = 'Status'

    def meal_count(self, obj):
        return obj._meal_count
    meal_count.short_description = 'Meals'
    meal_count.admin_order_field = '_meal_count'

    def point_preview(self, obj):
        return render_point_map_preview(obj.point, 'restaurant', height=300)
    point_preview.short_description = 'Map Preview'
