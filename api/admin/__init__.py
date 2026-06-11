from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Sum, Max, Q
from datetime import timedelta

from api.models.address import DeliveryAddress
from api.models.currency import Currency
from api.models.location import Country, State, City
from api.models.meal import Allergy, FitnessGoal, HealthCondition, Meal, PreferredCuisine
from api.models.meal_preference import MealPreference
from api.models.order import Order, OrderStatus
from api.models.recommendation import Recommendation
from api.models.referral_earning import ReferralEarning
from api.models.restaurant import Restaurant
from api.models.review import Review
from api.models.settings import AppSettings
from api.models.user import User
from api.models.message import Message, RoleChoices
from api.models.special_occasion import SpecialOccasion
from api.models.meal_embedding import MealEmbedding
from api.models.user_balance import UserBalance
from api.models.withdrawal import Withdrawal


# =============================================================================
# USER ADMIN
# =============================================================================
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['code', 'phone', 'city', 'gender', 'order_count', 'message_count', 'is_active_badge', 'created_at']
    list_filter = ['city', 'gender', 'is_active', 'created_at']
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
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
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
                return format_html('<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Active</span>')
            elif hours_ago <= 72:
                return format_html('<span style="background: #ffc107; color: black; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Recent</span>')
        return format_html('<span style="background: #6c757d; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Inactive</span>')
    is_active_badge.short_description = 'Activity'


# =============================================================================
# ORDER ADMIN
# =============================================================================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['code', 'user_link', 'meal_name', 'quantity', 'total_price_display', 'status_badge', 'paid_badge', 'ordered_via', 'created_at']
    list_filter = ['status', 'paid', 'ordered_via', 'currency', 'created_at']
    search_fields = ['code', 'user__phone', 'user__code', 'meal__name', 'rider_phone', 'rider_name']
    readonly_fields = ['code', 'created_at', 'updated_at']
    raw_id_fields = ['user', 'meal']
    ordering = ['-created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Order Info', {
            'fields': ('code', 'user', 'meal', 'quantity', 'status', 'ordered_via')
        }),
        ('Pricing', {
            'fields': ('currency', 'meal_price', 'delivery_fee', 'total_price', 'amount_paid', 'paid')
        }),
        ('Pickup Location', {
            'fields': ('pickup_street_address', 'pickup_point'),
            'classes': ('collapse',)
        }),
        ('Delivery Location', {
            'fields': ('dropoff_street_address', 'dropoff_point'),
        }),
        ('Rider Info', {
            'fields': ('rider_name', 'rider_phone', 'rider_company', 'rider_note'),
            'classes': ('collapse',)
        }),
        ('Notes & Timestamps', {
            'fields': ('note', 'delivered_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_dispatched', 'mark_as_arrived', 'mark_as_received', 'mark_as_paid']

    def user_link(self, obj):
        return format_html('<a href="/admin/api/user/{}/change/">{}</a>', obj.user.id, obj.user.phone or obj.user.code)
    user_link.short_description = 'User'

    def meal_name(self, obj):
        return obj.meal.name[:30] + '...' if len(obj.meal.name) > 30 else obj.meal.name
    meal_name.short_description = 'Meal'

    def total_price_display(self, obj):
        return f"{obj.currency.symbol}{obj.total_price:,.2f}"
    total_price_display.short_description = 'Total'

    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'dispatched': '#17a2b8',
            'arrived': '#6f42c1',
            'received': '#28a745',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html('<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>', color, obj.status.upper())
    status_badge.short_description = 'Status'

    def paid_badge(self, obj):
        if obj.paid:
            return format_html('<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">PAID</span>')
        return format_html('<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">UNPAID</span>')
    paid_badge.short_description = 'Payment'

    @admin.action(description='Mark selected orders as Dispatched')
    def mark_as_dispatched(self, request, queryset):
        queryset.update(status=OrderStatus.DISPATCHED)

    @admin.action(description='Mark selected orders as Arrived')
    def mark_as_arrived(self, request, queryset):
        queryset.update(status=OrderStatus.ARRIVED)

    @admin.action(description='Mark selected orders as Received')
    def mark_as_received(self, request, queryset):
        queryset.update(status=OrderStatus.RECEIVED, delivered_at=timezone.now())

    @admin.action(description='Mark selected orders as Paid')
    def mark_as_paid(self, request, queryset):
        queryset.update(paid=True)


# =============================================================================
# MESSAGE ADMIN
# =============================================================================
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
        return format_html('<a href="/admin/api/user/{}/change/">{}</a>', obj.user.id, obj.user.phone or obj.user.code)
    user_link.short_description = 'User'

    def role_badge(self, obj):
        if obj.role == 'user':
            return format_html('<span style="background: #17a2b8; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">USER</span>')
        return format_html('<span style="background: #6f42c1; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">BOT</span>')
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
        return format_html('<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>', color, obj.current_intent.replace('_', ' ').title())
    intent_badge.short_description = 'Intent'


# =============================================================================
# MEAL ADMIN
# =============================================================================
@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ['image_preview', 'name', 'restaurant', 'city', 'price_display', 'available_badge', 'stock_display', 'order_count', 'times_of_day']
    list_filter = ['available', 'city', 'restaurant', 'fitness_goals', 'cuisine', 'created_at']
    search_fields = ['name', 'code', 'description', 'restaurant__name']
    readonly_fields = ['code', 'image_preview_large', 'created_at', 'updated_at']
    filter_horizontal = ['fitness_goals', 'restricted_health_conditions', 'restricted_allergies', 'cuisine']
    ordering = ['-created_at']
    list_per_page = 50

    fieldsets = (
        ('Basic Info', {
            'fields': ('code', 'name', 'restaurant', 'city', 'description', 'price', 'available', 'image_url', 'image_preview_large')
        }),
        ('Availability', {
            'fields': ('times_of_day', 'available_from_time', 'available_to_time'),
            'classes': ('collapse',)
        }),
        ('Stock', {
            'fields': ('daily_stock_limit', 'remaining_stock'),
            'classes': ('collapse',)
        }),
        ('Nutrition', {
            'fields': ('calories', 'protein', 'carbs', 'fats', 'fiber', 'sugar', 'sodium', 'cholesterol', 'serving_amount_g'),
            'classes': ('collapse',)
        }),
        ('Diet & Restrictions', {
            'fields': ('fitness_goals', 'restricted_health_conditions', 'restricted_allergies', 'cuisine'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_order_count=Count('orders', distinct=True))

    def image_preview(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;"/>', obj.image_url.url)
        return '-'
    image_preview.short_description = 'Image'

    def image_preview_large(self, obj):
        if obj.image_url:
            return format_html('<img src="{}" style="max-width: 300px; max-height: 200px; object-fit: cover; border-radius: 8px;"/>', obj.image_url.url)
        return 'No image'
    image_preview_large.short_description = 'Preview'

    def price_display(self, obj):
        return f"{obj.price:,.2f}"
    price_display.short_description = 'Price'

    def available_badge(self, obj):
        if obj.available:
            return format_html('<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">YES</span>')
        return format_html('<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">NO</span>')
    available_badge.short_description = 'Available'

    def stock_display(self, obj):
        if obj.daily_stock_limit is None:
            return 'Unlimited'
        return f"{obj.remaining_stock or 0}/{obj.daily_stock_limit}"
    stock_display.short_description = 'Stock'

    def order_count(self, obj):
        return obj._order_count
    order_count.short_description = 'Orders'
    order_count.admin_order_field = '_order_count'


# =============================================================================
# RESTAURANT ADMIN
# =============================================================================
@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'address', 'hours_display', 'inactive_badge', 'meal_count']
    list_filter = ['inactive', 'created_at']
    search_fields = ['name', 'phone', 'address', 'email']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'phone', 'address', 'point')
        }),
        ('Contact', {
            'fields': ('email', 'website', 'social'),
            'classes': ('collapse',)
        }),
        ('Hours', {
            'fields': ('open_time', 'close_time', 'available_days'),
        }),
        ('Status', {
            'fields': ('inactive',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_meal_count=Count('meals', distinct=True))

    def hours_display(self, obj):
        return f"{obj.open_time.strftime('%H:%M')} - {obj.close_time.strftime('%H:%M')}"
    hours_display.short_description = 'Hours'

    def inactive_badge(self, obj):
        if obj.inactive:
            return format_html('<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">INACTIVE</span>')
        return format_html('<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">ACTIVE</span>')
    inactive_badge.short_description = 'Status'

    def meal_count(self, obj):
        return obj._meal_count
    meal_count.short_description = 'Meals'
    meal_count.admin_order_field = '_meal_count'


# =============================================================================
# RECOMMENDATION ADMIN
# =============================================================================
@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'meal_name', 'time_of_day', 'choice_option', 'day', 'sent_badge', 'accepted_badge', 'created_at']
    list_filter = ['time_of_day', 'choice_option', 'sent_to_user', 'accepted', 'day', 'created_at']
    search_fields = ['user__phone', 'user__code', 'meal__name']
    raw_id_fields = ['user', 'meal']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    list_per_page = 100
    date_hierarchy = 'day'

    def user_link(self, obj):
        return format_html('<a href="/admin/api/user/{}/change/">{}</a>', obj.user.id, obj.user.phone or obj.user.code)
    user_link.short_description = 'User'

    def meal_name(self, obj):
        return obj.meal.name[:30] + '...' if len(obj.meal.name) > 30 else obj.meal.name
    meal_name.short_description = 'Meal'

    def sent_badge(self, obj):
        if obj.sent_to_user:
            return format_html('<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">SENT</span>')
        return format_html('<span style="background: #6c757d; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">PENDING</span>')
    sent_badge.short_description = 'Sent'

    def accepted_badge(self, obj):
        if obj.accepted:
            return format_html('<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">YES</span>')
        return format_html('<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">NO</span>')
    accepted_badge.short_description = 'Accepted'


# =============================================================================
# REVIEW ADMIN
# =============================================================================
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
        return format_html('<a href="/admin/api/user/{}/change/">{}</a>', obj.user.id, obj.user.phone or obj.user.code)
    user_link.short_description = 'User'

    def order_code(self, obj):
        return obj.order.code
    order_code.short_description = 'Order'

    def rating_stars(self, obj):
        if obj.meal_rating:
            return format_html('<span style="color: #ffc107;">{}</span>', '★' * obj.meal_rating + '☆' * (5 - obj.meal_rating))
        return '-'
    rating_stars.short_description = 'Rating'

    def sentiment_badge(self, obj):
        if not obj.sentiment:
            return '-'
        colors = {'like': '#28a745', 'neutral': '#6c757d', 'hate': '#dc3545'}
        return format_html('<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                          colors.get(obj.sentiment, '#6c757d'), obj.sentiment.upper())
    sentiment_badge.short_description = 'Sentiment'

    def short_comment(self, obj):
        if obj.comment:
            return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
        return '-'
    short_comment.short_description = 'Comment'


# =============================================================================
# REFERRAL EARNING ADMIN
# =============================================================================
@admin.register(ReferralEarning)
class ReferralEarningAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'referred_user_link', 'amount_display', 'city', 'created_at']
    list_filter = ['currency', 'city', 'created_at']
    search_fields = ['user__phone', 'user__code', 'referred_user__phone', 'referred_user__code']
    raw_id_fields = ['user', 'referred_user']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def user_link(self, obj):
        return format_html('<a href="/admin/api/user/{}/change/">{}</a>', obj.user.id, obj.user.phone or obj.user.code)
    user_link.short_description = 'Referrer'

    def referred_user_link(self, obj):
        if obj.referred_user:
            return format_html('<a href="/admin/api/user/{}/change/">{}</a>', obj.referred_user.id, obj.referred_user.phone or obj.referred_user.code)
        return '-'
    referred_user_link.short_description = 'Referred User'

    def amount_display(self, obj):
        return f"{obj.currency.symbol}{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'


# =============================================================================
# USER BALANCE ADMIN
# =============================================================================
@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'amount_display', 'currency', 'updated_at']
    list_filter = ['currency', 'updated_at']
    search_fields = ['user__phone', 'user__code']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']

    def user_link(self, obj):
        return format_html('<a href="/admin/api/user/{}/change/">{}</a>', obj.user.id, obj.user.phone or obj.user.code)
    user_link.short_description = 'User'

    def amount_display(self, obj):
        return f"{obj.currency.symbol}{obj.amount:,.2f}"
    amount_display.short_description = 'Balance'


# =============================================================================
# WITHDRAWAL ADMIN
# =============================================================================
@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'amount_display', 'status_badge', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__phone', 'user__code']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def user_link(self, obj):
        return format_html('<a href="/admin/api/user/{}/change/">{}</a>', obj.user.id, obj.user.phone or obj.user.code)
    user_link.short_description = 'User'

    def amount_display(self, obj):
        if hasattr(obj, 'currency') and obj.currency:
            return f"{obj.currency.symbol}{obj.amount:,.2f}"
        return f"{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'

    def status_badge(self, obj):
        if hasattr(obj, 'status'):
            colors = {'pending': '#ffc107', 'approved': '#28a745', 'rejected': '#dc3545'}
            return format_html('<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                              colors.get(obj.status, '#6c757d'), obj.status.upper())
        return '-'
    status_badge.short_description = 'Status'


# =============================================================================
# LOCATION ADMINS
# =============================================================================
@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'state', 'timezone', 'user_count', 'meal_count']
    list_filter = ['state']
    search_fields = ['name', 'state__name']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _user_count=Count('users', distinct=True),
            _meal_count=Count('meals', distinct=True)
        )

    def user_count(self, obj):
        return obj._user_count
    user_count.short_description = 'Users'

    def meal_count(self, obj):
        return obj._meal_count
    meal_count.short_description = 'Meals'


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'city_count']
    list_filter = ['country']
    search_fields = ['name']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_city_count=Count('cities', distinct=True))

    def city_count(self, obj):
        return obj._city_count
    city_count.short_description = 'Cities'


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'state_count']
    search_fields = ['name', 'code']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_state_count=Count('states', distinct=True))

    def state_count(self, obj):
        return obj._state_count
    state_count.short_description = 'States'


# =============================================================================
# OTHER ADMINS
# =============================================================================
@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'street_address', 'is_default', 'created_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['user__phone', 'user__code', 'street_address']
    raw_id_fields = ['user']

    def user_link(self, obj):
        return format_html('<a href="/admin/api/user/{}/change/">{}</a>', obj.user.id, obj.user.phone or obj.user.code)
    user_link.short_description = 'User'


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'symbol']
    search_fields = ['name', 'code']


@admin.register(HealthCondition)
class HealthConditionAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(FitnessGoal)
class FitnessGoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(PreferredCuisine)
class PreferredCuisineAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(MealPreference)
class MealPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user_link', 'meal_name', 'preference_badge', 'created_at']
    list_filter = ['preference', 'created_at']
    search_fields = ['user__phone', 'user__code', 'meal__name']
    raw_id_fields = ['user', 'meal']

    def user_link(self, obj):
        return format_html('<a href="/admin/api/user/{}/change/">{}</a>', obj.user.id, obj.user.phone or obj.user.code)
    user_link.short_description = 'User'

    def meal_name(self, obj):
        return obj.meal.name
    meal_name.short_description = 'Meal'

    def preference_badge(self, obj):
        colors = {'like': '#28a745', 'neutral': '#6c757d', 'hate': '#dc3545'}
        return format_html('<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                          colors.get(obj.preference, '#6c757d'), obj.preference.upper())
    preference_badge.short_description = 'Preference'


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


# =============================================================================
# SPECIAL OCCASION ADMIN (already existed)
# =============================================================================
@admin.register(SpecialOccasion)
class SpecialOccasionAdmin(admin.ModelAdmin):
    list_display = ['name', 'date_display', 'boost_weight', 'is_recurring', 'active', 'meal_count', 'city_count']
    list_filter = ['active', 'is_recurring', 'month', 'cities']
    search_fields = ['name', 'description']
    filter_horizontal = ['meals', 'cities']

    fieldsets = (
        ('Occasion Details', {
            'fields': ('name', 'description', 'active')
        }),
        ('Date Configuration', {
            'fields': ('month', 'day', 'year', 'is_recurring'),
            'description': 'Set month (1-12) and day (1-31). Leave year blank for recurring annual occasions.'
        }),
        ('Boost Configuration', {
            'fields': ('boost_weight',),
            'description': 'Higher values = stronger recommendation. Typical: 50.0 for main dishes, 30.0 for sides.'
        }),
        ('Target Configuration', {
            'fields': ('meals', 'cities'),
            'description': 'Select meals to boost. Leave cities empty to apply globally.'
        }),
    )

    def meal_count(self, obj):
        return obj.meals.count()
    meal_count.short_description = 'Meals'

    def city_count(self, obj):
        count = obj.cities.count()
        return 'Global' if count == 0 else count
    city_count.short_description = 'Cities'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('meals', 'cities')


# =============================================================================
# MEAL EMBEDDING ADMIN (already existed)
# =============================================================================
@admin.register(MealEmbedding)
class MealEmbeddingAdmin(admin.ModelAdmin):
    list_display = ['meal', 'content_hash', 'embedding_preview', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['meal__name', 'content_hash']
    readonly_fields = ['meal', 'embedding', 'content_hash', 'embedding_text', 'created_at', 'updated_at']
    ordering = ['-updated_at']

    def embedding_preview(self, obj):
        if obj.embedding:
            return f"[{len(obj.embedding)} dims]"
        return "-"
    embedding_preview.short_description = 'Embedding'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
