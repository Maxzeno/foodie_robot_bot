from django.db import models
from api.models.base import BaseModel
from api.models.currency import Currency
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point

# from api.models.meal import PreferredCuisine


class Country(BaseModel):
    name = models.CharField(max_length=100, unique=True) # e.g. "Nigeria"
    code = models.CharField(max_length=2, unique=True) # ISO 3166-1 alpha-2 e.g. "NG"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name


class State(BaseModel):
    name = models.CharField(max_length=100) # e.g. "Lagos"
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="states"
    )

    class Meta:
        unique_together = ('name', 'country') # Prevent duplicate state names within same country
        ordering = ['-created_at']
        verbose_name = "State"
        verbose_name_plural = "States"

    def __str__(self):
        return f"{self.name}, {self.country.code}"


class City(BaseModel):
    name = models.CharField(max_length=100) # e.g. "Ikeja"
    state = models.ForeignKey(
        State, on_delete=models.PROTECT, related_name="cities"
    )
    boundary = gis_models.PolygonField(srid=4326)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='cities')
    preferred_cuisine = models.ManyToManyField("PreferredCuisine", blank=True, related_name="cities")
    average_meal_budget = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
 
    @classmethod
    def get_city_by_coordinates(cls, longitude, latitude):
        point = Point(longitude, latitude, srid=4326)
        
        try:
            # Use spatial lookup to find city whose boundary contains the point
            city = cls.objects.get(boundary__contains=point)
            return city
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            # In case of overlapping boundaries, return the first match
            return cls.objects.filter(boundary__contains=point).first()
    
    class Meta:
        unique_together = ('name', 'state') # Prevent duplicate city names within same state
        ordering = ['-created_at']
        verbose_name = "City"
        verbose_name_plural = "Cities"

    def __str__(self):
        return f"{self.name}, {self.state.name}"
