"""
Management command to populate FitnessGoal, HealthCondition, Allergy,
and PreferredCuisine lookup tables.

This is required for the AI meal analyzer signal to work properly.
"""
from django.core.management.base import BaseCommand
from api.models.meal import (
    FitnessGoal,
    FitnessGoalChoices,
    HealthCondition,
    HealthConditionChoices,
    Allergy,
    AllergyChoices,
    PreferredCuisine,
    CuisineChoices,
)


class Command(BaseCommand):
    help = 'Populates FitnessGoal, HealthCondition, Allergy, and PreferredCuisine lookup tables'

    def handle(self, *args, **options):
        self.stdout.write('Populating meal lookup tables...\n')

        # Populate FitnessGoals
        created_count = 0
        for choice in FitnessGoalChoices:
            obj, created = FitnessGoal.objects.get_or_create(
                name=choice.value,
                defaults={'description': choice.label}
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created FitnessGoal: {choice.label}')
        self.stdout.write(self.style.SUCCESS(f'FitnessGoals: {created_count} created, {FitnessGoal.objects.count()} total'))

        # Populate HealthConditions
        created_count = 0
        for choice in HealthConditionChoices:
            obj, created = HealthCondition.objects.get_or_create(
                name=choice.value,
                defaults={'description': choice.label}
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created HealthCondition: {choice.label}')
        self.stdout.write(self.style.SUCCESS(f'HealthConditions: {created_count} created, {HealthCondition.objects.count()} total'))

        # Populate Allergies
        created_count = 0
        for choice in AllergyChoices:
            obj, created = Allergy.objects.get_or_create(
                name=choice.value,
                defaults={'description': choice.label}
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created Allergy: {choice.label}')
        self.stdout.write(self.style.SUCCESS(f'Allergies: {created_count} created, {Allergy.objects.count()} total'))

        # Populate PreferredCuisines
        created_count = 0
        for choice in CuisineChoices:
            obj, created = PreferredCuisine.objects.get_or_create(
                name=choice.value,
                defaults={'description': choice.label}
            )
            if created:
                created_count += 1
                self.stdout.write(f'  Created PreferredCuisine: {choice.label}')
        self.stdout.write(self.style.SUCCESS(f'PreferredCuisines: {created_count} created, {PreferredCuisine.objects.count()} total'))

        self.stdout.write(self.style.SUCCESS('\nSuccessfully populated all meal lookup tables!'))
        self.stdout.write('\nYou can now create meals and the AI analyzer will be able to set:')
        self.stdout.write('  - Fitness goals (weight_loss, muscle_gain, maintenance)')
        self.stdout.write('  - Health condition restrictions (diabetes, hypertension, etc.)')
        self.stdout.write('  - Allergy restrictions (peanuts, seafood, dairy, etc.)')
        self.stdout.write('  - Cuisine types (nigerian, italian, chinese, etc.)')
