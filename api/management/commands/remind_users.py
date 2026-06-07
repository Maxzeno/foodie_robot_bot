"""
Management command to remind users to reply within the 24-hour free messaging window.

Usage:
    python manage.py remind_users
"""

from django.core.management.base import BaseCommand
from api.cron.remind_user_to_reply import remind_users_to_reply


class Command(BaseCommand):
    help = 'Remind users to reply within the 24-hour free messaging window'

    def handle(self, **options):
        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("Remind Users to Reply - Cron Job"))
        self.stdout.write("="*60)
        self.stdout.write(self.style.WARNING("Sending reminders to users..."))
        self.stdout.write("")

        result = remind_users_to_reply()

        # Display results
        self.stdout.write("")
        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("SUMMARY"))
        self.stdout.write("="*60)
        self.stdout.write(f"Total users checked: {result['total_checked']}")
        self.stdout.write(self.style.SUCCESS(f"Reminders sent: {result['reminded']}"))
        self.stdout.write(f"Already reminded (skipped): {result['already_reminded']}")

        if result['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {result['errors']}"))
        else:
            self.stdout.write(self.style.SUCCESS("No errors"))

        self.stdout.write("="*60)
