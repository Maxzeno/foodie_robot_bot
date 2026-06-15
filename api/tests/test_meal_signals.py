"""
Test script for meal signal handlers.

Run with: python manage.py shell < api/tests/test_meal_signals.py
Or import and run test functions individually in Django shell.
"""
import logging
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from api.models.meal import Meal
from api.models.restaurant import Restaurant
from api.models.location import City

# Set up logging to see signal messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MealSignalTests(TransactionTestCase):
    """
    Test cases for meal signal handlers.
    Uses TransactionTestCase to properly test transaction.on_commit behavior.
    """

    def setUp(self):
        """Set up test data."""
        # Get or create required related objects
        self.city = City.objects.first()
        if not self.city:
            logger.error("No City found in database. Please create one first.")
            return

        self.restaurant = Restaurant.objects.first()
        if not self.restaurant:
            logger.error("No Restaurant found in database. Please create one first.")
            return

    @patch('api.tasks.process_meal_image.process_meal_image_task')
    @patch('api.tasks.analyze_meal_with_ai.analyze_meal_with_ai_task')
    def test_new_meal_with_image_triggers_both_tasks(self, mock_ai_task, mock_image_task):
        """Test that creating a new meal with image triggers both tasks."""
        if not self.city or not self.restaurant:
            self.skipTest("Required test data not available")

        # Create a new meal with a mock image
        meal = Meal.objects.create(
            name="Test Meal With Image",
            restaurant=self.restaurant,
            city=self.city,
            price=1500.00,
            image_url="test_image_public_id"  # Mock Cloudinary public_id
        )

        # Both tasks should be called
        mock_image_task.assert_called_once_with(meal.id)
        mock_ai_task.assert_called_once_with(meal.id)

        # Cleanup
        meal.delete()
        logger.info("✅ Test passed: New meal with image triggers both tasks")

    @patch('api.tasks.process_meal_image.process_meal_image_task')
    @patch('api.tasks.analyze_meal_with_ai.analyze_meal_with_ai_task')
    def test_new_meal_without_image_triggers_no_tasks(self, mock_ai_task, mock_image_task):
        """Test that creating a new meal without image triggers no tasks."""
        if not self.city or not self.restaurant:
            self.skipTest("Required test data not available")

        # Create a new meal without image
        meal = Meal.objects.create(
            name="Test Meal No Image",
            restaurant=self.restaurant,
            city=self.city,
            price=1500.00,
        )

        # Neither task should be called
        mock_image_task.assert_not_called()
        mock_ai_task.assert_not_called()

        # Cleanup
        meal.delete()
        logger.info("✅ Test passed: New meal without image triggers no tasks")

    @patch('api.tasks.process_meal_image.process_meal_image_task')
    @patch('api.tasks.analyze_meal_with_ai.analyze_meal_with_ai_task')
    def test_update_meal_without_image_change_triggers_no_tasks(self, mock_ai_task, mock_image_task):
        """Test that updating a meal without changing image triggers no tasks."""
        if not self.city or not self.restaurant:
            self.skipTest("Required test data not available")

        # Create a meal first (clear mocks after creation)
        meal = Meal.objects.create(
            name="Test Meal For Update",
            restaurant=self.restaurant,
            city=self.city,
            price=1500.00,
            image_url="original_image_id"
        )
        mock_image_task.reset_mock()
        mock_ai_task.reset_mock()

        # Update only the name (not the image)
        meal.name = "Updated Meal Name"
        meal.save()

        # Neither task should be called since image didn't change
        mock_image_task.assert_not_called()
        mock_ai_task.assert_not_called()

        # Cleanup
        meal.delete()
        logger.info("✅ Test passed: Update without image change triggers no tasks")

    @patch('api.tasks.process_meal_image.process_meal_image_task')
    @patch('api.tasks.analyze_meal_with_ai.analyze_meal_with_ai_task')
    def test_update_meal_with_new_image_triggers_only_image_task(self, mock_ai_task, mock_image_task):
        """Test that updating a meal with new image triggers only image task (not AI)."""
        if not self.city or not self.restaurant:
            self.skipTest("Required test data not available")

        # Create a meal first
        meal = Meal.objects.create(
            name="Test Meal Image Update",
            restaurant=self.restaurant,
            city=self.city,
            price=1500.00,
            image_url="original_image_id"
        )
        mock_image_task.reset_mock()
        mock_ai_task.reset_mock()

        # Update with a new image (simulating new public_id)
        meal.image_url = "new_image_id"
        meal.save()

        # Only image task should be called (AI only runs on creation)
        mock_image_task.assert_called_once_with(meal.id)
        mock_ai_task.assert_not_called()

        # Cleanup
        meal.delete()
        logger.info("✅ Test passed: Update with new image triggers only image task")


def run_quick_test():
    """
    Quick manual test function to run in Django shell.

    Usage:
        from api.tests.test_meal_signals import run_quick_test
        run_quick_test()
    """
    from unittest.mock import patch

    logger.info("=" * 60)
    logger.info("Running quick signal tests...")
    logger.info("=" * 60)

    city = City.objects.first()
    if not city:
        logger.error("❌ No City found. Create one first.")
        return

    restaurant = Restaurant.objects.first()
    if not restaurant:
        logger.error("❌ No Restaurant found. Create one first.")
        return

    logger.info(f"Using City: {city.name}, Restaurant: {restaurant.name}")

    # Test 1: New meal with image
    logger.info("\n--- Test 1: New meal WITH image ---")
    with patch('api.tasks.process_meal_image.process_meal_image_task') as mock_img, \
         patch('api.tasks.analyze_meal_with_ai.analyze_meal_with_ai_task') as mock_ai:

        meal = Meal.objects.create(
            name="Signal Test Meal 1",
            restaurant=restaurant,
            city=city,
            price=1500.00,
            image_url="test_signal_image"
        )

        if mock_img.called and mock_ai.called:
            logger.info(f"✅ PASS: Both tasks queued for meal {meal.id}")
        else:
            logger.error(f"❌ FAIL: Image task called={mock_img.called}, AI task called={mock_ai.called}")

        meal.delete()

    # Test 2: New meal without image
    logger.info("\n--- Test 2: New meal WITHOUT image ---")
    with patch('api.tasks.process_meal_image.process_meal_image_task') as mock_img, \
         patch('api.tasks.analyze_meal_with_ai.analyze_meal_with_ai_task') as mock_ai:

        meal = Meal.objects.create(
            name="Signal Test Meal 2",
            restaurant=restaurant,
            city=city,
            price=1500.00,
        )

        if not mock_img.called and not mock_ai.called:
            logger.info(f"✅ PASS: No tasks queued for meal without image")
        else:
            logger.error(f"❌ FAIL: Image task called={mock_img.called}, AI task called={mock_ai.called}")

        meal.delete()

    # Test 3: Update meal without changing image
    logger.info("\n--- Test 3: Update meal WITHOUT image change ---")
    with patch('api.tasks.process_meal_image.process_meal_image_task') as mock_img, \
         patch('api.tasks.analyze_meal_with_ai.analyze_meal_with_ai_task') as mock_ai:

        # Create meal first
        meal = Meal.objects.create(
            name="Signal Test Meal 3",
            restaurant=restaurant,
            city=city,
            price=1500.00,
            image_url="test_signal_image_3"
        )
        mock_img.reset_mock()
        mock_ai.reset_mock()

        # Update only name
        meal.name = "Updated Signal Test Meal 3"
        meal.save()

        if not mock_img.called and not mock_ai.called:
            logger.info(f"✅ PASS: No tasks queued when only name changed")
        else:
            logger.error(f"❌ FAIL: Image task called={mock_img.called}, AI task called={mock_ai.called}")

        meal.delete()

    # Test 4: Update meal WITH new image
    logger.info("\n--- Test 4: Update meal WITH new image ---")
    with patch('api.tasks.process_meal_image.process_meal_image_task') as mock_img, \
         patch('api.tasks.analyze_meal_with_ai.analyze_meal_with_ai_task') as mock_ai:

        # Create meal first
        meal = Meal.objects.create(
            name="Signal Test Meal 4",
            restaurant=restaurant,
            city=city,
            price=1500.00,
            image_url="test_signal_image_4_old"
        )
        mock_img.reset_mock()
        mock_ai.reset_mock()

        # Update with new image
        meal.image_url = "test_signal_image_4_new"
        meal.save()

        if mock_img.called and not mock_ai.called:
            logger.info(f"✅ PASS: Only image task queued on image update (AI not called)")
        else:
            logger.error(f"❌ FAIL: Image task called={mock_img.called}, AI task called={mock_ai.called}")

        meal.delete()

    logger.info("\n" + "=" * 60)
    logger.info("Quick tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_quick_test()
