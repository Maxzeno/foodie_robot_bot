"""
Management command to send meal recommendations to active users.

Usage:
    python manage.py send_meal_recommendations
"""

from django.core.management.base import BaseCommand

from api.cron.recommend_meal_optimized_v1 import send_meal_recommendations
# from api.cron.recommend_meal import send_meal_recommendations


class Command(BaseCommand):
    help = 'Send meal recommendations to active users (replied in last 24 hours)'

    def handle(self, **options):
        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("Send Meal Recommendations - Cron Job"))
        self.stdout.write("="*60)
        self.stdout.write(self.style.WARNING("Sending meal recommendations to active users..."))
        self.stdout.write("")

        result = send_meal_recommendations()

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
