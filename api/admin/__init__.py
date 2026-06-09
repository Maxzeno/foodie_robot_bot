from django.contrib import admin

from api.models.address import DeliveryAddress
from api.models.currency import Currency
from api.models.location import Country, State, City
from api.models.meal import Allergy, FitnessGoal, HealthCondition, Meal, PreferredCuisine
from api.models.meal_preference import MealPreference
from api.models.order import Order
from api.models.recommendation import Recommendation
from api.models.referral_earning import ReferralEarning
from api.models.restaurant import Restaurant
from api.models.review import Review
from api.models.settings import AppSettings
from api.models.user import User
from api.models.message import Message
from api.models.special_occasion import SpecialOccasion
from leaflet.admin import LeafletGeoAdmin


from api.models.user_balance import UserBalance
from api.models.withdrawal import Withdrawal

# Import admin configurations

# Register your models here.
admin.site.register(DeliveryAddress, LeafletGeoAdmin)
admin.site.register(City, LeafletGeoAdmin)
admin.site.register(Restaurant, LeafletGeoAdmin)
admin.site.register(Order, LeafletGeoAdmin)

admin.site.register(User)
admin.site.register(State)
admin.site.register(Country)
admin.site.register(HealthCondition)
admin.site.register(Allergy)
admin.site.register(FitnessGoal)
admin.site.register(PreferredCuisine)
admin.site.register(Recommendation)
admin.site.register(Review)
admin.site.register(Currency)
admin.site.register(Message)
admin.site.register(MealPreference)
admin.site.register(ReferralEarning)
admin.site.register(Withdrawal)
admin.site.register(AppSettings)
admin.site.register(UserBalance)
admin.site.register(Meal)

# class MealAdminForm(forms.ModelForm):
#     times_of_day = forms.MultipleChoiceField(
#         choices=TimeOfDayChoices.choices,
#         widget=forms.CheckboxSelectMultiple,
#         required=False,
#     )

#     class Meta:
#         model = Meal
#         fields = '__all__'

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Load existing values into the form
#         if self.instance.pk and self.instance.times_of_day:
#             self.initial['times_of_day'] = self.instance.times_of_day

# @admin.register(Meal)
# class MealAdmin(admin.ModelAdmin):
#     form = MealAdminForm


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
