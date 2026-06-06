from django.contrib import admin

from api.models.address import DeliveryAddress
from api.models.currency import Currency
from api.models.location import Country, State, City
from api.models.meal import Allergy, FitnessGoal, HealthCondition, Meal, PreferredCuisine, TimeOfDayChoices
from api.models.meal_preference import MealPreference
from api.models.order import Order
from api.models.recommendation import Recommendation
from api.models.referral_earning import ReferralEarning
from api.models.restaurant import Restaurant
from api.models.review import Review
from api.models.settings import AppSettings
from api.models.user import User
from api.models.message import Message
from leaflet.admin import LeafletGeoAdmin

from django import forms

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

class MealAdminForm(forms.ModelForm):
    times_of_day = forms.MultipleChoiceField(
        choices=TimeOfDayChoices.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Meal
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load existing values into the form
        if self.instance.pk and self.instance.times_of_day:
            self.initial['times_of_day'] = self.instance.times_of_day

@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    form = MealAdminForm
