from django.core.management.base import BaseCommand
from faker import Faker
import random
from decimal import Decimal
from api.models.meal import (
    Meal, HealthCondition, Allergy, FitnessGoal, PreferredCuisine
)
from api.models.currency import Currency
from api.models.location import City


class Command(BaseCommand):
    help = 'Populate database with fake meal data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--meals',
            type=int,
            default=50,
            help='Number of meals to create'
        )

    def handle(self, *args, **options):
        fake = Faker()
        num_meals = options['meals']

        self.stdout.write('Getting health conditions, allergies, fitness goals, and cuisines...')
        
        # Create all health conditions
        health_conditions = []
        for hc in HealthCondition.objects.all():
            health_conditions.append(hc)

        # Create all allergies
        allergies = []
        for allergy in Allergy.objects.all():
            allergies.append(allergy)

        # Create all fitness goals
        fitness_goals = []
        for goal in FitnessGoal.objects.all():
            
            fitness_goals.append(goal)

        # Create all cuisines
        cuisines = []
        for cuisine in PreferredCuisine.objects.all():
            cuisines.append(cuisine)

        # Get or create currencies and cities
        currency = Currency.objects.get(
            code='NGN',
        )
        
        city = City.objects.get(
            name='Enugu')

        self.stdout.write(f'Creating {num_meals} meals...')

        meal_names = [
            'Grilled Chicken Salad', 'Jollof Rice with Beef', 'Pasta Carbonara',
            'Vegetable Stir Fry', 'Salmon Teriyaki', 'Caesar Salad',
            'Beef Tacos', 'Margherita Pizza', 'Chicken Curry', 'Sushi Platter',
            'Greek Yogurt Bowl', 'Protein Smoothie Bowl', 'Quinoa Buddha Bowl',
            'Turkey Sandwich', 'Veggie Burger', 'Shrimp Fried Rice',
            'Chicken Shawarma', 'Beef Burrito', 'Pad Thai', 'Pho Bo',
            'Chicken Alfredo', 'BBQ Ribs', 'Fish and Chips', 'Moussaka',
            'Paella', 'Tom Yum Soup', 'Bibimbap', 'Butter Chicken',
            'Fajitas', 'Ramen Bowl', 'Efo Riro with Pounded Yam',
            'Egusi Soup', 'Suya Plate', 'Moi Moi', 'Akara and Pap',
            'Fried Rice and Chicken', 'Ofada Rice with Ayamase',
            'Pepper Soup', 'Banga Soup', 'Edikang Ikong', 'Afang Soup',
            'Nkwobi', 'Abacha', 'Okra Soup', 'Ogbono Soup',
            'Jollof Spaghetti', 'Plantain and Eggs', 'Yam Porridge',
            'Beans Porridge', 'Coconut Rice'
        ]

        created_meals = 0
        for i in range(num_meals):
            meal_name = random.choice(meal_names) if i < len(meal_names) else fake.catch_phrase()
            
            meal = Meal.objects.create(
                name=f"{meal_name} #{i+1}" if i >= len(meal_names) else meal_name,
                description=fake.text(max_nb_chars=200),
                price=Decimal(random.uniform(500, 5000)).quantize(Decimal('0.01')),
                currency=currency,
                city=city,
                image_url=fake.image_url() if random.choice([True, False]) else None,
                available=random.choice([True, True, True, False]),  # 75% available
                
                calories=Decimal(random.uniform(150, 950)).quantize(Decimal('0.01')),
                protein=Decimal(random.uniform(5, 95)).quantize(Decimal('0.01')),
                carbs=Decimal(random.uniform(10, 120)).quantize(Decimal('0.01')),
                
                fats=Decimal(random.uniform(5, 60)).quantize(Decimal('0.01')),
                fiber=Decimal(random.uniform(2, 25)).quantize(Decimal('0.01')),
                sugar=Decimal(random.uniform(1, 30)).quantize(Decimal('0.01')),
                sodium=Decimal(random.uniform(100, 2000)).quantize(Decimal('0.01')),
                cholesterol=Decimal(random.uniform(0, 150)).quantize(Decimal('0.01')),
                serving_amount_g=Decimal(random.uniform(200, 800)).quantize(Decimal('0.01'))
            )

            # Add random fitness goals (1-2)
            meal.fitness_goals.set(random.sample(fitness_goals, k=random.randint(1, 2)))

            # Add random restricted health conditions (0-2)
            if random.choice([True, False]):
                meal.restricted_health_conditions.set(
                    random.sample(health_conditions, k=random.randint(0, 2))
                )

            # Add random restricted allergies (0-3)
            if random.choice([True, False]):
                meal.restricted_allergies.set(
                    random.sample(allergies, k=random.randint(0, 3))
                )

            # Add cuisines (1-2)
            meal.cuisine.set(random.sample(cuisines, k=random.randint(1, 2)))

            created_meals += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_meals} meals with related data'
            )
        )