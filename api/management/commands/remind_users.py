"""
Management command to remind users to reply within the 24-hour free messaging window.

Usage:
    python manage.py remind_users              # Send reminders
    python manage.py remind_users --dry-run    # Preview who would be reminded
    python manage.py remind_users --test-user +2348012345678  # Test with specific user
"""

from django.core.management.base import BaseCommand
from api.cron.remind_user_to_reply import remind_users_to_reply, get_users_needing_reminder
from api.models.user import User
from api.models.message import Message, RoleChoices, CurrentIntentChoices
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Remind users to reply within the 24-hour free messaging window'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which users would be reminded without actually sending messages',
        )
        parser.add_argument(
            '--test-user',
            type=str,
            help='Test with a specific user phone number (e.g., +2348012345678)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send reminder even if already sent recently (for testing)',
        )

    def handle(self, **options):
        dry_run = options['dry_run']
        test_user_phone = options.get('test_user')
        force = options['force']

        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("Remind Users to Reply - Cron Job"))
        self.stdout.write("="*60)

        # Test mode with specific user
        if test_user_phone:
            self.handle_test_user(test_user_phone, force)
            return

        # Dry run mode
        if dry_run:
            self.handle_dry_run()
            return

        # Normal execution
        self.stdout.write(self.style.WARNING("Sending reminders to users..."))
        self.stdout.write("")

        result = remind_users_to_reply()

        # Display results
        self.stdout.write("")
        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("SUMMARY"))
        self.stdout.write("="*60)
        self.stdout.write(f"Total users checked: {result['total_checked']}")
        self.stdout.write(self.style.SUCCESS(f"✓ Reminders sent: {result['reminded']}"))
        self.stdout.write(f"Already reminded (skipped): {result['already_reminded']}")

        if result['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"✗ Errors: {result['errors']}"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ No errors"))

        self.stdout.write("="*60)

    def handle_dry_run(self):
        """Show which users would be reminded without sending messages."""
        self.stdout.write(self.style.WARNING("DRY RUN MODE - No messages will be sent"))
        self.stdout.write("")

        users = get_users_needing_reminder()

        if not users:
            self.stdout.write(self.style.SUCCESS("No users need reminders at this time"))
            return

        self.stdout.write(f"Found {len(users)} user(s) who need reminders:")
        self.stdout.write("")

        now = timezone.now()
        for user in users:
            # Get last user message time
            last_message = user.messages.filter(role=RoleChoices.USER).order_by('-created_at').first()

            if last_message:
                hours_ago = (now - last_message.created_at).total_seconds() / 3600
                self.stdout.write(
                    f"  • {user.phone} - Last reply: {last_message.created_at} "
                    f"({hours_ago:.1f} hours ago)"
                )
            else:
                self.stdout.write(f"  • {user.phone} - No messages found")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Would send {len(users)} reminder(s)"))

    def handle_test_user(self, phone, force):
        """Test reminder with a specific user."""
        self.stdout.write(self.style.WARNING(f"TEST MODE - User: {phone}"))
        self.stdout.write("")

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with phone {phone} not found"))
            return

        # Get last user message
        last_message = user.messages.filter(role=RoleChoices.USER).order_by('-created_at').first()

        if not last_message:
            self.stdout.write(self.style.ERROR("User has no messages"))
            return

        now = timezone.now()
        hours_ago = (now - last_message.created_at).total_seconds() / 3600

        self.stdout.write(f"User: {user.phone}")
        self.stdout.write(f"Last reply: {last_message.created_at}")
        self.stdout.write(f"Hours since last reply: {hours_ago:.1f}")
        self.stdout.write("")

        # Check if already reminded
        twenty_four_hours_ago = now - timedelta(hours=24)
        existing_reminder = Message.objects.filter(
            user=user,
            role=RoleChoices.BOT,
            current_intent=CurrentIntentChoices.REMINDER_MESSAGE,
            created_at__gte=twenty_four_hours_ago
        ).order_by('-created_at').first()

        if existing_reminder and not force:
            self.stdout.write(
                self.style.WARNING(
                    f"User already received reminder at {existing_reminder.created_at}"
                )
            )
            self.stdout.write("Use --force to send anyway")
            return

        # Send reminder
        try:
            message_content = (
                "Hi! 👋\n\n"
                "It's important you respond so we know you still want meal recommendations. "
                "If you don't reply, we might stop sending recommendations until you message us.\n\n"
                "Reply with anything to keep receiving personalized meal suggestions!"
            )

            Message.bot_message_action_reply_simple(
                content=message_content,
                user=user,
                action_replies=["Yes, keep them coming!"],
                current_intent=CurrentIntentChoices.REMINDER_MESSAGE
            )

            self.stdout.write(self.style.SUCCESS(f"✓ Reminder sent successfully to {user.phone}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error sending reminder: {str(e)}"))
