"""
Admin configuration for Order model.
"""
import math
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from api.models.order import Order, OrderStatus
from api.admin.base import GeoJSONFieldMixin


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


@admin.register(Order)
class OrderAdmin(GeoJSONFieldMixin, admin.ModelAdmin):
    list_display = [
        'code', 'user_link', 'meal_name', 'quantity', 'total_price_display',
        'status_badge', 'paid_badge', 'ordered_via', 'created_at'
    ]
    list_filter = ['status', 'paid', 'ordered_via', 'currency', 'created_at']
    search_fields = ['code', 'user__phone', 'user__code', 'meal__name', 'rider_phone', 'rider_name']
    readonly_fields = [
        'code', 'order_summary_message', 'delivery_distance', 'pickup_point_preview', 'dropoff_point_preview',
        'route_preview', 'created_at', 'updated_at'
    ]
    # raw_id_fields = ['user', 'meal']
    ordering = ['-created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'

    geojson_point_fields = ['pickup_point', 'dropoff_point']

    fieldsets = (
        ('Order Summary', {
            'fields': ('order_summary_message',),
            'description': 'Quick order overview with locations and pricing'
        }),
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
            'fields': ('delivery_distance', 'route_preview'),
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

    actions = ['mark_as_accepted', 'mark_as_at_restaurant', 'mark_as_on_the_way', 'mark_as_delivered', 'mark_as_paid']

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

    def _get_coords(self, point):
        """Extract (lng, lat) from a GeoJSON point."""
        if point and isinstance(point, dict):
            coords = point.get('coordinates', [])
            if len(coords) >= 2:
                return coords[0], coords[1]
        return None, None

    def _render_point_with_gmaps(self, point, label, color):
        """Render a point preview with Google Maps link."""
        lng, lat = self._get_coords(point)
        if lng is None or lat is None:
            return format_html(
                '<div style="padding: 20px; background: #f8f9fa; border-radius: 8px; '
                'text-align: center; color: #6c757d;">No {} location set</div>',
                label.lower()
            )

        gmaps_url = f"https://www.google.com/maps?q={lat},{lng}"
        return format_html('''
            <div style="margin: 10px 0;">
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span style="background: {}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 12px;">{}</span>
                        <span style="font-family: monospace; color: #666;">{:.6f}, {:.6f}</span>
                    </div>
                    <a href="{}" target="_blank"
                       style="display: inline-flex; align-items: center; gap: 8px; padding: 10px 16px;
                              background: #4285f4; color: white; text-decoration: none; border-radius: 6px;
                              font-weight: 500; transition: background 0.2s;"
                       onmouseover="this.style.background='#3367d6'"
                       onmouseout="this.style.background='#4285f4'">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
                        </svg>
                        View on Google Maps
                    </a>
                </div>
            </div>
        ''', color, label, lat, lng, gmaps_url)

    def pickup_point_preview(self, obj):
        return self._render_point_with_gmaps(obj.pickup_point, 'PICKUP', '#28a745')
    pickup_point_preview.short_description = 'Pickup Location'

    def dropoff_point_preview(self, obj):
        return self._render_point_with_gmaps(obj.dropoff_point, 'DROPOFF', '#dc3545')
    dropoff_point_preview.short_description = 'Dropoff Location'

    def delivery_distance(self, obj):
        """Calculate and display the distance from pickup to dropoff in km."""
        pickup_lng, pickup_lat = self._get_coords(obj.pickup_point)
        dropoff_lng, dropoff_lat = self._get_coords(obj.dropoff_point)

        if pickup_lat is None or dropoff_lat is None:
            return format_html(
                '<span style="color: #6c757d;">Cannot calculate - missing location(s)</span>'
            )

        try:
            distance = _haversine_distance(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
            distance_str = f"{distance:.2f}"

            return format_html(
                '<div style="background: #e3f2fd; padding: 12px 16px; border-radius: 8px; '
                'border: 1px solid #90caf9; display: inline-block;">'
                '<span style="color: #1565c0; font-weight: bold; font-size: 18px;">{} km</span>'
                '<span style="color: #64b5f6; margin-left: 8px; font-size: 13px;">(straight line)</span>'
                '</div>',
                distance_str
            )
        except Exception as e:
            return format_html(
                '<span style="color: #dc3545;">Error calculating distance: {}</span>',
                str(e)
            )
    delivery_distance.short_description = 'Delivery Distance'

    def order_summary_message(self, obj: Order):
        """Generate a formatted message with order details for easy sharing."""
        pickup_lng, pickup_lat = self._get_coords(obj.pickup_point)
        dropoff_lng, dropoff_lat = self._get_coords(obj.dropoff_point)

        # Build the message lines
        message_lines = []
        message_lines.append(f"Hi we have a delivery (buy \"{obj.meal.name}\" at {obj.meal.restaurant.name}) \n")

        # Pickup line
        if pickup_lat is not None and pickup_lng is not None:
            pickup_gmaps = f"https://www.google.com/maps?q={pickup_lat},{pickup_lng}"
            pickup_address = obj.pickup_street_address or "Address not set"
            message_lines.append(f"Pickup meal at {obj.meal.restaurant.name} ({pickup_address} - {pickup_gmaps}) \n")
        else:
            message_lines.append(f"Pickup meal at {obj.meal.restaurant.name} ({obj.pickup_street_address or 'Address not set'}) \n")

        # Note for vendor (if set)
        if obj.note and obj.note.strip():
            message_lines.append(f"Note for vendor: {obj.note.strip()} \n")

        # Dropoff line
        if dropoff_lat is not None and dropoff_lng is not None:
            dropoff_gmaps = f"https://www.google.com/maps?q={dropoff_lat},{dropoff_lng}"
            dropoff_address = obj.dropoff_street_address or "Address not set"
            message_lines.append(f"Deliver to our client ({dropoff_address} - {dropoff_gmaps}) \n")
        else:
            message_lines.append(f"Deliver to our client ({obj.dropoff_street_address or 'Address not set'}) \n")

        # Client phone number
        client_phone = obj.user.phone or "Not available"
        message_lines.append(f"Client phone: {client_phone} \n")

        # Rider note (if set)
        if obj.rider_note and obj.rider_note.strip():
            message_lines.append(f"Rider instructions: {obj.rider_note.strip()} \n")

        # Cost line
        message_lines.append(f"How much will this cost?")

        # Join lines
        message_text = "\n".join(message_lines)

        if obj.paid == False:
            message_text = "Payment pending."

        elif obj.status != OrderStatus.PENDING:
            message_text = f"Order {obj.status}."

        # Create HTML display with copy functionality
        message_id = f"order-message-{obj.id or 'new'}"
        return format_html('''
            <div style="margin: 10px 0;">
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6;">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                        <h3 style="margin: 0; color: #333; font-size: 16px; font-weight: 600;">Order Summary Message</h3>
                        <button type="button" onclick="copyOrderMessage('{}', this)"
                                style="padding: 6px 14px; background: #28a745; color: white; border: none;
                                       border-radius: 5px; cursor: pointer; font-size: 13px; font-weight: 500;"
                                onmouseover="this.style.background='#218838'"
                                onmouseout="this.style.background='#28a745'">
                            Copy Message
                        </button>
                    </div>
                    <pre id="{}" style="background: white; padding: 15px; border-radius: 6px;
                              border: 1px solid #dee2e6; font-family: 'Segoe UI', Arial, sans-serif;
                              font-size: 14px; line-height: 1.6; margin: 0; white-space: pre-wrap;
                              word-wrap: break-word; color: #333;">{}</pre>
                </div>
            </div>
            <script>
                function copyOrderMessage(elementId, button) {{
                    const element = document.getElementById(elementId);
                    const text = element.textContent;
                    navigator.clipboard.writeText(text).then(() => {{
                        const originalText = button.textContent;
                        button.textContent = 'Copied!';
                        setTimeout(() => {{
                            button.textContent = originalText;
                        }}, 2000);
                    }}).catch(err => {{
                        alert('Failed to copy: ' + err);
                    }});
                }}
            </script>
        ''', message_id, message_id, message_text)
    order_summary_message.short_description = 'Order Summary Message'

    def route_preview(self, obj):
        """Render Google Maps directions link for the route."""
        pickup_lng, pickup_lat = self._get_coords(obj.pickup_point)
        dropoff_lng, dropoff_lat = self._get_coords(obj.dropoff_point)

        if pickup_lng is None and dropoff_lng is None:
            return format_html(
                '<div style="padding: 20px; background: #f8f9fa; border-radius: 8px; '
                'text-align: center; color: #6c757d;">No locations set</div>'
            )

        # Build the route info display
        html_parts = ['<div style="margin: 10px 0;">']

        # Location summary
        html_parts.append('<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6;">')

        if pickup_lat is not None:
            html_parts.append(f'''
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                    <span style="background: #28a745; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 12px;">PICKUP</span>
                    <span style="font-family: monospace; color: #666;">{pickup_lat:.6f}, {pickup_lng:.6f}</span>
                    <a href="https://www.google.com/maps?q={pickup_lat},{pickup_lng}" target="_blank" style="color: #4285f4; font-size: 12px;">View</a>
                </div>
            ''')

        if dropoff_lat is not None:
            html_parts.append(f'''
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                    <span style="background: #dc3545; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 12px;">DROPOFF</span>
                    <span style="font-family: monospace; color: #666;">{dropoff_lat:.6f}, {dropoff_lng:.6f}</span>
                    <a href="https://www.google.com/maps?q={dropoff_lat},{dropoff_lng}" target="_blank" style="color: #4285f4; font-size: 12px;">View</a>
                </div>
            ''')

        # Google Maps directions link (only if both points exist)
        if pickup_lat is not None and dropoff_lat is not None:
            directions_url = f"https://www.google.com/maps/dir/{pickup_lat},{pickup_lng}/{dropoff_lat},{dropoff_lng}"
            html_parts.append(f'''
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
                    <a href="{directions_url}" target="_blank"
                       style="display: inline-flex; align-items: center; gap: 8px; padding: 12px 20px;
                              background: #4285f4; color: white; text-decoration: none; border-radius: 6px;
                              font-weight: 500; transition: background 0.2s;"
                       onmouseover="this.style.background='#3367d6'"
                       onmouseout="this.style.background='#4285f4'">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M21.71 11.29l-9-9c-.39-.39-1.02-.39-1.41 0l-9 9c-.39.39-.39 1.02 0 1.41l9 9c.39.39 1.02.39 1.41 0l9-9c.39-.38.39-1.01 0-1.41zM14 14.5V12h-4v3H8v-4c0-.55.45-1 1-1h5V7.5l3.5 3.5-3.5 3.5z"/>
                        </svg>
                        Get Directions on Google Maps
                    </a>
                </div>
            ''')

        html_parts.append('</div></div>')

        return format_html(''.join(html_parts))
    route_preview.short_description = 'Route (Pickup → Dropoff)'

    @admin.action(description='Mark selected orders as Accepted')
    def mark_as_accepted(self, request, queryset):
        queryset.update(status=OrderStatus.ACCEPTED)

    @admin.action(description='Mark selected orders as At Restaurant')
    def mark_as_at_restaurant(self, request, queryset):
        queryset.update(status=OrderStatus.AT_RESTAURANT)

    @admin.action(description='Mark selected orders as On The Way')
    def mark_as_on_the_way(self, request, queryset):
        queryset.update(status=OrderStatus.ON_THE_WAY)

    @admin.action(description='Mark selected orders as Delivered')
    def mark_as_delivered(self, request, queryset):
        queryset.update(status=OrderStatus.DELIVERED, delivered_at=timezone.now())

    @admin.action(description='Mark selected orders as Paid')
    def mark_as_paid(self, request, queryset):
        queryset.update(paid=True)
