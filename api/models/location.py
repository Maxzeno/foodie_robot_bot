from django.db import models
from api.models.base import BaseModel
from api.models.currency import Currency
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point

# from api.models.meal import PreferredCuisine

class CommonTimezoneChoices(models.TextChoices):
    """
    Most commonly used timezones, organized by region.
    Better for dropdowns and user selection.
    """
    # Africa
    AFRICA_ABIDJAN = 'Africa/Abidjan', 'Africa/Abidjan (GMT)'
    AFRICA_ACCRA = 'Africa/Accra', 'Africa/Accra (GMT)'
    AFRICA_ADDIS_ABABA = 'Africa/Addis_Ababa', 'Africa/Addis Ababa (EAT, +03:00)'
    AFRICA_ALGIERS = 'Africa/Algiers', 'Africa/Algiers (CET, +01:00)'
    AFRICA_CAIRO = 'Africa/Cairo', 'Africa/Cairo (EET, +02:00)'
    AFRICA_CASABLANCA = 'Africa/Casablanca', 'Africa/Casablanca (+01:00)'
    AFRICA_JOHANNESBURG = 'Africa/Johannesburg', 'Africa/Johannesburg (SAST, +02:00)'
    AFRICA_LAGOS = 'Africa/Lagos', 'Africa/Lagos (WAT, +01:00)'
    AFRICA_NAIROBI = 'Africa/Nairobi', 'Africa/Nairobi (EAT, +03:00)'
    AFRICA_TUNIS = 'Africa/Tunis', 'Africa/Tunis (CET, +01:00)'
    
    # Americas
    AMERICA_ANCHORAGE = 'America/Anchorage', 'America/Anchorage (AKST, -09:00)'
    AMERICA_ARGENTINA_BUENOS_AIRES = 'America/Argentina/Buenos_Aires', 'America/Buenos Aires (ART, -03:00)'
    AMERICA_BOGOTA = 'America/Bogota', 'America/Bogota (COT, -05:00)'
    AMERICA_CARACAS = 'America/Caracas', 'America/Caracas (VET, -04:00)'
    AMERICA_CHICAGO = 'America/Chicago', 'America/Chicago (CST, -06:00)'
    AMERICA_DENVER = 'America/Denver', 'America/Denver (MST, -07:00)'
    AMERICA_LOS_ANGELES = 'America/Los_Angeles', 'America/Los Angeles (PST, -08:00)'
    AMERICA_MEXICO_CITY = 'America/Mexico_City', 'America/Mexico City (CST, -06:00)'
    AMERICA_NEW_YORK = 'America/New_York', 'America/New York (EST, -05:00)'
    AMERICA_SAO_PAULO = 'America/Sao_Paulo', 'America/Sao Paulo (BRT, -03:00)'
    AMERICA_TORONTO = 'America/Toronto', 'America/Toronto (EST, -05:00)'
    AMERICA_VANCOUVER = 'America/Vancouver', 'America/Vancouver (PST, -08:00)'
    
    # Asia
    ASIA_BAGHDAD = 'Asia/Baghdad', 'Asia/Baghdad (AST, +03:00)'
    ASIA_BANGKOK = 'Asia/Bangkok', 'Asia/Bangkok (ICT, +07:00)'
    ASIA_BEIJING = 'Asia/Beijing', 'Asia/Beijing (CST, +08:00)'
    ASIA_DHAKA = 'Asia/Dhaka', 'Asia/Dhaka (BST, +06:00)'
    ASIA_DUBAI = 'Asia/Dubai', 'Asia/Dubai (GST, +04:00)'
    ASIA_HONG_KONG = 'Asia/Hong_Kong', 'Asia/Hong Kong (HKT, +08:00)'
    ASIA_JAKARTA = 'Asia/Jakarta', 'Asia/Jakarta (WIB, +07:00)'
    ASIA_JERUSALEM = 'Asia/Jerusalem', 'Asia/Jerusalem (IST, +02:00)'
    ASIA_KARACHI = 'Asia/Karachi', 'Asia/Karachi (PKT, +05:00)'
    ASIA_KOLKATA = 'Asia/Kolkata', 'Asia/Kolkata (IST, +05:30)'
    ASIA_KUALA_LUMPUR = 'Asia/Kuala_Lumpur', 'Asia/Kuala Lumpur (MYT, +08:00)'
    ASIA_MANILA = 'Asia/Manila', 'Asia/Manila (PHT, +08:00)'
    ASIA_RIYADH = 'Asia/Riyadh', 'Asia/Riyadh (AST, +03:00)'
    ASIA_SEOUL = 'Asia/Seoul', 'Asia/Seoul (KST, +09:00)'
    ASIA_SHANGHAI = 'Asia/Shanghai', 'Asia/Shanghai (CST, +08:00)'
    ASIA_SINGAPORE = 'Asia/Singapore', 'Asia/Singapore (SGT, +08:00)'
    ASIA_TAIPEI = 'Asia/Taipei', 'Asia/Taipei (CST, +08:00)'
    ASIA_TOKYO = 'Asia/Tokyo', 'Asia/Tokyo (JST, +09:00)'
    
    # Australia & Pacific
    AUSTRALIA_MELBOURNE = 'Australia/Melbourne', 'Australia/Melbourne (AEDT, +11:00)'
    AUSTRALIA_PERTH = 'Australia/Perth', 'Australia/Perth (AWST, +08:00)'
    AUSTRALIA_SYDNEY = 'Australia/Sydney', 'Australia/Sydney (AEDT, +11:00)'
    PACIFIC_AUCKLAND = 'Pacific/Auckland', 'Pacific/Auckland (NZDT, +13:00)'
    PACIFIC_FIJI = 'Pacific/Fiji', 'Pacific/Fiji (FJT, +12:00)'
    PACIFIC_HONOLULU = 'Pacific/Honolulu', 'Pacific/Honolulu (HST, -10:00)'
    
    # Europe
    EUROPE_AMSTERDAM = 'Europe/Amsterdam', 'Europe/Amsterdam (CET, +01:00)'
    EUROPE_ATHENS = 'Europe/Athens', 'Europe/Athens (EET, +02:00)'
    EUROPE_BERLIN = 'Europe/Berlin', 'Europe/Berlin (CET, +01:00)'
    EUROPE_BRUSSELS = 'Europe/Brussels', 'Europe/Brussels (CET, +01:00)'
    EUROPE_BUCHAREST = 'Europe/Bucharest', 'Europe/Bucharest (EET, +02:00)'
    EUROPE_DUBLIN = 'Europe/Dublin', 'Europe/Dublin (GMT)'
    EUROPE_ISTANBUL = 'Europe/Istanbul', 'Europe/Istanbul (TRT, +03:00)'
    EUROPE_LISBON = 'Europe/Lisbon', 'Europe/Lisbon (WET)'
    EUROPE_LONDON = 'Europe/London', 'Europe/London (GMT)'
    EUROPE_MADRID = 'Europe/Madrid', 'Europe/Madrid (CET, +01:00)'
    EUROPE_MOSCOW = 'Europe/Moscow', 'Europe/Moscow (MSK, +03:00)'
    EUROPE_PARIS = 'Europe/Paris', 'Europe/Paris (CET, +01:00)'
    EUROPE_ROME = 'Europe/Rome', 'Europe/Rome (CET, +01:00)'
    EUROPE_STOCKHOLM = 'Europe/Stockholm', 'Europe/Stockholm (CET, +01:00)'
    EUROPE_VIENNA = 'Europe/Vienna', 'Europe/Vienna (CET, +01:00)'
    EUROPE_WARSAW = 'Europe/Warsaw', 'Europe/Warsaw (CET, +01:00)'
    EUROPE_ZURICH = 'Europe/Zurich', 'Europe/Zurich (CET, +01:00)'
    
    # UTC
    UTC = 'UTC', 'UTC (Coordinated Universal Time)'
    

class Country(BaseModel):
    name = models.CharField(max_length=100, unique=True) # e.g. "Nigeria"
    code = models.CharField(max_length=2, unique=True) # ISO 3166-1 alpha-2 e.g. "NG"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()

        if self.name:
            self.name = self.name.strip()

        super().save(*args, **kwargs)


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
    referral_bonus = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee_per_km = models.DecimalField(max_digits=10, decimal_places=2)
    min_delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)

    timezone = models.CharField(
            max_length=63,
            default=CommonTimezoneChoices.UTC,
            choices=CommonTimezoneChoices.choices,
            help_text="IANA timezone name (e.g., 'Africa/Lagos', 'America/New_York')"
        )
 
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
