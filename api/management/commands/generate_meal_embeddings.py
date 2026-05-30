from django.core.management.base import BaseCommand
from api.models.meal import Meal
from api.services.recommendation.embedding_recommendation import EmbeddingRecommendationService
from django.utils import timezone


class Command(BaseCommand):
    help = 'Generate embeddings for meals that do not have them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of embeddings for all meals',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of meals to process in each batch',
        )
        parser.add_argument(
            '--city',
            type=str,
            help='Only process meals from a specific city',
        )

    def handle(self, *args, **options):
        force = options['force']
        batch_size = options['batch_size']
        city_name = options.get('city')

        # Build query
        queryset = Meal.objects.filter(available=True)

        if city_name:
            queryset = queryset.filter(city__name__iexact=city_name)
            self.stdout.write(f"Filtering by city: {city_name}")

        if force:
            meals_to_process = queryset
            self.stdout.write(f"Force mode: regenerating embeddings for all meals")
        else:
            meals_to_process = queryset.filter(embedding__isnull=True)
            self.stdout.write(f"Processing meals without embeddings")

        total_count = meals_to_process.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No meals to process!"))
            return

        self.stdout.write(f"Found {total_count} meals to process")

        # Initialize service
        service = EmbeddingRecommendationService()

        # Process in batches
        processed = 0
        failed = 0

        for i in range(0, total_count, batch_size):
            batch = list(meals_to_process[i:i+batch_size])

            self.stdout.write(f"Processing batch {i//batch_size + 1} ({len(batch)} meals)...")

            try:
                service._generate_meal_embeddings(batch)
                processed += len(batch)
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Processed {processed}/{total_count} meals")
                )
            except Exception as e:
                failed += len(batch)
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to process batch: {str(e)}")
                )

        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"Successfully processed: {processed} meals"))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f"Failed: {failed} meals"))
        self.stdout.write("="*50)
