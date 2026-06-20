from django.db import models
from cloudinary.utils import cloudinary_url
from cloudinary import api
from api.models.base import BaseModel
from api.models.location import City
from api.models.restaurant import Restaurant
from api.utils.generate import generate_unique_code


class TimeOfDayChoices(models.TextChoices):
    MORNING = 'morning', 'Morning'
    AFTERNOON = 'afternoon', 'Afternoon'
    EVENING = 'evening', 'Evening'


    @staticmethod
    def get_time_of_day_as_str(time_of_day):
        if time_of_day == TimeOfDayChoices.MORNING:
            return "morning"
        elif time_of_day == TimeOfDayChoices.AFTERNOON:
            return "afternoon"
        else:
            return "evening"
    
    @staticmethod
    def get_period(value):
        if value == "morning":
            return TimeOfDayChoices.MORNING
        elif value == "afternoon":
            return TimeOfDayChoices.AFTERNOON
        else:
            return TimeOfDayChoices.EVENING


class HealthConditionChoices(models.TextChoices):
    DIABETES = 'diabetes', 'Diabetes'
    HYPERTENSION = 'hypertension', 'Hypertension'
    HIGH_CHOLESTEROL = 'high_cholesterol', 'High Cholesterol'
    ANEMIA = 'anemia', 'Anemia'
    CELIAC = 'celiac', 'Celiac Disease'
    LACTOSE_INTOLERANCE = 'lactose_intolerance', 'Lactose Intolerance'

    @classmethod
    def list_values(cls):
        return [choice.value.replace('_', ' ') for choice in cls]

class AllergyChoices(models.TextChoices):
    PEANUTS = 'peanuts', 'Peanuts'
    SEAFOOD = 'seafood', 'Seafood'
    DAIRY = 'dairy', 'Dairy'
    GLUTEN = 'gluten', 'Gluten'
    EGGS = 'eggs', 'Eggs'
    SOY = 'soy', 'Soy'
    TREE_NUTS = 'tree_nuts', 'Tree Nuts'

    @classmethod
    def list_values(cls):
        return [choice.value.replace('_', ' ') for choice in cls]
    
class FitnessGoalChoices(models.TextChoices):
    WEIGHT_LOSS = 'weight_loss', 'Weight Loss'
    MUSCLE_GAIN = 'muscle_gain', 'Muscle Gain'
    MAINTENANCE = 'maintenance', 'Maintenance'
    
    @classmethod
    def list_values(cls):
        return [choice.value.replace('_', ' ') for choice in cls]

class CuisineChoices(models.TextChoices):
    VEGAN_VEGETARIAN = 'vegan_vegetarian', 'Vegan Vegetarian'
    
    NIGERIAN = 'nigerian', 'Nigerian'
    GHANAIAN = 'ghanaian', 'Ghanaian'
    ETHIOPIAN = 'ethiopian', 'Ethiopian'
    MOROCCAN = 'moroccan', 'Moroccan'

    ITALIAN = 'italian', 'Italian'
    FRENCH = 'french', 'French'
    SPANISH = 'spanish', 'Spanish'
    GREEK = 'greek', 'Greek'
    BRITISH = 'british', 'British'

    CHINESE = 'chinese', 'Chinese'
    JAPANESE = 'japanese', 'Japanese'
    KOREAN = 'korean', 'Korean'
    THAI = 'thai', 'Thai'
    INDIAN = 'indian', 'Indian'
    VIETNAMESE = 'vietnamese', 'Vietnamese'
    FILIPINO = 'filipino', 'Filipino'

    AMERICAN = 'american', 'American'
    MEXICAN = 'mexican', 'Mexican'
    BRAZILIAN = 'brazilian', 'Brazilian'
    ARGENTINIAN = 'argentinian', 'Argentinian'
    CARIBBEAN = 'caribbean', 'Caribbean'

    @classmethod
    def list_values(cls):
        return [choice.value.replace('_', '/') for choice in cls]


class HealthCondition(BaseModel):
    name = models.CharField(
        max_length=50,
        choices=HealthConditionChoices.choices
    )
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Allergy(BaseModel):
    name = models.CharField(
        max_length=50,
        choices=AllergyChoices.choices
    )
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
    

class FitnessGoal(BaseModel):
    name = models.CharField(
        max_length=100,
        choices=FitnessGoalChoices.choices
    )
    description = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.name


class PreferredCuisine(BaseModel): # eg. Nigerian, Italian, Chinese
    name = models.CharField(
        max_length=100,
        choices=CuisineChoices.choices
    )
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

def unique_meal_code():
    return generate_unique_code(Meal, field='code')

class Meal(BaseModel):
    code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    name = models.CharField(max_length=250)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name='meals')

    description = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name='meals')

    image_url = models.ImageField(blank=True, null=True)

    available = models.BooleanField(default=True)

    times_of_day = models.JSONField(
        default=list,
        blank=True,
        help_text="Times of day this meal is good for (e.g., ['morning', 'afternoon', 'evening'])"
    )

    # Time-based availability
    available_from_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time when this meal becomes available (e.g., 06:00 for breakfast). Leave empty for no time restriction."
    )
    available_to_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time when this meal stops being available (e.g., 11:00 for breakfast). Leave empty for no time restriction."
    )

    # Stock management
    daily_stock_limit = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of this meal that can be ordered per day. Leave empty for unlimited stock."
    )
    remaining_stock = models.IntegerField(
        null=True,
        blank=True,
        help_text="Current remaining stock for today."
    )
    last_stock_reset_date = models.DateField(
        null=True,
        blank=True,
        help_text="Last date when stock was reset. Used for lazy daily reset based on city timezone."
    )

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

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Filter meals by city (very frequent in recommendation service)
            models.Index(fields=['city', 'available'], name='meal_city_available_idx'),
            # Restaurant meals
            models.Index(fields=['restaurant', 'available'], name='meal_restaurant_avail_idx'),
            # Meal code lookups
            models.Index(fields=['code'], name='meal_code_idx'),
            # Available meals with stock
            models.Index(fields=['available', '-created_at'], name='meal_available_created_idx'),
            # Price-based filtering
            models.Index(fields=['city', 'available', 'price'], name='meal_city_avail_price_idx'),
        ]

    def __str__(self):
        return f"{self.name} - {self.city.name} - {', '.join(list(self.fitness_goals.all().values_list('name', flat=True)))}"


    def is_available_at_time(self, check_time=None):
        """
        Check if meal is available at a specific time.

        Args:
            check_time: datetime.time object (defaults to current time)

        Returns:
            bool: True if available at the given time, False otherwise
        """
        from datetime import datetime

        if check_time is None:
            check_time = datetime.now().time()

        # Check time-based availability
        if self.available_from_time and check_time < self.available_from_time:
            return False

        if self.available_to_time and check_time > self.available_to_time:
            return False

        return True

    def has_stock_available(self):
        """
        Check if meal has stock available for ordering.

        Returns:
            bool: True if stock is available or unlimited, False if out of stock
        """
        # If no stock limit set, unlimited stock
        if self.daily_stock_limit is None:
            return True

        # If remaining_stock is None, initialize it to daily_stock_limit
        if self.remaining_stock is None:
            return True

        # Check if stock remains
        return self.remaining_stock > 0

    def is_fully_available(self, check_time=None):
        """
        Check if meal is fully available (enabled, in stock, restaurant open, time available).

        Args:
            check_time: datetime.time object (defaults to current time)

        Returns:
            bool: True if meal is available for ordering, False otherwise
        """
        # Check basic availability flag
        if not self.available:
            return False

        # Check if restaurant is inactive
        if self.restaurant.inactive:
            return False

        # Check if restaurant is open
        if not self.restaurant.is_open_now(current_time=check_time):
            return False

        # Check time-based availability
        if not self.is_available_at_time(check_time):
            return False

        # Check stock
        if not self.has_stock_available():
            return False

        return True

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = unique_meal_code()

        # Initialize remaining_stock to daily_stock_limit if set
        if self.daily_stock_limit is not None and self.remaining_stock is None:
            self.remaining_stock = self.daily_stock_limit

        super().save(*args, **kwargs)

    @property
    def get_branded_image_url(self) -> str:
        if self.image_url is None:
            return None
        
        try:
            print("Generating branded image URL for meal:", self.image_url.url)
            
            path = self.image_url.name

            print("Image path:", path)
            
            # public_id = path.split("/")[-1].split(".")[0]
            public_id = path
            print(f"Using public_id for branding: {public_id}")

            width = self.image_url.width
            height = self.image_url.height
            print(f"Original image dimensions: {width}x{height}")

            # Calculate sizes based on image dimensions
            logo_width = int(width * 0.40)
            font_size = int(height * 0.08)
            y_offset = int(height * 0.03)
            x_offset = int(width * 0.02)
            
            print(f"Calculated - Logo: {logo_width}px, Font: {font_size}px")

            branded_url, _ = cloudinary_url(
                public_id,
                transformation=[
                    # Logo overlay in top-right corner
                    {
                        'overlay': 'foodie_robot_brand:logo_kqqyoa',
                        'gravity': 'north_east',
                        'x': x_offset,
                        'y': y_offset,
                        'width': logo_width,
                        'opacity': 100
                    },
                    # Text overlay "Today's pick" at the bottom
                    {
                        'overlay': {
                            'font_family': 'Arial',
                            'font_size': font_size,
                            'font_weight': 'bold',
                            'text': "Today's pick"
                        },
                        'gravity': 'south',
                        'y': y_offset,
                        'color': 'white'
                    }
                ]
            )
            print(f"Generated branded URL: {branded_url}")
            return branded_url
        except Exception as e:
            print("get_branded_image_url error:", e)
            return None
