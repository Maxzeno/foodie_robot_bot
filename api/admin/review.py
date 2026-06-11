"""
Admin configuration for Review model.
"""
from django.contrib import admin
from django.utils.html import format_html

from api.models.review import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'order_code', 'rating_stars', 'sentiment_badge', 'short_comment', 'created_at']
    list_filter = ['meal_rating', 'sentiment', 'created_at']
    search_fields = ['user__phone', 'user__code', 'order__code', 'comment']
    raw_id_fields = ['user', 'order']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 50

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/api/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.phone or obj.user.code
        )
    user_link.short_description = 'User'

    def order_code(self, obj):
        return format_html(
            '<a href="/admin/api/order/{}/change/">{}</a>',
            obj.order.id,
            obj.order.code
        )
    order_code.short_description = 'Order'

    def rating_stars(self, obj):
        if obj.meal_rating:
            filled = '<span style="color: #ffc107;">&#9733;</span>' * obj.meal_rating
            empty = '<span style="color: #dee2e6;">&#9733;</span>' * (5 - obj.meal_rating)
            return format_html('{}{} <small>({})</small>', filled, empty, obj.meal_rating)
        return '-'
    rating_stars.short_description = 'Rating'

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
