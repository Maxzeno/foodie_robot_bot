import io
import logging
import requests
from django import db
from huey.contrib.djhuey import task
from cloudinary.uploader import upload

logger = logging.getLogger(__name__)


@task()
def process_meal_image_task(meal_id):
    """
    Task to process meal image: download from Cloudinary, add logo and text, then re-upload.
    This replaces the original image in Cloudinary to avoid duplicates.

    Args:
        meal_id: ID of the meal to process
    """
    # Close stale database connections
    db.close_old_connections()

    try:
        from api.models.meal import Meal, add_logo_to_image

        # Fetch the meal
        try:
            meal = Meal.objects.get(pk=meal_id)
        except Meal.DoesNotExist:
            logger.error(f"Meal {meal_id} not found for image processing")
            return

        # Check if meal has an image
        if not meal.image_url:
            logger.warning(f"Meal {meal_id} has no image to process")
            return

        # Get the Cloudinary URL and public_id
        image_url = str(meal.image_url.url) if hasattr(meal.image_url, 'url') else str(meal.image_url)
        public_id = meal.image_url.public_id if hasattr(meal.image_url, 'public_id') else None

        if not public_id:
            logger.error(f"Could not extract public_id from meal {meal_id} image")
            return

        logger.info(f"Processing image for meal {meal_id}: {meal.name}")

        # Download the image from Cloudinary
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        # Create an in-memory file object
        image_file = io.BytesIO(response.content)
        image_file.name = f"{public_id.split('/')[-1]}.jpg"

        # Process the image (add logo and text)
        processed_image = add_logo_to_image(image_file)

        if not processed_image:
            logger.warning(f"Image processing returned None for meal {meal_id}")
            return

        # Reset file pointer to beginning
        processed_image.seek(0)

        # Upload processed image back to Cloudinary, replacing the original
        # Using the same public_id with overwrite=True will replace the original image
        upload_result = upload(
            processed_image,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
            format="jpg"
        )

        logger.info(
            f"Successfully processed and uploaded image for meal {meal_id}. "
            f"URL: {upload_result.get('secure_url')}"
        )

    except requests.RequestException as e:
        logger.error(f"Error downloading image for meal {meal_id}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error processing image for meal {meal_id}: {e}", exc_info=True)
