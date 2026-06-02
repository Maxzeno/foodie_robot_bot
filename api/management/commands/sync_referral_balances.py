"""
Management command to sync existing referral earnings to UserBalance model.

Usage:
    python manage.py sync_referral_balances

This command should be run once after deploying the UserBalance model
to populate balances from existing ReferralEarning records.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from api.utils.balance import sync_all_users_referral_earnings


class Command(BaseCommand):
    help = 'Sync all existing referral earnings to UserBalance model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode (no changes will be saved)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.WARNING(
                'Starting sync of referral earnings to UserBalance...'
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE('Running in DRY-RUN mode (no changes will be saved)')
            )

        try:
            if dry_run:
                # Use transaction to rollback all changes
                with transaction.atomic():
                    results = sync_all_users_referral_earnings()
                    self._display_results(results)
                    # Raise exception to rollback
                    raise Exception("Dry run - rolling back changes")
            else:
                results = sync_all_users_referral_earnings()
                self._display_results(results)

                self.stdout.write(
                    self.style.SUCCESS(
                        '\nSuccessfully synced referral earnings to UserBalance!'
                    )
                )

        except Exception as e:
            if dry_run and "Dry run" in str(e):
                self.stdout.write(
                    self.style.SUCCESS(
                        '\nDry run completed successfully (no changes saved)'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Error syncing balances: {str(e)}')
                )
                raise

    def _display_results(self, results):
        """Display the results of the sync operation."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('Sync Results:'))
        self.stdout.write('='*50)
        self.stdout.write(f"Total users: {results['total_users']}")
        self.stdout.write(f"Users with earnings: {results['users_with_earnings']}")
        self.stdout.write(f"Total balance records created: {results['total_balances_created']}")
        self.stdout.write('='*50 + '\n')
