"""
Admin configuration for Review model.
"""
from django.contrib import admin
from django.utils.html import format_html

from api.models.review import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id_link', 'user_link', 'order_link', 'rating_display', 'sentiment_badge', 'short_comment', 'created_at']
    list_display_links = ['id_link']
    list_filter = ['meal_rating', 'sentiment', 'created_at']
    search_fields = ['user__phone', 'user__code', 'order__code', 'comment']
    raw_id_fields = ['user', 'order']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 50

    def id_link(self, obj):
        """Clickable ID to review detail page."""
        return f"#{obj.id}"
    id_link.short_description = 'ID'

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/api/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.phone or obj.user.code
        )
    user_link.short_description = 'User'

    def order_link(self, obj):
        return format_html(
            '<a href="/admin/api/order/{}/change/">{}</a>',
            obj.order.id,
            obj.order.code
        )
    order_link.short_description = 'Order'

    def rating_display(self, obj):
        """Display rating as stars."""
        if obj.meal_rating:
            # Use actual star characters
            filled = '⭐' * obj.meal_rating
            empty = '☆' * (5 - obj.meal_rating)
            return format_html(
                '<span style="font-size: 16px; letter-spacing: 2px;">{}{}</span> <small style="color: #6c757d;">({})</small>',
                filled, empty, obj.meal_rating
            )
        return '-'
    rating_display.short_description = 'Rating'
    rating_display.admin_order_field = 'meal_rating'

    def sentiment_badge(self, obj):
        if not obj.sentiment:
            return '-'
        colors = {
            'like': '#28a745',
            'neutral': '#6c757d',
            'hate': '#dc3545'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.sentiment, '#6c757d'),
            obj.sentiment.upper()
        )
    sentiment_badge.short_description = 'Sentiment'

    def short_comment(self, obj):
        if obj.comment:
            return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
        return '-'
    short_comment.short_description = 'Comment'
