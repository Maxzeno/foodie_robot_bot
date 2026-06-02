"""
Django Admin configuration for UserBalance model.

This provides an admin interface to view and manage user balances.
"""
from django.contrib import admin
from django.db.models import Sum
from api.models.user_balance import UserBalance, BalanceType


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'user_code',
        'user_phone',
        'balance_type',
        'formatted_amount',
        'currency_code',
        'created_at',
        'updated_at'
    ]
    list_filter = [
        'balance_type',
        'currency',
        'created_at',
    ]
    search_fields = [
        'user__code',
        'user__phone',
        'user__email',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    ordering = ['-created_at']

    def user_code(self, obj):
        """Display user code."""
        return obj.user.code
    user_code.short_description = 'User Code'
    user_code.admin_order_field = 'user__code'

    def user_phone(self, obj):
        """Display user phone."""
        return obj.user.phone or '-'
    user_phone.short_description = 'Phone'

    def formatted_amount(self, obj):
        """Display formatted amount with currency symbol."""
        return f"{obj.currency.symbol}{obj.amount:,.2f}"
    formatted_amount.short_description = 'Amount'
    formatted_amount.admin_order_field = 'amount'

    def currency_code(self, obj):
        """Display currency code."""
        return obj.currency.code
    currency_code.short_description = 'Currency'
    currency_code.admin_order_field = 'currency__code'

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'currency')

    # Custom admin actions
    actions = ['recalculate_balances']

    def recalculate_balances(self, request, queryset):
        """
        Recalculate balances for selected users.
        Only works for referral balances.
        """
        from api.utils.balance import sync_referral_earnings_to_balance

        user_ids = queryset.values_list('user_id', flat=True).distinct()
        count = 0

        for user_id in user_ids:
            from api.models.user import User
            user = User.objects.get(id=user_id)
            sync_referral_earnings_to_balance(user)
            count += 1

        self.message_user(
            request,
            f"Successfully recalculated balances for {count} users."
        )
    recalculate_balances.short_description = "Recalculate referral balances for selected users"
