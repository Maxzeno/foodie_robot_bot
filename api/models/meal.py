import io
import os

from django.db import models
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image as PILImage

from api.models.base import BaseModel
from api.models.location import City
from cloudinary.models import CloudinaryField

from api.models.restaurant import Restaurant
from api.utils.generate import generate_unique_code


# Path to logo for branding meal images
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'utils', 'assets', 'logo.png')


def _get_font(size: int, bold: bool = False):
    """Get font with fallback to default."""
    try:
        font_paths = [
            # macOS fonts
            "/System/Library/Fonts/SFNSDisplay.ttf" if bold else "/System/Library/Fonts/SFNSText.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
            # Linux fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            # Windows fonts
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        ]
        for path in font_paths:
            try:
                from PIL import ImageFont
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        from PIL import ImageFont
        return ImageFont.load_default()
    except Exception:
        from PIL import ImageFont
        return ImageFont.load_default()


def add_logo_to_image(image_file):
    """Add FoodieRobot logo with background and catchy phrase to meal image."""
    if not image_file:
        return image_file

    try:
        from PIL import ImageDraw

        # Get filename
        filename = getattr(image_file, 'name', 'meal.jpg')

        # Open the image
        img = PILImage.open(image_file)

        # Convert to RGBA for transparency support
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Create drawing context
        draw = ImageDraw.Draw(img)

        # Open and resize logo (bigger - 25% of image width)
        logo = PILImage.open(LOGO_PATH)
        logo_width = int(img.width * 0.28)
        logo_ratio = logo.width / logo.height
        logo_height = int(logo_width / logo_ratio)
        logo = logo.resize((logo_width, logo_height), PILImage.Resampling.LANCZOS)

        # Position: top-right corner
        padding = int(img.width * 0.03)
        logo_x = img.width - logo_width - padding
        logo_y = padding

        # Draw rounded rectangle background behind logo (white with slight transparency)
        bg_padding = int(img.width * 0.02)
        bg_x1 = logo_x - bg_padding
        bg_y1 = logo_y - bg_padding
        bg_x2 = logo_x + logo_width + bg_padding
        bg_y2 = logo_y + logo_height + bg_padding

        # Create semi-transparent white background
        overlay = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle(
            (bg_x1, bg_y1, bg_x2, bg_y2),
            radius=int(img.width * 0.02),
            fill=(255, 255, 255, 230)
        )
        img = PILImage.alpha_composite(img, overlay)

        # Paste logo with transparency
        if logo.mode == 'RGBA':
            img.paste(logo, (logo_x, logo_y), logo)
        else:
            img.paste(logo, (logo_x, logo_y))

        # Add catchy phrase at bottom with gradient background
        phrase = "Today's pick!"
        font_size = int(img.width * 0.055)
        font = _get_font(font_size, bold=True)

        # Calculate text dimensions
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), phrase, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Banner at bottom
        banner_height = text_height + int(img.height * 0.04)
        banner_y = img.height - banner_height

        # Create gradient banner overlay
        banner_overlay = PILImage.new('RGBA', img.size, (0, 0, 0, 0))
        banner_draw = ImageDraw.Draw(banner_overlay)

        # Draw gradient (darker at bottom)
        for i in range(banner_height):
            opacity = int(200 * (i / banner_height))
            banner_draw.rectangle(
                [(0, banner_y + i), (img.width, banner_y + i + 1)],
                fill=(0, 0, 0, opacity)
            )

        img = PILImage.alpha_composite(img, banner_overlay)

        # Draw text centered on banner
        draw = ImageDraw.Draw(img)
        text_x = (img.width - text_width) // 2
        text_y = banner_y + (banner_height - text_height) // 2

        # Text shadow
        draw.text((text_x + 2, text_y + 2), phrase, font=font, fill=(0, 0, 0, 180))
        # Main text (white)
        draw.text((text_x, text_y), phrase, font=font, fill=(255, 255, 255, 255))

        # Convert back to RGB for JPEG output
        if img.mode == 'RGBA':
            background = PILImage.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background

        # Save to memory
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=90, optimize=True)
        output.seek(0)

        # Ensure filename ends with .jpg
        if not filename.lower().endswith(('.jpg', '.jpeg')):
            filename = filename.rsplit('.', 1)[0] + '.jpg'

        return InMemoryUploadedFile(
            file=output,
            field_name='image_url',
            name=filename,
            content_type='image/jpeg',
            size=output.getbuffer().nbytes,
            charset=None
        )

    except FileNotFoundError:
        print(f"Logo not found at {LOGO_PATH}, skipping logo overlay")
        return image_file
    except Exception as e:
        print(f"Error adding logo to image: {e}")
        return image_file


def process_meal_image(image_file):
    """
    Process meal image: enhance with AI, convert WebP to JPG, and add logo.

    Processing order:
    1. Convert WebP to JPG if needed
    2. Enhance with AI to make more appealing (realistic)
    3. Add FoodieRobot logo
    """
    if not image_file:
        return image_file

    try:
        filename = getattr(image_file, 'name', '')
        content_type = getattr(image_file, 'content_type', '')

        # Check if WebP - convert first
        is_webp = (
            filename.lower().endswith('.webp') or
            content_type == 'image/webp'
        )

        if is_webp:
            # Open WebP and convert to RGB
            img = PILImage.open(image_file)

            if img.mode in ('RGBA', 'LA', 'P'):
                background = PILImage.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Save as JPEG to memory
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=90, optimize=True)
            output.seek(0)

            new_filename = filename.rsplit('.', 1)[0] + '.jpg'

            image_file = InMemoryUploadedFile(
                file=output,
                field_name='image_url',
                name=new_filename,
                content_type='image/jpeg',
                size=output.getbuffer().nbytes,
                charset=None
            )

        return add_logo_to_image(image_file)

    except Exception as e:
        print(f"Error processing meal image: {e}")
        return image_file


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

    image_url = CloudinaryField('image', blank=True, null=True)

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

        # Note: Image processing (adding logo/text) is now handled asynchronously
        # by the process_meal_image_task after the meal is saved

        super().save(*args, **kwargs)
