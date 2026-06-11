"""
Admin configuration for Message model.
"""
from django.contrib import admin
from django.utils.html import format_html

from api.models.message import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['short_content', 'user_link', 'role_badge', 'intent_badge', 'created_at']
    list_filter = ['role', 'current_intent', 'created_at']
    search_fields = ['content', 'user__phone', 'user__code', 'message_id']
    readonly_fields = ['message_id', 'resp', 'metadata', 'created_at', 'updated_at']
    raw_id_fields = ['user', 'reply_to']
    ordering = ['-created_at']
    list_per_page = 100
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Message', {
            'fields': ('message_id', 'user', 'role', 'content', 'current_intent')
        }),
        ('Reply & Media', {
            'fields': ('reply_to', 'preview_media'),
            'classes': ('collapse',)
        }),
        ('Raw Data', {
            'fields': ('resp', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def short_content(self, obj):
        if obj.content:
            return obj.content[:60] + '...' if len(obj.content) > 60 else obj.content
        return '-'
    short_content.short_description = 'Content'

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/api/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.phone or obj.user.code
        )
    user_link.short_description = 'User'

    def role_badge(self, obj):
        if obj.role == 'user':
            return format_html(
                '<span style="background: #17a2b8; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">USER</span>'
            )
        return format_html(
            '<span style="background: #6f42c1; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">BOT</span>'
        )
    role_badge.short_description = 'Role'

    def intent_badge(self, obj):
        if not obj.current_intent or obj.current_intent == 'no_intent':
            return '-'
        colors = {
            'needs_reply': '#ffc107',
            'reminder_message': '#17a2b8',
            'flow_message': '#6f42c1',
            'completed_reply': '#28a745',
        }
        color = colors.get(obj.current_intent, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.current_intent.replace('_', ' ').title()
        )
    intent_badge.short_description = 'Intent'
