"""
Admin configuration for Company model.
"""
from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

from api.models.company import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'contact_info', 'registration_number',
        'rider_count', 'online_riders', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = [
        'name', 'registration_number',
        'user__code', 'user__phone', 'user__email'
    ]
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 50
    autocomplete_fields = ['user']

    fieldsets = (
        ('Company Info', {
            'fields': ('user', 'name', 'registration_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').annotate(
            _rider_count=Count('riders', distinct=True),
            _online_riders=Count('riders', filter=Q(user__is_online=True), distinct=True)
        )

    def contact_info(self, obj):
        contact = obj.user.email or obj.user.phone or obj.user.code
        return format_html(
            '<span style="color: #666; font-size: 11px;">{}</span>',
            contact
        )
    contact_info.short_description = 'Contact'

    def rider_count(self, obj):
        count = obj._rider_count
        if count > 0:
            return format_html(
                '<span style="color: #007bff; font-weight: 500;">{}</span>',
                count
            )
        return format_html('<span style="color: #6c757d;">0</span>')
    rider_count.short_description = 'Total Riders'
    rider_count.admin_order_field = '_rider_count'

    def online_riders(self, obj):
        online = obj._online_riders
        total = obj._rider_count
        if online > 0:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">{} / {}</span>',
                online, total
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">0 / {}</span>',
            total
        )
    online_riders.short_description = 'Online'
    online_riders.admin_order_field = '_online_riders'
