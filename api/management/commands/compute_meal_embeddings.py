# api/management/commands/compute_meal_embeddings.py
"""
Management command to pre-compute and cache meal embeddings.

Run this command:
1. After adding new meals to the database
2. After updating meal descriptions or attributes
3. On initial setup to populate the embedding cache

Usage:
    python manage.py compute_meal_embeddings
    python manage.py compute_meal_embeddings --city=Lagos
    python manage.py compute_meal_embeddings --force  # Regenerate all
    python manage.py compute_meal_embeddings --batch-size=50
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from api.models.meal import Meal
from api.models.meal_embedding import MealEmbedding
from api.services.recommendation.meal_embedding import MealEmbeddingService


class Command(BaseCommand):
    help = 'Pre-compute and cache OpenAI embeddings for meals'

    def add_arguments(self, parser):
        parser.add_argument(
            '--city',
            type=str,
            help='Only process meals in this city (by name)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of all embeddings (ignore cache)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of meals to process in each batch (default: 100)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making API calls',
        )

    def handle(self, *args, **options):
        city_filter = options.get('city')
        force = options.get('force', False)
        batch_size = options.get('batch_size', 100)
        dry_run = options.get('dry_run', False)

        self.stdout.write(self.style.NOTICE('Starting meal embedding computation...'))

        # Build query
        queryset = Meal.objects.filter(available=True)

        if city_filter:
            queryset = queryset.filter(city__name__icontains=city_filter)
            self.stdout.write(f'Filtering by city: {city_filter}')

        # Prefetch related for embedding text generation
        queryset = queryset.prefetch_related('cuisine', 'fitness_goals')

        meals = list(queryset)
        total_meals = len(meals)

        self.stdout.write(f'Found {total_meals} available meals')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No API calls will be made'))

            # Check which need updates
            service = MealEmbeddingService()
            needs_update = 0

            for meal in meals:
                content_hash = service._compute_content_hash(meal)
                existing = MealEmbedding.objects.filter(
                    meal=meal,
                    content_hash=content_hash
                ).first()

                if not existing or force:
                    needs_update += 1
                    self.stdout.write(f'  Would update: {meal.name} (ID: {meal.id})')

            self.stdout.write(f'\n{needs_update} meals would be processed')

            # Estimate cost
            avg_tokens = 150  # Approximate tokens per meal
            cost_per_1k = 0.00002  # text-embedding-3-small pricing
            estimated_cost = (needs_update * avg_tokens / 1000) * cost_per_1k
            self.stdout.write(f'Estimated cost: ${estimated_cost:.4f}')

            return

        # Initialize service
        service = MealEmbeddingService()

        # Process in batches
        processed = 0
        cached = 0
        errors = 0

        for i in range(0, total_meals, batch_size):
            batch = meals[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_meals + batch_size - 1) // batch_size

            self.stdout.write(f'\nProcessing batch {batch_num}/{total_batches} '
                            f'({len(batch)} meals)...')

            try:
                # Get embeddings for batch
                embeddings = service.get_embeddings_batch(batch, force_refresh=force)

                batch_processed = len(embeddings)
                processed += batch_processed

                # Count cached vs new
                for meal in batch:
                    if meal.id in embeddings:
                        # Check if it was cached
                        content_hash = service._compute_content_hash(meal)
                        existing = MealEmbedding.objects.filter(
                            meal=meal,
                            content_hash=content_hash
                        ).first()
                        if existing and existing.updated_at == existing.created_at:
                            # Newly created
                            pass
                        else:
                            cached += 1

                self.stdout.write(
                    self.style.SUCCESS(f'  Batch complete: {batch_processed} embeddings')
                )

            except Exception as e:
                errors += len(batch)
                self.stdout.write(
                    self.style.ERROR(f'  Batch error: {str(e)}')
                )

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'Embedding computation complete!'))
        self.stdout.write(f'  Total meals: {total_meals}')
        self.stdout.write(f'  Processed: {processed}')
        self.stdout.write(f'  From cache: {cached}')
        self.stdout.write(f'  Errors: {errors}')

        # Show sample
        sample = MealEmbedding.objects.select_related('meal').first()
        if sample:
            self.stdout.write(f'\nSample embedding:')
            self.stdout.write(f'  Meal: {sample.meal.name}')
            self.stdout.write(f'  Hash: {sample.content_hash}')
            self.stdout.write(f'  Dimensions: {len(sample.embedding)}')
            self.stdout.write(f'  Text preview: {sample.embedding_text[:100]}...')
