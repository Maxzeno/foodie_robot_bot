from django.contrib import admin

from api.models.address import DeliveryAddress
from api.models.currency import Currency
from api.models.location import City, Country, State
from api.models.meal import Allergy, FitnessGoal, HealthCondition, Meal, PreferredCuisine
from api.models.order import Order
from api.models.recommendation import Recommendation
from api.models.review import Review
from api.models.user import User
from leaflet.admin import LeafletGeoAdmin

# Register your models here.
admin.site.register(User)
admin.site.register(DeliveryAddress, LeafletGeoAdmin)
admin.site.register(City, LeafletGeoAdmin)
admin.site.register(State)
admin.site.register(Country)
admin.site.register(Meal)
admin.site.register(HealthCondition)
admin.site.register(Allergy)
admin.site.register(FitnessGoal)
admin.site.register(PreferredCuisine)
admin.site.register(Recommendation)
admin.site.register(Order)
admin.site.register(Review)
admin.site.register(Currency)
