"""
Admin configuration for User model.
"""
from django import forms
from django.contrib import admin
from django.db.models import Count, Max, Q
from django.utils.html import format_html
from django.utils import timezone

from api.models.user import User
from api.models.message import RoleChoices


class _DEPRECATED_RolesWidget(forms.CheckboxSelectMultiple):
    """Custom widget for displaying roles as styled checkboxes."""

    def __init__(self, *args, **kwargs):
        choices = [(role.value, role.label) for role in UserRole]
        super().__init__(choices=choices, *args, **kwargs)

    def format_value(self, value):
        """Convert JSON array to list for checkbox rendering."""
        if isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                value = []
        return value or []

    def render(self, name, value, attrs=None, renderer=None):
        """Render checkboxes with custom styling."""
        from django.utils.html import format_html
        from django.utils.safestring import mark_safe

        if value is None:
            value = []
        elif isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except:
                value = []

        # Role colors matching the badge display
        role_styles = {
            'customer': 'color: #007bff; font-weight: 500;',
            'rider': 'color: #28a745; font-weight: 500;',
            'company': 'color: #6f42c1; font-weight: 500;',
        }

        html_parts = [
            '<ul style="list-style-type: none; padding-left: 0; margin: 10px 0;">'
        ]

        for role_value, role_label in self.choices:
            is_checked = role_value in value
            checked_attr = 'checked' if is_checked else ''
            style = role_styles.get(role_value, '')

            html_parts.append(f'''
                <li style="margin-bottom: 12px; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid {role_styles.get(role_value, '#6c757d').split(': ')[1].split(';')[0]};">
                    <label style="display: flex; align-items: center; cursor: pointer; {style}">
                        <input type="checkbox" name="{name}" value="{role_value}" {checked_attr}
                               style="margin-right: 10px; width: 18px; height: 18px; cursor: pointer;">
                        <span style="font-size: 14px;">{role_label}</span>
                    </label>
                </li>
            ''')

        html_parts.append('</ul>')

        return mark_safe(''.join(html_parts))


class UserAdminForm(forms.ModelForm):
    """Custom form for User admin."""

    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm

    class Media:
        css = {
            'all': []
        }
        js = []

    list_display = [
        'code', 'phone', 'city', 'user_type_badge', 'referral_info', 'profile_complete_badge',
        'order_count', 'message_count', 'is_active_badge', 'is_blocked_badge', 'created_at'
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
        return qs.select_related('referred_by', 'city').annotate(
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

    def referral_info(self, obj):
        if obj.referred_by:
            return format_html(
                '<span style="color: #007bff; font-weight: 500;">✓ {}</span>',
                obj.referred_by.code or obj.referred_by.phone
            )
        return format_html('<span style="color: #6c757d;">-</span>')
    referral_info.short_description = 'Referred By'

    def profile_complete_badge(self, obj):
        # Check if key profile fields are filled
        required_fields = [
            obj.average_meal_budget,
            obj.fitness_goals,
        ]
        secondary_required_fields = [
            obj.city,
        ]

        required_complete = all(required_fields)
        secondary_required_complete = all(secondary_required_fields)

        if required_complete and secondary_required_complete:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">✓ Complete</span>'
            )
        elif required_complete:
            return format_html(
                '<span style="background: #ffc107; color: black; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">⚠ Partial</span>'
            )
        return format_html(
            '<span style="background: #dc3545; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">✗ Incomplete</span>'
        )
    profile_complete_badge.short_description = 'Profile'

    def user_type_badge(self, obj):
        """Show user type based on model relationships."""
        badges = []

        # Everyone is a customer by default
        badges.append(
            '<span style="background: #007bff; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; margin-right: 3px;">Customer</span>'
        )

        # Check if rider
        if obj.is_rider:
            # Check if company
            if obj.is_company:
                badges.append(
                    '<span style="background: #6f42c1; color: white; padding: 3px 8px; '
                    'border-radius: 3px; font-size: 11px; margin-right: 3px;">Company</span>'
                )
            else:
                badges.append(
                    '<span style="background: #28a745; color: white; padding: 3px 8px; '
                    'border-radius: 3px; font-size: 11px; margin-right: 3px;">Rider</span>'
                )

        return format_html(''.join(badges))
    user_type_badge.short_description = 'Type'
