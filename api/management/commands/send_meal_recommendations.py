"""
Management command to send meal recommendations to active users.

Usage:
    python manage.py send_meal_recommendations              # Send recommendations
    python manage.py send_meal_recommendations --dry-run    # Preview who would receive
    python manage.py send_meal_recommendations --test-user +2348012345678  # Test with specific user
    python manage.py send_meal_recommendations --force      # Force send even if already sent today
"""

from django.core.management.base import BaseCommand
from api.cron.recommend_meal import send_meal_recommendations, get_users_to_send_recommendations
from api.models.user import User
from api.models.recommendation import Recommendation, ChoiceOption
from api.models.meal import Meal, TimeOfDayChoices
from api.services.recommendation.meal_recommendation import MealRecommendationService
from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload
from api.models.message import Message
from django.utils import timezone


class Command(BaseCommand):
    help = 'Send meal recommendations to active users (replied in last 24 hours)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which users would receive recommendations without actually sending',
        )
        parser.add_argument(
            '--test-user',
            type=str,
            help='Test with a specific user phone number (e.g., +2348012345678)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send recommendations even if already sent today (for testing)',
        )
        parser.add_argument(
            '--time-period',
            type=str,
            choices=['morning', 'afternoon', 'evening'],
            help='Override time period detection (for testing)',
        )

    def handle(self, **options):
        dry_run = options['dry_run']
        test_user_phone = options.get('test_user')
        force = options['force']
        time_period_override = options.get('time_period')

        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("Send Meal Recommendations - Cron Job"))
        self.stdout.write("="*60)

        # Test mode with specific user
        if test_user_phone:
            self.handle_test_user(test_user_phone, force, time_period_override)
            return

        # Dry run mode
        if dry_run:
            self.handle_dry_run()
            return

        # Normal execution
        self.stdout.write(self.style.WARNING("Sending meal recommendations to active users..."))
        self.stdout.write("")

        result = send_meal_recommendations()

        # Display results
        self.stdout.write("")
        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("SUMMARY"))
        self.stdout.write("="*60)
        self.stdout.write(f"Total active users checked: {result['total_users']}")
        self.stdout.write(self.style.SUCCESS(f"✓ Users sent recommendations: {result['users_sent']}"))
        self.stdout.write(f"Skipped (no city): {result['users_skipped_no_city']}")
        self.stdout.write(f"Skipped (already sent): {result['users_skipped_already_sent']}")

        if result['users_failed'] > 0:
            self.stdout.write(self.style.ERROR(f"✗ Failed: {result['users_failed']}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ No failures"))

        self.stdout.write(f"Total messages sent: {result['total_messages_sent']}")
        self.stdout.write("="*60)

    def handle_dry_run(self):
        """Show which users would receive recommendations without sending messages."""
        self.stdout.write(self.style.WARNING("DRY RUN MODE - No messages will be sent"))
        self.stdout.write("")

        users = get_users_to_send_recommendations()

        if not users:
            self.stdout.write(self.style.SUCCESS("No users need recommendations at this time"))
            self.stdout.write("")
            self.stdout.write("This could mean:")
            self.stdout.write("  • No users have replied in the last 24 hours")
            self.stdout.write("  • All active users already received recommendations for this time period today")
            self.stdout.write("  • Users don't have cities set")
            return

        self.stdout.write(f"Found {len(users)} user(s) who would receive recommendations:")
        self.stdout.write("")

        for user in users:
            time_period = user.get_time_period()
            today = user.get_local_time().date()

            # Check last message time
            last_message = user.messages.filter(role='user').order_by('-created_at').first()
            hours_ago = "N/A"
            if last_message:
                hours_ago = f"{(timezone.now() - last_message.created_at).total_seconds() / 3600:.1f}"

            self.stdout.write(
                f"  • {user.phone} - Time period: {time_period}, "
                f"Date: {today}, Last reply: {hours_ago}h ago"
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Would send recommendations to {len(users)} user(s)"))

    def handle_test_user(self, phone, force, time_period_override):
        """Test recommendations with a specific user."""
        self.stdout.write(self.style.WARNING(f"TEST MODE - User: {phone}"))
        if time_period_override:
            self.stdout.write(self.style.WARNING(f"Time period override: {time_period_override}"))
        self.stdout.write("")

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with phone {phone} not found"))
            return

        # Check if user has city
        if not user.city:
            self.stdout.write(self.style.ERROR("User has no city set. Cannot generate recommendations."))
            self.stdout.write("Please set user's city first.")
            return

        # Get time period
        if time_period_override:
            time_period = time_period_override
            self.stdout.write(f"Using override time period: {time_period}")
        else:
            time_period = user.get_time_period()
            self.stdout.write(f"Detected time period: {time_period}")

        today = user.get_local_time().date()

        self.stdout.write(f"User: {user.phone}")
        self.stdout.write(f"City: {user.city.name}")
        self.stdout.write(f"Date: {today}")
        self.stdout.write("")

        # Check if already sent
        existing_recommendations = Recommendation.objects.filter(
            user=user,
            time_of_day=TimeOfDayChoices.get_period(time_period),
            day=today,
            sent_to_user=True
        )

        if existing_recommendations.exists() and not force:
            self.stdout.write(
                self.style.WARNING(
                    f"User already received {time_period} recommendations today "
                    f"({existing_recommendations.count()} recommendations)"
                )
            )
            self.stdout.write("Use --force to send anyway")
            self.stdout.write("")

            # Show existing recommendations
            self.stdout.write("Existing recommendations:")
            for rec in existing_recommendations:
                self.stdout.write(f"  • {rec.choice_option}: {rec.meal.name} - {rec.meal.price:,.2f}")
            return

        # Generate and send recommendations
        try:
            self.stdout.write("Generating recommendations...")

            service = MealRecommendationService()
            recommended_meal_dict = service.get_recommendations(
                user=user,
                num_recommendations_per_period=2,
            )

            meal_ids = recommended_meal_dict.get(time_period, [])

            if not meal_ids:
                self.stdout.write(self.style.ERROR(f"No meals recommended for {time_period}"))
                return

            self.stdout.write(self.style.SUCCESS(f"Generated {len(meal_ids)} recommendations"))
            self.stdout.write("")

            # Get meals
            recommended_meals = Meal.objects.filter(id__in=meal_ids)

            messages_sent = 0
            for index, meal in enumerate(recommended_meals):
                choice_option = ChoiceOption.FIRST if index == 0 else ChoiceOption.SECOND
                position_text = 'first' if index == 0 else 'second'

                # Create or get recommendation
                recommendation_obj, created = Recommendation.objects.get_or_create(
                    user=user,
                    meal=meal,
                    time_of_day=TimeOfDayChoices.get_period(time_period),
                    choice_option=choice_option,
                    day=today,
                    defaults={'sent_to_user': True}
                )

                if not created and not force:
                    self.stdout.write(f"  Recommendation already exists: {meal.name}")
                    continue

                # Update if using force
                if not created:
                    recommendation_obj.sent_to_user = True
                    recommendation_obj.save(update_fields=['sent_to_user'])

                # Send message
                text = f"Your {position_text} {time_period} meal recommendation, {meal.name}, Meal Cost {meal.price:,.2f}"
                image_url = meal.image_url.url if meal.image_url else None
                payload = recommend_product_payload(recommendation_obj.id, text, image_url)

                Message.bot_message_action_reply(
                    content=text,
                    user=user,
                    payload=payload,
                    metadata={
                        "meal_id": str(meal.id),
                        "recommendation_id": recommendation_obj.id,
                        "description": "Users can order, like or hate meal"
                    }
                )

                messages_sent += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Sent {position_text} recommendation: {meal.name} - {meal.price:,.2f}"
                    )
                )

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"✓ Successfully sent {messages_sent} recommendation(s) to {user.phone}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
