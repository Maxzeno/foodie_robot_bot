"""
Management command to test the order review signal.

Usage:
    python manage.py test_order_review_signal <order_id>           # Test with specific order
    python manage.py test_order_review_signal --create-test-order  # Create test order and mark as received
"""

from django.core.management.base import BaseCommand
from api.models.order import Order, OrderStatus
from api.models.user import User
from api.models.meal import Meal
from api.models.review import Review


class Command(BaseCommand):
    help = 'Test the order review signal by marking an order as received'

    def add_arguments(self, parser):
        parser.add_argument(
            'order_id',
            nargs='?',
            type=int,
            help='Order ID to mark as received',
        )
        parser.add_argument(
            '--create-test-order',
            action='store_true',
            help='Create a test order and mark it as received',
        )
        parser.add_argument(
            '--user-phone',
            type=str,
            help='User phone number for test order (when using --create-test-order)',
        )

    def handle(self, **options):
        order_id = options.get('order_id')
        create_test = options['create_test_order']
        user_phone = options.get('user_phone')

        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("Test Order Review Signal"))
        self.stdout.write("="*60)

        if create_test:
            self.create_and_test_order(user_phone)
        elif order_id:
            self.test_existing_order(order_id)
        else:
            self.stdout.write(self.style.ERROR("Please provide either an order_id or use --create-test-order"))
            self.stdout.write("")
            self.stdout.write("Examples:")
            self.stdout.write("  python manage.py test_order_review_signal 123")
            self.stdout.write("  python manage.py test_order_review_signal --create-test-order --user-phone +234...")

    def create_and_test_order(self, user_phone):
        """Create a test order and mark it as received."""
        self.stdout.write(self.style.WARNING("Creating test order..."))
        self.stdout.write("")

        # Get or create test user
        if user_phone:
            try:
                user = User.objects.get(phone=user_phone)
                self.stdout.write(f"Using user: {user.phone}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User with phone {user_phone} not found"))
                return
        else:
            user = User.objects.filter(city__isnull=False).first()
            if not user:
                self.stdout.write(self.style.ERROR("No users found in database"))
                return
            self.stdout.write(f"Using first user: {user.phone}")

        # Get first available meal
        meal = Meal.objects.filter(available=True).first()
        if not meal:
            self.stdout.write(self.style.ERROR("No meals found in database"))
            return

        self.stdout.write(f"Using meal: {meal.name}")
        self.stdout.write("")

        # Create order
        order = Order.objects.create(
            user=user,
            meal=meal,
            status=OrderStatus.PENDING,
            quantity=1,
            currency=user.city.currency if user.city else meal.city.currency,
            total_price=meal.price,
            meal_price=meal.price,
            delivery_fee=0,
            amount_paid=meal.price,
            paid=True
        )

        self.stdout.write(self.style.SUCCESS(f"✓ Created test order: {order.code} (ID: {order.id})"))
        self.stdout.write(f"Status: {order.status}")
        self.stdout.write("")

        # Mark as received to trigger signal
        self.stdout.write(self.style.WARNING("Marking order as RECEIVED to trigger signal..."))
        self.stdout.write("")

        order.status = OrderStatus.RECEIVED
        order.save()

        self.stdout.write(self.style.SUCCESS("✓ Order marked as RECEIVED"))
        self.stdout.write("")
        self.stdout.write("Signal should have triggered!")
        self.stdout.write("")
        self.stdout.write("Check:")
        self.stdout.write(f"1. User {user.phone} should have received a WhatsApp Flow message")
        self.stdout.write(f"2. Message should contain ORDER_REVIEW flow")
        self.stdout.write(f"3. Order ID in message metadata: {order.id}")

    def test_existing_order(self, order_id):
        """Test with an existing order."""
        self.stdout.write(f"Testing with order ID: {order_id}")
        self.stdout.write("")

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Order with ID {order_id} not found"))
            return

        self.stdout.write(f"Order: {order.code}")
        self.stdout.write(f"User: {order.user.phone}")
        self.stdout.write(f"Meal: {order.meal.name}")
        self.stdout.write(f"Current status: {order.status}")
        self.stdout.write("")

        # Check if review already exists
        existing_review = Review.objects.filter(order=order).exists()
        if existing_review:
            self.stdout.write(self.style.WARNING("⚠ Review already exists for this order"))
            self.stdout.write("Signal will NOT send review request")
            self.stdout.write("")

        if order.status == OrderStatus.RECEIVED:
            self.stdout.write(self.style.WARNING("Order is already marked as RECEIVED"))
            self.stdout.write("Re-saving will trigger signal check...")
            self.stdout.write("")

            # Re-save to trigger signal
            order.save()

            self.stdout.write(self.style.SUCCESS("✓ Order re-saved"))
            self.stdout.write("")

            if existing_review:
                self.stdout.write("Signal did NOT send message (review exists)")
            else:
                self.stdout.write("Signal should have checked and potentially sent message")
        else:
            self.stdout.write(self.style.WARNING(f"Marking order as RECEIVED (was: {order.status})..."))
            self.stdout.write("")

            order.status = OrderStatus.RECEIVED
            order.save()

            self.stdout.write(self.style.SUCCESS("✓ Order marked as RECEIVED"))
            self.stdout.write("")
            self.stdout.write("Signal should have triggered!")

        self.stdout.write("")
        self.stdout.write("Expected behavior:")
        self.stdout.write("1. If NO review exists → WhatsApp Flow message sent")
        self.stdout.write("2. If review EXISTS → No message sent (already reviewed)")
        self.stdout.write("3. If message already sent → No duplicate message")
