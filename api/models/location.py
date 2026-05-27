from django.db import models
from api.models.base import BaseModel


class Country(BaseModel):
    name = models.CharField(max_length=100, unique=True) # e.g. "Nigeria"
    code = models.CharField(max_length=2, unique=True) # ISO 3166-1 alpha-2 e.g. "NG"

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name


class State(BaseModel):
    name = models.CharField(max_length=100) # e.g. "Lagos"
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="states"
    )

    class Meta:
        unique_together = ('name', 'country') # Prevent duplicate state names within same country
        verbose_name = "State"
        verbose_name_plural = "States"

    def __str__(self):
        return f"{self.name}, {self.country.code}"


class City(BaseModel):
    name = models.CharField(max_length=100) # e.g. "Ikeja"
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, related_name="cities"
    )

    class Meta:
        unique_together = ('name', 'state') # Prevent duplicate city names within same state
        verbose_name = "City"
        verbose_name_plural = "Cities"

    def __str__(self):
        return f"{self.name}, {self.state.name}"
