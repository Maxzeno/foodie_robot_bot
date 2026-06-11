"""
Admin configuration for Order model.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from api.models.order import Order, OrderStatus
from api.admin.base import (
    GeoJSONFieldMixin,
    render_point_map_preview,
)


@admin.register(Order)
class OrderAdmin(GeoJSONFieldMixin, admin.ModelAdmin):
    list_display = [
        'code', 'user_link', 'meal_name', 'quantity', 'total_price_display',
        'status_badge', 'paid_badge', 'ordered_via', 'created_at'
    ]
    list_filter = ['status', 'paid', 'ordered_via', 'currency', 'created_at']
    search_fields = ['code', 'user__phone', 'user__code', 'meal__name', 'rider_phone', 'rider_name']
    readonly_fields = [
        'code', 'pickup_point_preview', 'dropoff_point_preview',
        'route_preview', 'created_at', 'updated_at'
    ]
    raw_id_fields = ['user', 'meal']
    ordering = ['-created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'

    geojson_point_fields = ['pickup_point', 'dropoff_point']

    fieldsets = (
        ('Order Info', {
            'fields': ('code', 'user', 'meal', 'quantity', 'status', 'ordered_via')
        }),
        ('Pricing', {
            'fields': ('currency', 'meal_price', 'delivery_fee', 'total_price', 'amount_paid', 'paid')
        }),
        ('Pickup Location', {
            'fields': ('pickup_street_address', 'pickup_point', 'pickup_point_preview'),
            'description': 'Restaurant pickup location'
        }),
        ('Delivery Location', {
            'fields': ('dropoff_street_address', 'dropoff_point', 'dropoff_point_preview'),
            'description': 'Customer delivery location'
        }),
        ('Route Overview', {
            'fields': ('route_preview',),
            'classes': ('collapse',),
            'description': 'Map showing both pickup and dropoff locations'
        }),
        ('Rider Info', {
            'fields': ('rider_name', 'rider_phone', 'rider_company', 'rider_note'),
            'classes': ('collapse',)
        }),
        ('Notes & Timestamps', {
            'fields': ('note', 'delivered_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_dispatched', 'mark_as_arrived', 'mark_as_received', 'mark_as_paid']

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

    def total_price_display(self, obj):
        return f"{obj.currency.symbol}{obj.total_price:,.2f}"
    total_price_display.short_description = 'Total'

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'dispatched': '#17a2b8',
            'arrived': '#6f42c1',
            'received': '#28a745',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def paid_badge(self, obj):
        if obj.paid:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">PAID</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">UNPAID</span>'
        )
    paid_badge.short_description = 'Payment'

    def pickup_point_preview(self, obj):
        return render_point_map_preview(obj.pickup_point, 'pickup', height=250)
    pickup_point_preview.short_description = 'Pickup Map'

    def dropoff_point_preview(self, obj):
        return render_point_map_preview(obj.dropoff_point, 'dropoff', height=250)
    dropoff_point_preview.short_description = 'Dropoff Map'

    def route_preview(self, obj):
        """Render a map showing both pickup and dropoff locations."""
        if not obj.pickup_point and not obj.dropoff_point:
            return format_html(
                '<div style="padding: 20px; background: #f8f9fa; border-radius: 8px; '
                'text-align: center; color: #6c757d;">No locations set</div>'
            )

        pickup_coords = obj.pickup_point.get('coordinates', []) if obj.pickup_point else []
        dropoff_coords = obj.dropoff_point.get('coordinates', []) if obj.dropoff_point else []

        # Calculate center
        all_coords = []
        if len(pickup_coords) >= 2:
            all_coords.append(pickup_coords)
        if len(dropoff_coords) >= 2:
            all_coords.append(dropoff_coords)

        if not all_coords:
            return format_html(
                '<div style="padding: 20px; background: #f8f9fa; border-radius: 8px; '
                'text-align: center; color: #6c757d;">Invalid coordinates</div>'
            )

        center_lng = sum(c[0] for c in all_coords) / len(all_coords)
        center_lat = sum(c[1] for c in all_coords) / len(all_coords)
        map_id = f"route_map_{obj.pk}"

        pickup_js = ""
        dropoff_js = ""
        bounds_js = "var bounds = [];"

        if len(pickup_coords) >= 2:
            pickup_js = f"""
                var pickupMarker = L.marker([{pickup_coords[1]}, {pickup_coords[0]}], {{
                    icon: L.divIcon({{
                        className: 'custom-div-icon',
                        html: '<div style="background: #28a745; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;">PICKUP</div>',
                        iconSize: [70, 30],
                        iconAnchor: [35, 30]
                    }})
                }}).addTo(map);
                bounds.push([{pickup_coords[1]}, {pickup_coords[0]}]);
            """

        if len(dropoff_coords) >= 2:
            dropoff_js = f"""
                var dropoffMarker = L.marker([{dropoff_coords[1]}, {dropoff_coords[0]}], {{
                    icon: L.divIcon({{
                        className: 'custom-div-icon',
                        html: '<div style="background: #dc3545; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;">DROPOFF</div>',
                        iconSize: [70, 30],
                        iconAnchor: [35, 30]
                    }})
                }}).addTo(map);
                bounds.push([{dropoff_coords[1]}, {dropoff_coords[0]}]);
            """

        # Add line between points if both exist
        line_js = ""
        if len(pickup_coords) >= 2 and len(dropoff_coords) >= 2:
            line_js = f"""
                L.polyline([
                    [{pickup_coords[1]}, {pickup_coords[0]}],
                    [{dropoff_coords[1]}, {dropoff_coords[0]}]
                ], {{color: '#007bff', weight: 3, dashArray: '10, 10'}}).addTo(map);
            """

        return format_html('''
            <div style="margin: 10px 0;">
                <div id="{}" style="height: 350px; border-radius: 8px; border: 1px solid #dee2e6;"></div>
                <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
                <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                <script>
                    (function() {{
                        setTimeout(function() {{
                            if (typeof L !== 'undefined') {{
                                var map = L.map('{}').setView([{}, {}], 13);
                                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                                    attribution: '&copy; OpenStreetMap contributors'
                                }}).addTo(map);
                                {}
                                {}
                                {}
                                {}
                                if (bounds.length > 1) {{
                                    map.fitBounds(bounds, {{padding: [50, 50]}});
                                }}
                            }}
                        }}, 100);
                    }})();
                </script>
            </div>
        ''', map_id, map_id, center_lat, center_lng, bounds_js, pickup_js, dropoff_js, line_js)
    route_preview.short_description = 'Route Map (Pickup → Dropoff)'

    @admin.action(description='Mark selected orders as Dispatched')
    def mark_as_dispatched(self, request, queryset):
        queryset.update(status=OrderStatus.DISPATCHED)

    @admin.action(description='Mark selected orders as Arrived')
    def mark_as_arrived(self, request, queryset):
        queryset.update(status=OrderStatus.ARRIVED)

    @admin.action(description='Mark selected orders as Received')
    def mark_as_received(self, request, queryset):
        queryset.update(status=OrderStatus.RECEIVED, delivered_at=timezone.now())

    @admin.action(description='Mark selected orders as Paid')
    def mark_as_paid(self, request, queryset):
        queryset.update(paid=True)
