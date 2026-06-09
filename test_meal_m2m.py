"""
Test script to verify ManyToMany relationships persist after signal
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodie_robot.settings')
django.setup()

from api.models.meal import Meal, FitnessGoal, HealthCondition, Allergy, PreferredCuisine
from django.db import transaction

# Find a recent meal
meal = Meal.objects.order_by('-created_at').first()

if not meal:
    print("No meals found in database")
    exit()

print(f"\n=== Testing Meal: {meal.name} (ID: {meal.id}) ===\n")

# Check what's actually saved in the database
print(f"Fitness Goals: {list(meal.fitness_goals.values_list('name', flat=True))}")
print(f"Health Conditions: {list(meal.restricted_health_conditions.values_list('name', flat=True))}")
print(f"Allergies: {list(meal.restricted_allergies.values_list('name', flat=True))}")
print(f"Cuisines: {list(meal.cuisine.values_list('name', flat=True))}")

print(f"\nNutritional Info:")
print(f"  Calories: {meal.calories}")
print(f"  Protein: {meal.protein}g")
print(f"  Carbs: {meal.carbs}g")
print(f"  Times of day: {meal.times_of_day}")

# Now try manually setting and verify it persists
print(f"\n=== Manual Test: Setting fitness goals manually ===\n")

with transaction.atomic():
    fitness_goals = FitnessGoal.objects.filter(name__in=['maintenance', 'muscle_gain'])
    print(f"Found {fitness_goals.count()} fitness goals: {list(fitness_goals.values_list('name', flat=True))}")

    meal.fitness_goals.set(fitness_goals)
    print(f"After .set(): {list(meal.fitness_goals.all())}")

# Re-fetch from database to verify persistence
meal.refresh_from_db()
print(f"After refresh_from_db(): {list(meal.fitness_goals.values_list('name', flat=True))}")

# Fetch a completely new instance
meal_new = Meal.objects.get(pk=meal.pk)
print(f"Fresh instance from DB: {list(meal_new.fitness_goals.values_list('name', flat=True))}")
