"""
Admin configuration for location models: Country, State, City, DeliveryAddress.
"""
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from api.models.location import Country, State, City
from api.models.address import DeliveryAddress
from api.admin.base import (
    GeoJSONFieldMixin,
    GeoJSONPointWidget,
    GeoJSONPolygonWidget,
    render_point_map_preview,
    render_polygon_map_preview,
    render_geojson_display,
)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'state_count']
    search_fields = ['name', 'code']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_state_count=Count('states', distinct=True))

    def state_count(self, obj):
        return obj._state_count
    state_count.short_description = 'States'


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'city_count']
    list_filter = ['country']
    search_fields = ['name']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_city_count=Count('cities', distinct=True))

    def city_count(self, obj):
        return obj._city_count
    city_count.short_description = 'Cities'


@admin.register(City)
class CityAdmin(GeoJSONFieldMixin, admin.ModelAdmin):
    list_display = ['name', 'state', 'timezone', 'has_boundary', 'user_count', 'meal_count']
    list_filter = ['state', 'timezone']
    search_fields = ['name', 'state__name']
    readonly_fields = ['boundary_preview', 'created_at', 'updated_at']

    geojson_polygon_fields = ['boundary']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'state', 'currency', 'timezone')
        }),
        ('Boundary (GeoJSON Polygon)', {
            'fields': ('boundary', 'boundary_preview'),
            'description': 'Define the city boundary as a GeoJSON Polygon. The boundary is used to determine which city a location belongs to.'
        }),
        ('Settings', {
            'fields': ('preferred_cuisine', 'average_meal_budget', 'referral_bonus', 'delivery_fee_per_km', 'min_delivery_fee'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = ['preferred_cuisine']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _user_count=Count('users', distinct=True),
            _meal_count=Count('meals', distinct=True)
        )

    def user_count(self, obj):
        return obj._user_count
    user_count.short_description = 'Users'

    def meal_count(self, obj):
        return obj._meal_count
    meal_count.short_description = 'Meals'

    def has_boundary(self, obj):
        if obj.boundary:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">SET</span>'
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">NOT SET</span>'
        )
    has_boundary.short_description = 'Boundary'

    def boundary_preview(self, obj):
        return render_polygon_map_preview(obj.boundary, 'city_boundary', height=400)
    boundary_preview.short_description = 'Map Preview'


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(GeoJSONFieldMixin, admin.ModelAdmin):
    list_display = ['user', 'name', 'street_address', 'has_location', 'is_default', 'created_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['user__phone', 'user__code', 'street_address', 'name']
    raw_id_fields = ['user']
    readonly_fields = ['point_preview', 'created_at', 'updated_at']

    geojson_point_fields = ['point']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Address Info', {
            'fields': ('name', 'street_address', 'is_default')
        }),
        ('Location (GeoJSON Point)', {
            'fields': ('point', 'point_preview'),
            'description': 'Set the delivery location as a GeoJSON Point: {"type": "Point", "coordinates": [longitude, latitude]}'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # def user_link(self, obj):
    #     return format_html(
    #         '<a href="/admin/api/user/{}/change/">{}</a>',
    #         obj.user.id,
    #         obj.user.phone or obj.user.code
    #     )
    # user_link.short_description = 'User'

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

    def point_preview(self, obj):
        return render_point_map_preview(obj.point, 'delivery_address', height=300)
    point_preview.short_description = 'Map Preview'
