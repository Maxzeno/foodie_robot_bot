"""
Admin configuration for finance-related models:
ReferralEarning, UserBalance, Withdrawal.
"""
from django.contrib import admin
from django.utils.html import format_html

from api.models.referral_earning import ReferralEarning
from api.models.user_balance import UserBalance
from api.models.withdrawal import Withdrawal


@admin.register(ReferralEarning)
class ReferralEarningAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'referred_user_link', 'amount_display', 'city', 'created_at']
    list_filter = ['currency', 'city', 'created_at']
    search_fields = ['user__phone', 'user__code', 'referred_user__phone', 'referred_user__code']
    raw_id_fields = ['user', 'referred_user']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/api/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.phone or obj.user.code
        )
    user_link.short_description = 'Referrer'

    def referred_user_link(self, obj):
        if obj.referred_user:
            return format_html(
                '<a href="/admin/api/user/{}/change/">{}</a>',
                obj.referred_user.id,
                obj.referred_user.phone or obj.referred_user.code
            )
        return '-'
    referred_user_link.short_description = 'Referred User'

    def amount_display(self, obj):
        return f"{obj.currency.symbol}{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_link', 'amount_display', 'currency', 'updated_at']
    list_filter = ['currency', 'updated_at']
    search_fields = ['user__phone', 'user__code']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/api/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.phone or obj.user.code
        )
    user_link.short_description = 'User'

    def amount_display(self, obj):
        return f"{obj.currency.symbol}{obj.amount:,.2f}"
    amount_display.short_description = 'Balance'


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'amount_display', 'status_badge', 'bank_info', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['user__phone', 'user__code', 'account_name', 'account_number']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Amount', {
            'fields': ('currency', 'amount')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_name', 'account_number')
        }),
        ('Status', {
            'fields': ('status', 'rejection_reason', 'payment_reference', 'processed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        return format_html(
            '<a href="/admin/api/user/{}/change/">{}</a>',
            obj.user.id,
            obj.user.phone or obj.user.code
        )
    user_link.short_description = 'User'

    def amount_display(self, obj):
        if hasattr(obj, 'currency') and obj.currency:
            return f"{obj.currency.symbol}{obj.amount:,.2f}"
        return f"{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'

    def bank_info(self, obj):
        return f"{obj.bank_name} - {obj.account_number}"
    bank_info.short_description = 'Bank'

    def status_badge(self, obj):
        if hasattr(obj, 'status'):
            colors = {
                'pending': '#ffc107',
                'approved': '#28a745',
                'rejected': '#dc3545'
            }
            text_color = 'black' if obj.status == 'pending' else 'white'
            return format_html(
                '<span style="background: {}; color: {}; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">{}</span>',
                colors.get(obj.status, '#6c757d'),
                text_color,
                obj.status.upper()
            )
        return '-'
    status_badge.short_description = 'Status'
