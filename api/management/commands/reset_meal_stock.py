# """
# Management command to reset meal stock daily.

# This should be run as a daily cron job at midnight to reset remaining_stock
# back to daily_stock_limit for all meals.

# Usage:
#     python manage.py reset_meal_stock
#     python manage.py reset_meal_stock --dry-run
# """

# from django.core.management.base import BaseCommand
# from api.models.meal import Meal
# from django.utils import timezone


# class Command(BaseCommand):
#     help = 'Reset meal stock limits daily (reset remaining_stock to daily_stock_limit)'

#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--dry-run',
#             action='store_true',
#             help='Show which meals would be reset without actually resetting them',
#         )

#     def handle(self, **options):
#         dry_run = options['dry_run']

#         self.stdout.write("=" * 60)
#         self.stdout.write(self.style.HTTP_INFO("Reset Meal Stock - Daily Cron Job"))
#         self.stdout.write("=" * 60)
#         self.stdout.write(f"Timestamp: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
#         self.stdout.write("")

#         # Get meals that have stock tracking enabled
#         meals_with_stock_tracking = Meal.objects.filter(
#             daily_stock_limit__isnull=False
#         ).exclude(
#             daily_stock_limit=0
#         )

#         total_meals = meals_with_stock_tracking.count()

#         if total_meals == 0:
#             self.stdout.write(self.style.SUCCESS("No meals with stock tracking found."))
#             return

#         self.stdout.write(f"Found {total_meals} meal(s) with stock tracking enabled")
#         self.stdout.write("")

#         if dry_run:
#             self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
#             self.stdout.write("")

#             for meal in meals_with_stock_tracking[:10]:  # Show first 10 as sample
#                 current_stock = meal.remaining_stock if meal.remaining_stock is not None else "Not set"
#                 self.stdout.write(
#                     f"  • {meal.name} (ID: {meal.id}): "
#                     f"Current={current_stock}, Will reset to={meal.daily_stock_limit}"
#                 )

#             if total_meals > 10:
#                 self.stdout.write(f"  ... and {total_meals - 10} more")

#             self.stdout.write("")
#             self.stdout.write(self.style.SUCCESS(f"Would reset {total_meals} meal(s)"))

#         else:
#             # Reset stock for all meals with stock tracking
#             updated_count = 0
#             for meal in meals_with_stock_tracking:
#                 old_stock = meal.remaining_stock
#                 meal.remaining_stock = meal.daily_stock_limit
#                 meal.save(update_fields=['remaining_stock'])
#                 updated_count += 1

#                 # Log first few updates
#                 if updated_count <= 5:
#                     self.stdout.write(
#                         self.style.SUCCESS(
#                             f"  ✓ {meal.name}: {old_stock} → {meal.daily_stock_limit}"
#                         )
#                     )

#             if updated_count > 5:
#                 self.stdout.write(f"  ... and {updated_count - 5} more")

#             self.stdout.write("")
#             self.stdout.write(self.style.SUCCESS(f"✓ Successfully reset {updated_count} meal(s)"))

#         self.stdout.write("=" * 60)
