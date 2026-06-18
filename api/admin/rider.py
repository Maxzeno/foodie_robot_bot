"""
Admin configuration for Rider model.
"""
from django.contrib import admin
from django.utils.html import format_html

from api.models.rider import Rider


@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = [
        'rider_info', 'company_info', 'online_badge',
        'verified_badge', 'created_at'
    ]
    list_filter = ['company', 'created_at']
    search_fields = [
        'user__code', 'user__phone', 'user__email',
        'user__first_name', 'user__last_name', 'company__name'
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 50
    autocomplete_fields = ['user', 'company']

    fieldsets = (
        ('Rider Info', {
            'fields': ('user', 'company')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'company', 'company__user')

    def rider_info(self, obj):
        name = f"{obj.user.first_name or ''} {obj.user.last_name or ''}".strip()
        contact = obj.user.email or obj.user.phone or obj.user.code
        if name:
            return format_html(
                '<strong>{}</strong><br><span style="color: #666; font-size: 11px;">{}</span>',
                name, contact
            )
        return format_html('<strong>{}</strong>', contact)
    rider_info.short_description = 'Rider'

    def company_info(self, obj):
        if obj.company:
            return format_html(
                '<span style="color: #007bff;">{}</span>',
                obj.company.name
            )
        return format_html(
            '<span style="color: #6c757d; font-style: italic;">Independent</span>'
        )
    company_info.short_description = 'Company'

    def online_badge(self, obj):
        if obj.user.is_online:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">● Online</span>'
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">○ Offline</span>'
        )
    online_badge.short_description = 'Status'

    def verified_badge(self, obj):
        if obj.user.is_verified:
            return format_html(
                '<span style="background: #17a2b8; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">✓ Verified</span>'
            )
        return format_html(
            '<span style="background: #ffc107; color: black; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">⚠ Unverified</span>'
        )
    verified_badge.short_description = 'Verification'
