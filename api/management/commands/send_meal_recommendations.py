"""
Management command to send meal recommendations to active users.

Usage:
    python manage.py send_meal_recommendations [--async]

Options:
    --async    Queue the task asynchronously via Huey (default: run synchronously)
"""

from django.core.management.base import BaseCommand
from api.tasks.recommend_meal import send_meal_recommendations_task


class Command(BaseCommand):
    help = 'Send meal recommendations to active users (replied in last 24 hours)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--async',
            action='store_true',
            dest='run_async',
            help='Queue the task asynchronously via Huey'
        )

    def handle(self, **options):
        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("Send Meal Recommendations - Huey Task"))
        self.stdout.write("="*60)

        if options['run_async']:
            self.stdout.write(self.style.WARNING("Queuing task asynchronously..."))
            send_meal_recommendations_task()
            self.stdout.write(self.style.SUCCESS("Task queued successfully!"))
            return

        self.stdout.write(self.style.WARNING("Sending meal recommendations to active users (synchronous)..."))
        self.stdout.write("")

        # Call the task function directly for synchronous execution
        result = send_meal_recommendations_task.call_local()

        # Display results
        self.stdout.write("")
        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("SUMMARY"))
        self.stdout.write("="*60)
        self.stdout.write(f"Total active users checked: {result['total_users']}")
        self.stdout.write(self.style.SUCCESS(f"Users sent recommendations: {result['users_sent']}"))
        self.stdout.write(f"Skipped (no city): {result['users_skipped_no_city']}")
        self.stdout.write(f"Skipped (already sent): {result['users_skipped_already_sent']}")

        if result['users_failed'] > 0:
            self.stdout.write(self.style.ERROR(f"Failed: {result['users_failed']}"))
        else:
            self.stdout.write(self.style.SUCCESS("No failures"))

        self.stdout.write(f"Total messages sent: {result['total_messages_sent']}")
        self.stdout.write("="*60)
