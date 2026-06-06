from api.models.base import BaseModel
from django.db import models
from django.contrib.gis.db import models as gis_models


class Restaurant(BaseModel):
    name = models.CharField(max_length=250)
    phone = models.CharField(max_length=250)
    address = models.CharField(max_length=250)
    point = gis_models.PointField(srid=4326)

    email = models.CharField(max_length=250, blank=True, null=True)
    website = models.URLField(max_length=250, blank=True, null=True)
    social = models.URLField(max_length=250, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.phone} - {self.address} - {self.website} - {self.social}"
