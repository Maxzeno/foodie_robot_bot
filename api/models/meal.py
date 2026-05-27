from django.db import models
from api.models.base import BaseModel
from api.models.currency import Currency
from api.models.location import City

class HealthConditionChoices(models.TextChoices):
    DIABETES = 'diabetes', 'Diabetes'
    HYPERTENSION = 'hypertension', 'Hypertension'
    HIGH_CHOLESTEROL = 'high_cholesterol', 'High Cholesterol'
    ANEMIA = 'anemia', 'Anemia'
    CELIAC = 'celiac', 'Celiac Disease'
    LACTOSE_INTOLERANCE = 'lactose_intolerance', 'Lactose Intolerance'

class AllergyChoices(models.TextChoices):
    PEANUTS = 'peanuts', 'Peanuts'
    SEAFOOD = 'seafood', 'Seafood'
    DAIRY = 'dairy', 'Dairy'
    GLUTEN = 'gluten', 'Gluten'
    EGGS = 'eggs', 'Eggs'
    SOY = 'soy', 'Soy'
    TREE_NUTS = 'tree_nuts', 'Tree Nuts'

class FitnessGoalChoices(models.TextChoices):
    WEIGHT_LOSS = 'weight_loss', 'Weight Loss'
    MUSCLE_GAIN = 'muscle_gain', 'Muscle Gain'
    MAINTENANCE = 'maintenance', 'Maintenance'

class CuisineChoices(models.TextChoices):
    NIGERIAN = 'nigerian', 'Nigerian'
    # GHANAIAN = 'ghanaian', 'Ghanaian'
    # ETHIOPIAN = 'ethiopian', 'Ethiopian'
    # MOROCCAN = 'moroccan', 'Moroccan'

    # ITALIAN = 'italian', 'Italian'
    # FRENCH = 'french', 'French'
    # SPANISH = 'spanish', 'Spanish'
    # GREEK = 'greek', 'Greek'
    # BRITISH = 'british', 'British'

    CHINESE = 'chinese', 'Chinese'
    # JAPANESE = 'japanese', 'Japanese'
    # KOREAN = 'korean', 'Korean'
    # THAI = 'thai', 'Thai'
    # INDIAN = 'indian', 'Indian'
    # VIETNAMESE = 'vietnamese', 'Vietnamese'
    # FILIPINO = 'filipino', 'Filipino'

    # AMERICAN = 'american', 'American'
    # MEXICAN = 'mexican', 'Mexican'
    # BRAZILIAN = 'brazilian', 'Brazilian'
    # ARGENTINIAN = 'argentinian', 'Argentinian'
    # CARIBBEAN = 'caribbean', 'Caribbean'


class HealthCondition(BaseModel):
    name = models.CharField(
        max_length=50,
        choices=HealthConditionChoices.choices
    )
    description = models.TextField(null=True, blank=True)


class Allergy(BaseModel):
    name = models.CharField(
        max_length=50,
        choices=AllergyChoices.choices
    )
    description = models.TextField(null=True, blank=True)


class FitnessGoal(BaseModel):
    name = models.CharField(
        max_length=100,
        choices=FitnessGoalChoices.choices
    )
    description = models.TextField(null=True, blank=True)


class PreferredCuisine(BaseModel): # eg. Nigerian, Italian, Chinese
    name = models.CharField(
        max_length=100,
        choices=CuisineChoices.choices
    )
    description = models.TextField(null=True, blank=True)


class Meal(BaseModel):
    name = models.CharField(max_length=250)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name='meals')

    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='meals')

    image_url = models.URLField(blank=True, null=True)

    available = models.BooleanField(default=True)

    # Nutritional info
    calories = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    protein = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    carbs = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fats = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fiber = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sugar = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sodium = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    cholesterol = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    serving_amount_g = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total weight in grams (g) of one serving of this meal, including all components"
    )

    fitness_goals = models.ManyToManyField(FitnessGoal, blank=True, related_name="meals")
    restricted_health_conditions = models.ManyToManyField(HealthCondition, blank=True, related_name="meals")
    restricted_allergies = models.ManyToManyField(Allergy, blank=True, related_name="meals")
    cuisine = models.ManyToManyField(PreferredCuisine, blank=True, related_name="meals")

    def __str__(self):
        return self.name
