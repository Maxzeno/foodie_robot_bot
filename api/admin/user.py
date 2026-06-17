"""
Admin configuration for User model.
"""
from django.contrib import admin
from django.db.models import Count, Max, Q
from django.utils.html import format_html
from django.utils import timezone

from api.models.user import User
from api.models.message import RoleChoices


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'phone', 'city', 'order_count',
        'message_count', 'is_active_badge', 'is_blocked_badge', 'created_at'
    ]
    list_filter = ['city', 'gender', 'is_active', 'is_blocked', 'created_at']
    search_fields = ['code', 'phone', 'email', 'username', 'first_name', 'last_name']
    readonly_fields = ['code', 'created_at', 'updated_at', 'last_login', 'date_joined']
    filter_horizontal = ['health_conditions', 'allergies', 'preferred_cuisine', 'groups', 'user_permissions']
    ordering = ['-created_at']
    list_per_page = 50

    fieldsets = (
        ('User Info', {
            'fields': ('code', 'phone', 'email', 'username', 'password', 'first_name', 'last_name')
        }),
        ('Profile', {
            'fields': ('city', 'gender', 'average_meal_budget', 'fitness_goals')
        }),
        ('Health & Preferences', {
            'fields': ('health_conditions', 'allergies', 'preferred_cuisine'),
            'classes': ('collapse',)
        }),
        ('Referral', {
            'fields': ('referred_by',),
            'classes': ('collapse',)
        }),
        ('Status & Permissions', {
            'fields': ('is_active', 'is_blocked', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _order_count=Count('orders', distinct=True),
            _message_count=Count('messages', filter=Q(messages__role=RoleChoices.USER), distinct=True),
            _last_message=Max('messages__created_at', filter=Q(messages__role=RoleChoices.USER))
        )

    def order_count(self, obj):
        return obj._order_count
    order_count.short_description = 'Orders'
    order_count.admin_order_field = '_order_count'

    def message_count(self, obj):
        return obj._message_count
    message_count.short_description = 'Messages'
    message_count.admin_order_field = '_message_count'

    def is_active_badge(self, obj):
        now = timezone.now()
        if hasattr(obj, '_last_message') and obj._last_message:
            hours_ago = (now - obj._last_message).total_seconds() / 3600
            if hours_ago <= 24:
                return format_html(
                    '<span style="background: #28a745; color: white; padding: 3px 8px; '
                    'border-radius: 3px; font-size: 11px;">Active</span>'
                )
            elif hours_ago <= 72:
                return format_html(
                    '<span style="background: #ffc107; color: black; padding: 3px 8px; '
                    'border-radius: 3px; font-size: 11px;">Recent</span>'
                )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">Inactive</span>'
        )
    is_active_badge.short_description = 'Activity'

    def is_blocked_badge(self, obj):
        if obj.is_blocked:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">BLOCKED</span>'
            )
        return ''
    is_blocked_badge.short_description = 'Blocked'
