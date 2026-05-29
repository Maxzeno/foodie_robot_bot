from django.core.management.base import BaseCommand
from faker import Faker
import random
from decimal import Decimal
from api.models.meal import (
    Meal, HealthCondition, Allergy, FitnessGoal, PreferredCuisine,
    TimeOfDayChoices, HealthConditionChoices, AllergyChoices,
    FitnessGoalChoices, CuisineChoices
)
from api.models.location import City
from api.models.restaurant import Restaurant


class Command(BaseCommand):
    help = 'Populate database with variety of meals, mainly Nigerian cuisine'

    def add_arguments(self, parser):
        parser.add_argument(
            '--meals',
            type=int,
            default=100,
            help='Number of meals to create (default: 100)'
        )

    def handle(self, *args, **options):
        fake = Faker()
        num_meals = options['meals']

        # Create reference data if not exists
        self.stdout.write('Creating/getting health conditions...')
        health_conditions = []
        for choice in HealthConditionChoices.choices:
            hc, created = HealthCondition.objects.get_or_create(
                name=choice[0],
                defaults={'description': f'{choice[1]} condition'}
            )
            health_conditions.append(hc)
            if created:
                self.stdout.write(f'  Created: {choice[1]}')

        self.stdout.write('Creating/getting allergies...')
        allergies = []
        for choice in AllergyChoices.choices:
            allergy, created = Allergy.objects.get_or_create(
                name=choice[0],
                defaults={'description': f'{choice[1]} allergy'}
            )
            allergies.append(allergy)
            if created:
                self.stdout.write(f'  Created: {choice[1]}')

        self.stdout.write('Creating/getting fitness goals...')
        fitness_goals = []
        for choice in FitnessGoalChoices.choices:
            goal, created = FitnessGoal.objects.get_or_create(
                name=choice[0],
                defaults={'description': f'{choice[1]} goal'}
            )
            fitness_goals.append(goal)
            if created:
                self.stdout.write(f'  Created: {choice[1]}')

        self.stdout.write('Creating/getting cuisines...')
        cuisines = []
        for choice in CuisineChoices.choices:
            cuisine, created = PreferredCuisine.objects.get_or_create(
                name=choice[0],
                defaults={'description': f'{choice[1]} cuisine'}
            )
            cuisines.append(cuisine)
            if created:
                self.stdout.write(f'  Created: {choice[1]}')

        # Create helper dicts for quick lookup
        health_conditions_dict = {hc.name: hc for hc in health_conditions}
        allergies_dict = {a.name: a for a in allergies}
        fitness_goals_dict = {fg.name: fg for fg in fitness_goals}
        cuisines_dict = {c.name: c for c in cuisines}

        city = City.objects.get(name='Enugu')

        # Create sample restaurants
        self.stdout.write('Creating restaurants...')
        restaurants = []
        restaurant_names = [
            'Mama Cass Kitchen', 'Bukka Hut', 'Yakoyo Restaurant',
            'The Place Restaurant', 'Café Neo', 'Oriental Restaurant',
            'Chicken Republic', 'Tantalizers', 'Mr Biggs', 'Sweet Sensation'
        ]

        for name in restaurant_names:
            restaurant, created = Restaurant.objects.get_or_create(
                name=name,
                defaults={
                    'phone': fake.phone_number(),
                    'address': fake.address(),
                    'email': fake.email(),
                }
            )
            restaurants.append(restaurant)

        self.stdout.write(f'Creating {num_meals} meals...')

        # Comprehensive meal data with Nigerian focus
        meal_database = [
            # Nigerian Breakfast
            {
                'name': 'Akara and Pap',
                'description': 'Traditional Nigerian bean cakes served with fermented corn pudding',
                'price': (800, 1500),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.MORNING],
                'calories': (350, 450),
                'protein': (12, 18),
                'carbs': (45, 60),
                'fats': (12, 18),
                'fiber': (6, 10),
                'sugar': (8, 12),
                'sodium': (400, 600),
                'cholesterol': (0, 5),
                'serving_amount_g': (400, 500),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.SOY],
            },
            {
                'name': 'Moi Moi',
                'description': 'Steamed bean pudding made from blended black-eyed peas',
                'price': (1000, 1800),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.MORNING, TimeOfDayChoices.AFTERNOON],
                'calories': (200, 280),
                'protein': (15, 20),
                'carbs': (20, 30),
                'fats': (8, 12),
                'fiber': (5, 8),
                'sugar': (3, 5),
                'sodium': (300, 500),
                'cholesterol': (20, 40),
                'serving_amount_g': (300, 400),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.SOY, AllergyChoices.EGGS],
            },
            {
                'name': 'Yam and Egg Sauce',
                'description': 'Boiled yam served with scrambled eggs and vegetables',
                'price': (1200, 2000),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.MORNING],
                'calories': (400, 500),
                'protein': (15, 22),
                'carbs': (55, 70),
                'fats': (10, 15),
                'fiber': (4, 7),
                'sugar': (5, 8),
                'sodium': (350, 550),
                'cholesterol': (280, 350),
                'serving_amount_g': (450, 550),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.EGGS],
            },
            {
                'name': 'Plantain and Eggs',
                'description': 'Fried ripe plantains served with scrambled eggs',
                'price': (1500, 2200),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.MORNING, TimeOfDayChoices.AFTERNOON],
                'calories': (450, 550),
                'protein': (12, 18),
                'carbs': (60, 75),
                'fats': (18, 25),
                'fiber': (5, 7),
                'sugar': (25, 35),
                'sodium': (300, 450),
                'cholesterol': (280, 350),
                'serving_amount_g': (400, 500),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.EGGS],
            },
            {
                'name': 'Beans Porridge',
                'description': 'Savory beans cooked with plantain, palm oil and spices',
                'price': (1200, 2000),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.MORNING, TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (350, 450),
                'protein': (18, 24),
                'carbs': (50, 65),
                'fats': (8, 14),
                'fiber': (12, 18),
                'sugar': (6, 10),
                'sodium': (400, 650),
                'cholesterol': (0, 0),
                'serving_amount_g': (450, 600),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.SOY],
            },
            {
                'name': 'Yam Porridge (Asaro)',
                'description': 'Yam cooked in rich pepper sauce with fish or meat',
                'price': (1500, 2500),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (400, 520),
                'protein': (15, 22),
                'carbs': (60, 75),
                'fats': (12, 18),
                'fiber': (6, 9),
                'sugar': (8, 12),
                'sodium': (500, 750),
                'cholesterol': (25, 50),
                'serving_amount_g': (500, 650),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.SEAFOOD],
            },

            # Nigerian Main Dishes
            {
                'name': 'Jollof Rice with Chicken',
                'description': 'Iconic Nigerian rice dish cooked in tomato sauce with grilled chicken',
                'price': (2000, 3500),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (550, 700),
                'protein': (30, 40),
                'carbs': (70, 90),
                'fats': (18, 28),
                'fiber': (4, 7),
                'sugar': (8, 12),
                'sodium': (800, 1200),
                'cholesterol': (80, 120),
                'serving_amount_g': (550, 700),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE, FitnessGoalChoices.MUSCLE_GAIN],
            },
            {
                'name': 'Jollof Rice with Beef',
                'description': 'Classic jollof rice served with tender beef',
                'price': (2200, 3800),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (600, 750),
                'protein': (32, 42),
                'carbs': (70, 90),
                'fats': (22, 32),
                'fiber': (4, 7),
                'sugar': (8, 12),
                'sodium': (850, 1250),
                'cholesterol': (90, 130),
                'serving_amount_g': (550, 700),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE, FitnessGoalChoices.MUSCLE_GAIN],
            },
            {
                'name': 'Fried Rice with Chicken',
                'description': 'Colorful Nigerian-style fried rice with vegetables and chicken',
                'price': (2000, 3500),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (520, 680),
                'protein': (28, 38),
                'carbs': (65, 85),
                'fats': (18, 26),
                'fiber': (5, 8),
                'sugar': (6, 10),
                'sodium': (750, 1100),
                'cholesterol': (80, 115),
                'serving_amount_g': (550, 700),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE, FitnessGoalChoices.MUSCLE_GAIN],
            },
            {
                'name': 'Coconut Rice with Fish',
                'description': 'Fragrant rice cooked in coconut milk served with grilled fish',
                'price': (2500, 4000),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (580, 720),
                'protein': (30, 40),
                'carbs': (68, 85),
                'fats': (22, 32),
                'fiber': (3, 6),
                'sugar': (5, 8),
                'sodium': (600, 900),
                'cholesterol': (70, 100),
                'serving_amount_g': (550, 700),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.SEAFOOD],
            },
            {
                'name': 'Ofada Rice with Ayamase Sauce',
                'description': 'Local unpolished rice with spicy green pepper sauce and assorted meat',
                'price': (2800, 4500),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (650, 800),
                'protein': (35, 45),
                'carbs': (75, 95),
                'fats': (25, 35),
                'fiber': (6, 10),
                'sugar': (5, 8),
                'sodium': (900, 1300),
                'cholesterol': (100, 140),
                'serving_amount_g': (600, 750),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN, FitnessGoalChoices.MAINTENANCE],
            },
            {
                'name': 'Jollof Spaghetti',
                'description': 'Nigerian-style spaghetti cooked in tomato sauce with vegetables',
                'price': (1800, 2800),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (480, 620),
                'protein': (18, 26),
                'carbs': (75, 95),
                'fats': (12, 20),
                'fiber': (5, 8),
                'sugar': (8, 12),
                'sodium': (700, 1000),
                'cholesterol': (20, 40),
                'serving_amount_g': (500, 650),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.GLUTEN],
            },

            # Nigerian Soups
            {
                'name': 'Egusi Soup with Pounded Yam',
                'description': 'Melon seed soup with assorted meat and fish served with pounded yam',
                'price': (2500, 4000),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (700, 850),
                'protein': (35, 48),
                'carbs': (85, 110),
                'fats': (28, 38),
                'fiber': (8, 12),
                'sugar': (6, 10),
                'sodium': (800, 1200),
                'cholesterol': (90, 130),
                'serving_amount_g': (650, 800),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.SEAFOOD, AllergyChoices.TREE_NUTS],
            },
            {
                'name': 'Efo Riro with Pounded Yam',
                'description': 'Vegetable soup with assorted meat served with pounded yam',
                'price': (2500, 4000),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (680, 820),
                'protein': (32, 45),
                'carbs': (90, 115),
                'fats': (22, 32),
                'fiber': (10, 15),
                'sugar': (8, 12),
                'sodium': (750, 1150),
                'cholesterol': (85, 125),
                'serving_amount_g': (650, 800),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN, FitnessGoalChoices.MAINTENANCE],
            },
            {
                'name': 'Ogbono Soup with Fufu',
                'description': 'Draw soup made from ground ogbono seeds with assorted meat and fufu',
                'price': (2300, 3800),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (650, 800),
                'protein': (30, 42),
                'carbs': (85, 105),
                'fats': (25, 35),
                'fiber': (12, 18),
                'sugar': (5, 8),
                'sodium': (700, 1100),
                'cholesterol': (80, 120),
                'serving_amount_g': (650, 800),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN, FitnessGoalChoices.MAINTENANCE],
            },
            {
                'name': 'Okra Soup with Eba',
                'description': 'Slimy okra soup with seafood and meat served with garri (eba)',
                'price': (2200, 3500),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (600, 750),
                'protein': (28, 40),
                'carbs': (80, 100),
                'fats': (18, 28),
                'fiber': (10, 15),
                'sugar': (5, 8),
                'sodium': (650, 1000),
                'cholesterol': (75, 110),
                'serving_amount_g': (600, 750),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.SEAFOOD],
            },
            {
                'name': 'Edikang Ikong Soup',
                'description': 'Nutritious vegetable soup with waterleaf and fluted pumpkin leaves',
                'price': (3000, 4500),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (720, 880),
                'protein': (38, 50),
                'carbs': (85, 110),
                'fats': (28, 38),
                'fiber': (12, 18),
                'sugar': (6, 10),
                'sodium': (800, 1200),
                'cholesterol': (95, 135),
                'serving_amount_g': (700, 850),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.SEAFOOD],
            },
            {
                'name': 'Afang Soup with Garri',
                'description': 'Wild vegetable soup with waterleaf served with eba',
                'price': (2800, 4200),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (700, 850),
                'protein': (35, 48),
                'carbs': (88, 112),
                'fats': (26, 36),
                'fiber': (14, 20),
                'sugar': (6, 10),
                'sodium': (750, 1150),
                'cholesterol': (90, 130),
                'serving_amount_g': (700, 850),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.SEAFOOD],
            },
            {
                'name': 'Banga Soup with Starch',
                'description': 'Palm nut soup served with cassava starch',
                'price': (2500, 4000),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (680, 830),
                'protein': (32, 44),
                'carbs': (82, 105),
                'fats': (28, 38),
                'fiber': (7, 11),
                'sugar': (5, 8),
                'sodium': (700, 1100),
                'cholesterol': (85, 125),
                'serving_amount_g': (650, 800),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.SEAFOOD],
            },
            {
                'name': 'Pepper Soup (Goat Meat)',
                'description': 'Spicy aromatic broth with goat meat and traditional spices',
                'price': (2500, 4000),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.EVENING],
                'calories': (320, 420),
                'protein': (35, 48),
                'carbs': (8, 15),
                'fats': (15, 22),
                'fiber': (2, 4),
                'sugar': (3, 6),
                'sodium': (900, 1300),
                'cholesterol': (95, 135),
                'serving_amount_g': (450, 600),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MUSCLE_GAIN],
            },
            {
                'name': 'Catfish Pepper Soup',
                'description': 'Spicy fish broth with fresh catfish and aromatic spices',
                'price': (2800, 4500),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.EVENING],
                'calories': (280, 380),
                'protein': (32, 45),
                'carbs': (5, 12),
                'fats': (12, 18),
                'fiber': (2, 4),
                'sugar': (2, 5),
                'sodium': (850, 1250),
                'cholesterol': (80, 115),
                'serving_amount_g': (450, 600),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.SEAFOOD],
            },

            # Nigerian Snacks & Specials
            {
                'name': 'Suya Plate',
                'description': 'Spicy grilled beef skewers with onions and peppers',
                'price': (1500, 3000),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (450, 600),
                'protein': (40, 55),
                'carbs': (10, 18),
                'fats': (28, 38),
                'fiber': (3, 5),
                'sugar': (4, 7),
                'sodium': (800, 1200),
                'cholesterol': (110, 150),
                'serving_amount_g': (300, 450),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.PEANUTS],
            },
            {
                'name': 'Nkwobi',
                'description': 'Spicy cow foot delicacy in palm oil sauce',
                'price': (2000, 3500),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (550, 700),
                'protein': (35, 48),
                'carbs': (8, 15),
                'fats': (38, 50),
                'fiber': (2, 4),
                'sugar': (3, 6),
                'sodium': (950, 1350),
                'cholesterol': (180, 250),
                'serving_amount_g': (350, 500),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_health_conditions': [HealthConditionChoices.HIGH_CHOLESTEROL, HealthConditionChoices.HYPERTENSION],
            },
            {
                'name': 'Abacha (African Salad)',
                'description': 'Cassava-based salad with ugba, fish, and vegetables',
                'price': (1800, 3000),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (380, 500),
                'protein': (18, 28),
                'carbs': (45, 60),
                'fats': (15, 22),
                'fiber': (8, 12),
                'sugar': (5, 8),
                'sodium': (600, 900),
                'cholesterol': (40, 70),
                'serving_amount_g': (400, 550),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.SEAFOOD],
            },
            {
                'name': 'Gizdodo',
                'description': 'Gizzard and plantain stir-fry in peppered sauce',
                'price': (2200, 3500),
                'cuisine': [CuisineChoices.NIGERIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (520, 680),
                'protein': (28, 38),
                'carbs': (50, 68),
                'fats': (22, 32),
                'fiber': (5, 8),
                'sugar': (20, 28),
                'sodium': (750, 1100),
                'cholesterol': (220, 300),
                'serving_amount_g': (450, 600),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_health_conditions': [HealthConditionChoices.HIGH_CHOLESTEROL],
            },

            # International dishes
            {
                'name': 'Grilled Chicken Salad',
                'description': 'Fresh mixed greens with grilled chicken breast and vinaigrette',
                'price': (2000, 3200),
                'cuisine': [CuisineChoices.AMERICAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (280, 380),
                'protein': (32, 42),
                'carbs': (15, 25),
                'fats': (10, 16),
                'fiber': (5, 8),
                'sugar': (6, 10),
                'sodium': (450, 700),
                'cholesterol': (75, 105),
                'serving_amount_g': (350, 500),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MUSCLE_GAIN],
            },
            {
                'name': 'Caesar Salad',
                'description': 'Romaine lettuce with parmesan, croutons, and Caesar dressing',
                'price': (1800, 2800),
                'cuisine': [CuisineChoices.AMERICAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (350, 480),
                'protein': (12, 18),
                'carbs': (25, 38),
                'fats': (22, 32),
                'fiber': (3, 6),
                'sugar': (4, 7),
                'sodium': (700, 1000),
                'cholesterol': (45, 70),
                'serving_amount_g': (350, 500),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.DAIRY, AllergyChoices.GLUTEN],
            },
            {
                'name': 'Pasta Carbonara',
                'description': 'Creamy Italian pasta with bacon, eggs, and parmesan',
                'price': (2500, 4000),
                'cuisine': [CuisineChoices.ITALIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (650, 800),
                'protein': (28, 38),
                'carbs': (75, 95),
                'fats': (30, 42),
                'fiber': (3, 6),
                'sugar': (5, 8),
                'sodium': (900, 1300),
                'cholesterol': (220, 300),
                'serving_amount_g': (450, 600),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.GLUTEN, AllergyChoices.DAIRY, AllergyChoices.EGGS],
                'restricted_health_conditions': [HealthConditionChoices.HIGH_CHOLESTEROL],
            },
            {
                'name': 'Margherita Pizza',
                'description': 'Classic Italian pizza with tomato, mozzarella, and basil',
                'price': (2800, 4500),
                'cuisine': [CuisineChoices.ITALIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (600, 750),
                'protein': (24, 32),
                'carbs': (80, 100),
                'fats': (22, 32),
                'fiber': (4, 7),
                'sugar': (8, 12),
                'sodium': (1000, 1400),
                'cholesterol': (50, 80),
                'serving_amount_g': (500, 650),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.GLUTEN, AllergyChoices.DAIRY],
            },
            {
                'name': 'Chicken Shawarma',
                'description': 'Middle Eastern wrap with grilled chicken and garlic sauce',
                'price': (1500, 2500),
                'cuisine': [CuisineChoices.MOROCCAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (480, 620),
                'protein': (32, 42),
                'carbs': (55, 70),
                'fats': (16, 24),
                'fiber': (4, 7),
                'sugar': (6, 10),
                'sodium': (850, 1200),
                'cholesterol': (80, 115),
                'serving_amount_g': (400, 550),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.GLUTEN, AllergyChoices.DAIRY],
            },
            {
                'name': 'Pad Thai',
                'description': 'Thai stir-fried rice noodles with shrimp, peanuts, and tamarind',
                'price': (2500, 3800),
                'cuisine': [CuisineChoices.THAI],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (550, 700),
                'protein': (24, 34),
                'carbs': (70, 90),
                'fats': (20, 30),
                'fiber': (4, 7),
                'sugar': (15, 22),
                'sodium': (1200, 1600),
                'cholesterol': (120, 160),
                'serving_amount_g': (450, 600),
                'fitness_goals': [FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.SEAFOOD, AllergyChoices.PEANUTS, AllergyChoices.EGGS],
            },
            {
                'name': 'Butter Chicken with Rice',
                'description': 'Creamy Indian curry with tender chicken and basmati rice',
                'price': (2800, 4200),
                'cuisine': [CuisineChoices.INDIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (650, 800),
                'protein': (35, 45),
                'carbs': (75, 95),
                'fats': (28, 38),
                'fiber': (4, 7),
                'sugar': (10, 15),
                'sodium': (950, 1350),
                'cholesterol': (100, 140),
                'serving_amount_g': (550, 700),
                'fitness_goals': [FitnessGoalChoices.MUSCLE_GAIN, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.DAIRY],
            },
            {
                'name': 'Sushi Platter',
                'description': 'Assorted Japanese sushi rolls with fresh fish and vegetables',
                'price': (3500, 5500),
                'cuisine': [CuisineChoices.JAPANESE],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (420, 550),
                'protein': (28, 38),
                'carbs': (65, 85),
                'fats': (8, 14),
                'fiber': (3, 6),
                'sugar': (8, 12),
                'sodium': (1200, 1800),
                'cholesterol': (55, 85),
                'serving_amount_g': (450, 600),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.SEAFOOD, AllergyChoices.SOY],
            },
            {
                'name': 'Greek Yogurt Bowl',
                'description': 'Protein-rich yogurt with granola, berries, and honey',
                'price': (1500, 2500),
                'cuisine': [CuisineChoices.GREEK],
                'times_of_day': [TimeOfDayChoices.MORNING, TimeOfDayChoices.AFTERNOON],
                'calories': (280, 380),
                'protein': (18, 25),
                'carbs': (40, 55),
                'fats': (8, 14),
                'fiber': (5, 8),
                'sugar': (22, 30),
                'sodium': (150, 250),
                'cholesterol': (25, 40),
                'serving_amount_g': (350, 500),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.DAIRY, AllergyChoices.TREE_NUTS],
            },
            {
                'name': 'Vegetable Stir Fry',
                'description': 'Colorful mixed vegetables in Asian-style sauce',
                'price': (1500, 2500),
                'cuisine': [CuisineChoices.CHINESE, CuisineChoices.VEGAN_VEGETARIAN],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (220, 320),
                'protein': (8, 14),
                'carbs': (35, 48),
                'fats': (8, 14),
                'fiber': (8, 12),
                'sugar': (10, 15),
                'sodium': (700, 1000),
                'cholesterol': (0, 0),
                'serving_amount_g': (400, 550),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MAINTENANCE],
                'restricted_allergies': [AllergyChoices.SOY],
            },
            {
                'name': 'Salmon Teriyaki',
                'description': 'Grilled salmon glazed with teriyaki sauce and vegetables',
                'price': (3500, 5000),
                'cuisine': [CuisineChoices.JAPANESE],
                'times_of_day': [TimeOfDayChoices.AFTERNOON, TimeOfDayChoices.EVENING],
                'calories': (420, 550),
                'protein': (38, 50),
                'carbs': (28, 40),
                'fats': (18, 26),
                'fiber': (3, 6),
                'sugar': (12, 18),
                'sodium': (1100, 1500),
                'cholesterol': (85, 120),
                'serving_amount_g': (450, 600),
                'fitness_goals': [FitnessGoalChoices.WEIGHT_LOSS, FitnessGoalChoices.MUSCLE_GAIN],
                'restricted_allergies': [AllergyChoices.SEAFOOD, AllergyChoices.SOY],
            },
        ]

        created_meals = 0
        meals_to_create = min(num_meals, len(meal_database))

        # Shuffle for variety
        random.shuffle(meal_database)

        for i in range(meals_to_create):
            meal_data = meal_database[i % len(meal_database)]
            restaurant = random.choice(restaurants)

            # Generate values within ranges
            meal = Meal.objects.create(
                name=meal_data['name'],
                description=meal_data['description'],
                price=Decimal(random.uniform(*meal_data['price'])).quantize(Decimal('0.01')),
                city=city,
                restaurant=restaurant,
                image_url=None,  # Can be added later
                available=random.choice([True, True, True, False]),  # 75% available
                times_of_day=meal_data['times_of_day'],
                calories=Decimal(random.uniform(*meal_data['calories'])).quantize(Decimal('0.01')),
                protein=Decimal(random.uniform(*meal_data['protein'])).quantize(Decimal('0.01')),
                carbs=Decimal(random.uniform(*meal_data['carbs'])).quantize(Decimal('0.01')),
                fats=Decimal(random.uniform(*meal_data['fats'])).quantize(Decimal('0.01')),
                fiber=Decimal(random.uniform(*meal_data['fiber'])).quantize(Decimal('0.01')),
                sugar=Decimal(random.uniform(*meal_data['sugar'])).quantize(Decimal('0.01')),
                sodium=Decimal(random.uniform(*meal_data['sodium'])).quantize(Decimal('0.01')),
                cholesterol=Decimal(random.uniform(*meal_data['cholesterol'])).quantize(Decimal('0.01')),
                serving_amount_g=Decimal(random.uniform(*meal_data['serving_amount_g'])).quantize(Decimal('0.01')),
            )

            # Set fitness goals
            fitness_goal_objects = [
                fitness_goals_dict[fg] for fg in meal_data.get('fitness_goals', [])
                if fg in fitness_goals_dict
            ]
            if fitness_goal_objects:
                meal.fitness_goals.set(fitness_goal_objects)
            else:
                # Default to random if none specified
                meal.fitness_goals.set(random.sample(fitness_goals, k=random.randint(1, 2)))

            # Set restricted health conditions
            health_condition_objects = [
                health_conditions_dict[hc] for hc in meal_data.get('restricted_health_conditions', [])
                if hc in health_conditions_dict
            ]
            if health_condition_objects:
                meal.restricted_health_conditions.set(health_condition_objects)

            # Set restricted allergies
            allergy_objects = [
                allergies_dict[a] for a in meal_data.get('restricted_allergies', [])
                if a in allergies_dict
            ]
            if allergy_objects:
                meal.restricted_allergies.set(allergy_objects)

            # Set cuisines
            cuisine_objects = [
                cuisines_dict[c] for c in meal_data['cuisine']
                if c in cuisines_dict
            ]
            if cuisine_objects:
                meal.cuisine.set(cuisine_objects)
            else:
                # Fallback to random
                meal.cuisine.set(random.sample(cuisines, k=random.randint(1, 2)))

            created_meals += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_meals} meals with {len(restaurants)} restaurants'
            )
        )