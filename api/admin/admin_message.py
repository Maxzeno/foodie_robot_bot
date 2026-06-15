from django.contrib import admin
from django.utils.html import format_html
from django.db import transaction
from api.models.admin_message import BroadcastMessage, SingleUserMessage, MessageStatusChoices


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'content_preview', 'cities_display', 'status_badge',
        'sent_count', 'failed_count', 'total_eligible', 'created_at'
    ]
    list_filter = ['status', 'cities', 'created_at']
    search_fields = ['content']
    filter_horizontal = ['cities']
    readonly_fields = [
        'status', 'sent_count', 'failed_count', 'total_eligible',
        'error_message', 'sent_at', 'completed_at', 'eligible_users_preview'
    ]

    fieldsets = (
        ('Message', {
            'fields': ('content', 'image_url', 'cities')
        }),
        ('Status & Results', {
            'fields': (
                'status', 'sent_count', 'failed_count', 'total_eligible',
                'error_message', 'sent_at', 'completed_at'
            ),
            'classes': ('collapse',)
        }),
        ('Preview', {
            'fields': ('eligible_users_preview',),
            'classes': ('collapse',)
        }),
    )

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"

    def cities_display(self, obj):
        cities = list(obj.cities.values_list('name', flat=True)[:3])
        if obj.cities.count() > 3:
            cities.append(f"+{obj.cities.count() - 3} more")
        return ", ".join(cities) if cities else "All Cities"
    cities_display.short_description = "Cities"

    def status_badge(self, obj):
        colors = {
            MessageStatusChoices.PENDING: '#6c757d',
            MessageStatusChoices.SENDING: '#007bff',
            MessageStatusChoices.COMPLETED: '#28a745',
            MessageStatusChoices.FAILED: '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def eligible_users_preview(self, obj):
        if obj.pk:
            users = obj.get_eligible_users()[:20]
            count = obj.get_eligible_users().count()
            if count == 0:
                return "No eligible users found (users must be active within last 24 hours)"

            user_list = "<br>".join([
                f"- {u.code} ({u.phone}) - {u.city.name if u.city else 'No city'}"
                for u in users
            ])
            if count > 20:
                user_list += f"<br>... and {count - 20} more users"

            return format_html(
                '<strong>Total eligible: {}</strong><br><br>{}',
                count, user_list
            )
        return "Save to see eligible users preview"
    eligible_users_preview.short_description = "Eligible Users Preview"

    def save_model(self, request, obj, form, change):
        # Only send if this is a new message (not an update)
        is_new = obj.pk is None

        super().save_model(request, obj, form, change)

        if is_new and obj.status == MessageStatusChoices.PENDING:
            # Queue the task to send the broadcast
            from api.tasks.send_admin_message import send_broadcast_message_task
            transaction.on_commit(lambda: send_broadcast_message_task(obj.id))
            self.message_user(
                request,
                f"Broadcast message queued for sending to eligible users in selected cities."
            )

    def has_change_permission(self, request, obj=None):
        # Don't allow editing after sending has started
        if obj and obj.status != MessageStatusChoices.PENDING:
            return False
        return super().has_change_permission(request, obj)


@admin.register(SingleUserMessage)
class SingleUserMessageAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_display', 'content_preview', 'status_badge',
        'user_active_status', 'created_at', 'sent_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['content', 'user__code', 'user__phone']
    raw_id_fields = ['user']
    readonly_fields = ['status', 'error_message', 'sent_at', 'user_activity_info']

    fieldsets = (
        ('Message', {
            'fields': ('user', 'content', 'image_url')
        }),
        ('User Activity', {
            'fields': ('user_activity_info',),
        }),
        ('Status & Results', {
            'fields': ('status', 'error_message', 'sent_at'),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj):
        return f"{obj.user.code} ({obj.user.phone})"
    user_display.short_description = "User"

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"

    def status_badge(self, obj):
        colors = {
            MessageStatusChoices.PENDING: '#6c757d',
            MessageStatusChoices.SENDING: '#007bff',
            MessageStatusChoices.COMPLETED: '#28a745',
            MessageStatusChoices.FAILED: '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def user_active_status(self, obj):
        is_active = obj.is_user_active()
        if is_active:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">Active</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">Inactive</span>'
        )
    user_active_status.short_description = "24h Window"

    def user_activity_info(self, obj):
        if not obj.pk or not obj.user:
            return "Select a user to see activity info"

        from api.models.message import Message, RoleChoices
        from django.utils import timezone
        from datetime import timedelta

        last_message = Message.objects.filter(
            user=obj.user,
            role=RoleChoices.USER
        ).order_by('-created_at').first()

        if not last_message:
            return format_html(
                '<span style="color: #dc3545;">User has never sent a message. '
                'Cannot send free message.</span>'
            )

        now = timezone.now()
        time_diff = now - last_message.created_at
        hours_ago = time_diff.total_seconds() / 3600

        is_active = hours_ago <= 24

        if is_active:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">'
                'User is ACTIVE (last message: {:.1f} hours ago)<br>'
                'Free message window: {:.1f} hours remaining</span>',
                hours_ago, 24 - hours_ago
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">'
                'User is INACTIVE (last message: {:.1f} hours ago)<br>'
                'Cannot send free message - user outside 24-hour window</span>',
                hours_ago
            )
    user_activity_info.short_description = "User Activity Status"

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None

        super().save_model(request, obj, form, change)

        if is_new and obj.status == MessageStatusChoices.PENDING:
            # Check if user is active before queuing
            if not obj.is_user_active():
                obj.status = MessageStatusChoices.FAILED
                obj.error_message = "User is not within the 24-hour free service window"
                obj.save(update_fields=['status', 'error_message'])
                self.message_user(
                    request,
                    f"Message NOT sent: User {obj.user.code} is not active (outside 24-hour window).",
                    level='error'
                )
                return

            # Queue the task to send the message
            from api.tasks.send_admin_message import send_single_user_message_task
            transaction.on_commit(lambda: send_single_user_message_task(obj.id))
            self.message_user(
                request,
                f"Message queued for sending to user {obj.user.code}."
            )

    def has_change_permission(self, request, obj=None):
        # Don't allow editing after sending has started
        if obj and obj.status != MessageStatusChoices.PENDING:
            return False
        return super().has_change_permission(request, obj)
