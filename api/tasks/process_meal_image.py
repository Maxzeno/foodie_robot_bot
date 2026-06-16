import io
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django import db
from huey.contrib.djhuey import task
from PIL import Image as PILImage
from cloudinary import CloudinaryImage
from cloudinary.uploader import upload, destroy

logger = logging.getLogger(__name__)


def get_image_public_id(img):
    """Extract public_id from CloudinaryField value.

    Handles both CloudinaryResource objects and string representations.
    String format: image/upload/v1234567890/public_id.jpg
    """
    if not img:
        return None
    if hasattr(img, 'public_id'):
        return img.public_id
    # For string values, extract just the public_id part
    img_str = str(img)
    # Remove 'image/upload/vXXX/' prefix if present
    if 'image/upload/' in img_str:
        # Format: image/upload/v1234567890/public_id.jpg
        parts = img_str.split('/')
        if len(parts) >= 4:
            # Get everything after version, remove extension
            public_id_with_ext = '/'.join(parts[3:])
            return public_id_with_ext.rsplit('.', 1)[0]
    return img_str


def get_http_session():
    """Create a requests session with retry logic."""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    return session


@task()
def process_meal_image_task(meal_id):
    """
    Task to process meal image: download from Cloudinary, convert to JPG,
    add logo and text, delete old image, upload new one, and update meal.

    Args:
        meal_id: ID of the meal to process
    """
    print(f"Starting process_meal_image_task for meal {meal_id}")

    # Close stale database connections
    db.close_old_connections()

    try:
        from api.models.meal import Meal, add_logo_to_image

        # Fetch the meal
        try:
            meal = Meal.objects.get(pk=meal_id)
        except Meal.DoesNotExist:
            print(f"Meal {meal_id} not found for image processing")
            return

        # Check if meal has an image
        if not meal.image_url:
            print(f"Meal {meal_id} has no image to process")
            return

        # Get the public_id using the helper function that handles both
        # CloudinaryResource objects and string representations
        old_public_id = get_image_public_id(meal.image_url)

        if not old_public_id:
            print(f"Could not extract public_id from meal {meal_id} image")
            return

        print(f"Extracted public_id: {old_public_id} from image_url: {meal.image_url}")

        print(f"Processing image for meal {meal_id}: {meal.name} (public_id: {old_public_id})")

        # Build download URL using Cloudinary SDK (more reliable, handles format conversion)
        image_url = CloudinaryImage(old_public_id).build_url(format='jpg')
        print(f"Downloading from: {image_url}")

        # Download the image with retry logic
        session = get_http_session()
        response = session.get(image_url, timeout=120)
        response.raise_for_status()
        print(f"Downloaded {len(response.content)} bytes")

        # Open image with PIL to handle any format (webp, png, etc.)
        original_image = PILImage.open(io.BytesIO(response.content))
        print(f"Downloaded image format: {original_image.format}, mode: {original_image.mode}")

        # Convert to RGB if necessary (handles RGBA, P, LA modes)
        if original_image.mode in ('RGBA', 'LA', 'P'):
            background = PILImage.new('RGB', original_image.size, (255, 255, 255))
            if original_image.mode == 'P':
                original_image = original_image.convert('RGBA')
            if original_image.mode in ('RGBA', 'LA'):
                background.paste(original_image, mask=original_image.split()[-1])
            else:
                background.paste(original_image)
            original_image = background
        elif original_image.mode != 'RGB':
            original_image = original_image.convert('RGB')

        # Save as JPEG to BytesIO for processing
        image_buffer = io.BytesIO()
        original_image.save(image_buffer, format='JPEG', quality=95)
        image_buffer.seek(0)
        image_buffer.name = f"meal_{meal_id}.jpg"

        # Process the image (add logo and text)
        processed_image = add_logo_to_image(image_buffer)

        if not processed_image:
            print(f"Image processing returned None for meal {meal_id}")
            return

        # Reset file pointer to beginning
        processed_image.seek(0)

        # Upload processed image to Cloudinary as a NEW image
        # Use a new public_id to ensure fresh upload
        new_public_id = f"meals/processed_{meal_id}"

        upload_result = upload(
            processed_image,
            public_id=new_public_id,
            overwrite=True,
            resource_type="image",
            format="jpg",
            invalidate=True  # Invalidate CDN cache
        )

        new_image_url = upload_result.get('secure_url')
        new_public_id_result = upload_result.get('public_id')
        new_version = upload_result.get('version')
        new_format = upload_result.get('format', 'jpg')

        print(f"Uploaded processed image for meal {meal_id}. New URL: {new_image_url}")
        print(f"Upload result: public_id={new_public_id_result}, version={new_version}, format={new_format}")

        # Update the meal with the new image
        # CloudinaryField stores: image/upload/v{version}/{public_id}.{format}
        cloudinary_resource_value = f"image/upload/v{new_version}/{new_public_id_result}.{new_format}"

        # Use update() to avoid triggering signals again
        Meal.objects.filter(pk=meal_id).update(image_url=cloudinary_resource_value)

        print(f"Updated meal {meal_id} with new image: {cloudinary_resource_value}")

        # Delete the old image from Cloudinary to free up space
        if old_public_id and old_public_id != new_public_id_result:
            try:
                destroy_result = destroy(old_public_id, resource_type="image")
                print(f"Deleted old image {old_public_id} from Cloudinary: {destroy_result}")
            except Exception as e:
                # Don't fail the task if deletion fails - just log it
                print(f"Failed to delete old image {old_public_id}: {e}")

        print(
            f"Successfully processed image for meal {meal_id}. "
            f"Old: {old_public_id} -> New: {new_public_id_result}"
        )

    except requests.RequestException as e:
        print(f"Error downloading image for meal {meal_id}: {e}", exc_info=True)
    except Exception as e:
        print(f"Error processing image for meal {meal_id}: {e}", exc_info=True)
