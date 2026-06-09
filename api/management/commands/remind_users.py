"""
Management command to remind users to reply within the 24-hour free messaging window.

Usage:
    python manage.py remind_users [--async]

Options:
    --async    Queue the task asynchronously via Huey (default: run synchronously)
"""

from django.core.management.base import BaseCommand
from api.tasks.remind_user_to_reply import remind_users_to_reply_task


class Command(BaseCommand):
    help = 'Remind users to reply within the 24-hour free messaging window'

    def add_arguments(self, parser):
        parser.add_argument(
            '--async',
            action='store_true',
            dest='run_async',
            help='Queue the task asynchronously via Huey'
        )

    def handle(self, **options):
        self.stdout.write("="*60)
        self.stdout.write(self.style.HTTP_INFO("Remind Users to Reply - Huey Task"))
        self.stdout.write("="*60)

        if options['run_async']:
            self.stdout.write(self.style.WARNING("Queuing task asynchronously..."))
            remind_users_to_reply_task()
            self.stdout.write(self.style.SUCCESS("Task queued successfully!"))
            return

        self.stdout.write(self.style.WARNING("Sending reminders to users (synchronous)..."))
        self.stdout.write("")

        # Call the task function directly for synchronous execution
        result = remind_users_to_reply_task.call_local()

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
