"""
Admin configuration for location models: Country, State, City, DeliveryAddress.
"""
import math
from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from api.models.location import Country, State, City
from api.models.address import DeliveryAddress, NonReachedArea
from api.admin.base import (
    GeoJSONFieldMixin,
    GeoJSONPointWidget,
    GeoJSONPolygonWidget,
    render_point_map_preview,
    render_polygon_map_preview,
    render_geojson_display,
)


def _haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers using Haversine formula."""
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def _calculate_polygon_area_km2(coordinates):
    """
    Calculate the area of a polygon in km² using the Shoelace formula
    with latitude correction for spherical coordinates.
    """
    if not coordinates or len(coordinates) < 3:
        return 0

    # Get the centroid latitude for area correction
    lats = [coord[1] for coord in coordinates]
    avg_lat = sum(lats) / len(lats)

    # Conversion factors at the average latitude
    # 1 degree latitude ≈ 111 km
    # 1 degree longitude ≈ 111 * cos(latitude) km
    km_per_deg_lat = 111.0
    km_per_deg_lon = 111.0 * math.cos(math.radians(avg_lat))

    # Convert coordinates to km from an arbitrary origin
    coords_km = []
    for coord in coordinates:
        x_km = coord[0] * km_per_deg_lon
        y_km = coord[1] * km_per_deg_lat
        coords_km.append((x_km, y_km))

    # Shoelace formula
    n = len(coords_km)
    area = 0
    for i in range(n):
        j = (i + 1) % n
        area += coords_km[i][0] * coords_km[j][1]
        area -= coords_km[j][0] * coords_km[i][1]

    return abs(area) / 2


def _calculate_boundary_stats(boundary):
    """Calculate farthest distance and area for a GeoJSON polygon boundary."""
    if not boundary or not isinstance(boundary, dict):
        return None, None

    coords = boundary.get('coordinates', [])
    if not coords or not coords[0]:
        return None, None

    # Get outer ring coordinates (first array in polygon)
    outer_ring = coords[0]
    if len(outer_ring) < 3:
        return None, None

    # Calculate max distance (farthest points)
    max_distance = 0
    for i, coord1 in enumerate(outer_ring):
        for coord2 in outer_ring[i + 1:]:
            # coord format is [longitude, latitude]
            dist = _haversine_distance(coord1[1], coord1[0], coord2[1], coord2[0])
            if dist > max_distance:
                max_distance = dist

    # Calculate area
    area = _calculate_polygon_area_km2(outer_ring)

    return max_distance, area


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
    readonly_fields = ['boundary_preview', 'boundary_info', 'created_at', 'updated_at']

    geojson_polygon_fields = ['boundary']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'state', 'currency', 'timezone')
        }),
        ('Boundary (GeoJSON Polygon)', {
            'fields': ('boundary', 'boundary_info', 'boundary_preview'),
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

    def boundary_info(self, obj):
        """Display boundary statistics: farthest distance and total area."""
        try:
            if not obj.boundary:
                return format_html(
                    '<span style="color: #6c757d;">No boundary set</span>'
                )

            # Check if boundary has the expected structure
            if not isinstance(obj.boundary, dict):
                return format_html(
                    '<span style="color: #dc3545;">Invalid boundary format (not a dict)</span>'
                )

            boundary_type = obj.boundary.get('type', '')
            coords = obj.boundary.get('coordinates', [])

            if boundary_type != 'Polygon' or not coords:
                return format_html(
                    '<span style="color: #dc3545;">Invalid boundary: type={}, coords_len={}</span>',
                    boundary_type, len(coords) if coords else 0
                )

            max_distance, area = _calculate_boundary_stats(obj.boundary)

            if max_distance is None or area is None:
                return format_html(
                    '<span style="color: #dc3545;">Could not calculate boundary stats</span>'
                )

            # Format numbers first, then use format_html
            distance_str = f"{float(max_distance):.2f}"
            area_str = f"{float(area):.2f}"

            return format_html(
                '<div style="background: #f8f9fa; padding: 12px; border-radius: 8px; border: 1px solid #dee2e6;">'
                '<div style="margin-bottom: 8px;">'
                '<strong style="color: #495057;">📏 Farthest Distance:</strong> '
                '<span style="color: #28a745; font-weight: bold;">{} km</span>'
                '</div>'
                '<div>'
                '<strong style="color: #495057;">📐 Total Area:</strong> '
                '<span style="color: #007bff; font-weight: bold;">{} km²</span>'
                '</div>'
                '</div>',
                distance_str, area_str
            )
        except Exception as e:
            return format_html(
                '<span style="color: #dc3545;">Error: {}</span>',
                str(e)
            )
    boundary_info.short_description = 'Boundary Statistics'

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


@admin.register(NonReachedArea)
class NonReachedAreaAdmin(GeoJSONFieldMixin, admin.ModelAdmin):
    list_display = ['user', 'name', 'street_address', 'has_location', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__phone', 'user__code', 'street_address', 'name']
    raw_id_fields = ['user']
    readonly_fields = ['point_preview', 'created_at', 'updated_at']

    geojson_point_fields = ['point']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Address Info', {
            'fields': ('name', 'street_address')
        }),
        ('Location (GeoJSON Point)', {
            'fields': ('point', 'point_preview'),
            'description': 'Set the location as a GeoJSON Point: {"type": "Point", "coordinates": [longitude, latitude]}'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

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
        return render_point_map_preview(obj.point, 'non_reached_area', height=300)
    point_preview.short_description = 'Map Preview'
