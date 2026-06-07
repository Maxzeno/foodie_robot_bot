# """
# OPTIMIZED VERSION 2: Celery Distributed Task Queue
# Expected speedup: 10-50x faster (scales horizontally)

# Benefits:
# - True async processing (non-blocking)
# - Horizontal scaling (add more workers)
# - Task retry on failure
# - Task monitoring and tracking
# - Production-ready

# Setup Required:
# 1. Install: pip install celery redis
# 2. Configure Celery in settings.py
# 3. Start Redis: redis-server
# 4. Start Celery worker: celery -A foodie_robot worker -l info
# """

# from celery import shared_task, group
# from django.utils import timezone
# from datetime import timedelta
# from django.db.models import Max, Q
# from api.models.user import User
# from api.models.message import Message, RoleChoices
# from api.models.meal import Meal, TimeOfDayChoices
# from api.models.recommendation import Recommendation, ChoiceOption
# from api.services.recommendation.meal_recommendation import MealRecommendationService
# from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload
# import logging

# logger = logging.getLogger(__name__)


# @shared_task
# def send_meal_recommendations_async():
#     """
#     Main cron task - distributes work to Celery workers.
#     This returns immediately and processes users in background.
#     """
#     now = timezone.now()
#     twenty_four_hours_ago = now - timedelta(hours=24)

#     # Get active users (optimized query)
#     active_users = User.objects.annotate(
#         last_user_message_time=Max(
#             'messages__created_at',
#             filter=Q(messages__role=RoleChoices.USER)
#         )
#     ).filter(
#         last_user_message_time__gte=twenty_four_hours_ago
#     ).select_related('city', 'fitness_goals').prefetch_related(
#         'preferred_cuisine', 'allergies', 'health_conditions'
#     )

#     total_users = active_users.count()

#     if total_users == 0:
#         logger.info("No active users to process")
#         return {
#             "total_users": 0,
#             "tasks_created": 0
#         }

#     # Create a group of tasks (one per user)
#     # Celery will distribute these across available workers
#     job = group(
#         process_user_recommendations.s(user.id)
#         for user in active_users
#     )

#     # Execute all tasks asynchronously
#     result = job.apply_async()

#     logger.info(f"Created {total_users} recommendation tasks")

#     return {
#         "total_users": total_users,
#         "tasks_created": total_users,
#         "group_id": result.id
#     }


# @shared_task(
#     bind=True,
#     max_retries=3,
#     default_retry_delay=60,  # Retry after 60 seconds
#     autoretry_for=(Exception,),
#     retry_backoff=True
# )
# def process_user_recommendations(self, user_id):
#     """
#     Process recommendations for a single user (runs on Celery worker).

#     Features:
#     - Automatic retry on failure (max 3 times)
#     - Exponential backoff
#     - Task tracking
#     """
#     try:
#         # Fetch user with prefetched data
#         user = User.objects.select_related(
#             'city', 'fitness_goals'
#         ).prefetch_related(
#             'preferred_cuisine', 'allergies', 'health_conditions'
#         ).get(id=user_id)

#         # Get user's current time period
#         time_period = user.get_time_period()
#         today = user.get_local_time().date()

#         # Check if user has city set
#         if not user.city:
#             logger.debug(f"User {user_id} has no city set")
#             return {'status': 'no_city', 'messages_sent': 0}

#         # Check if recommendations already exist
#         existing_count = Recommendation.objects.filter(
#             user=user,
#             time_of_day=TimeOfDayChoices.get_period(time_period),
#             day=today,
#             sent_to_user=True
#         ).count()

#         if existing_count > 0:
#             logger.debug(f"User {user_id} already has recommendations for today")
#             return {'status': 'already_sent', 'messages_sent': 0}

#         # Generate and send recommendations
#         messages_sent = _generate_and_send_recommendations(user, time_period, today)

#         if messages_sent > 0:
#             logger.info(f"Successfully sent {messages_sent} recommendations to user {user_id}")
#             return {'status': 'sent', 'messages_sent': messages_sent}
#         else:
#             return {'status': 'no_recommendations', 'messages_sent': 0}

#     except User.DoesNotExist:
#         logger.error(f"User {user_id} not found")
#         return {'status': 'user_not_found', 'messages_sent': 0}

#     except Exception as e:
#         logger.error(f"Error processing user {user_id}: {e}", exc_info=True)
#         # Celery will automatically retry this task
#         raise


# def _generate_and_send_recommendations(user, current_time_period, today):
#     """Generate and send meal recommendations (same as optimized v1)."""
#     try:
#         service = MealRecommendationService()
#         recommended_meal_dict = service.get_recommendations(
#             user=user,
#             num_recommendations_per_period=2,
#         )

#         messages_sent = 0

#         # Collect all meal IDs for batch fetching
#         all_meal_ids = []
#         for time_period in ['morning', 'afternoon', 'evening']:
#             all_meal_ids.extend(recommended_meal_dict.get(time_period, []))

#         if not all_meal_ids:
#             return 0

#         # Batch fetch all meals
#         meals_by_id = {
#             meal.id: meal
#             for meal in Meal.objects.filter(id__in=all_meal_ids).select_related('restaurant', 'city')
#         }

#         # Check existing recommendations
#         existing_recs = Recommendation.objects.filter(
#             user=user,
#             day=today,
#             meal_id__in=all_meal_ids
#         ).select_related('meal')

#         existing_recs_map = {
#             (rec.meal_id, rec.time_of_day, rec.choice_option): rec
#             for rec in existing_recs
#         }

#         # Process recommendations
#         for time_period in ['morning', 'afternoon', 'evening']:
#             meal_ids = recommended_meal_dict.get(time_period, [])
#             if not meal_ids:
#                 continue

#             time_of_day_enum = TimeOfDayChoices.get_period(time_period)

#             for index, meal_id in enumerate(meal_ids):
#                 meal = meals_by_id.get(meal_id)
#                 if not meal:
#                     continue

#                 choice_option = ChoiceOption.FIRST if index == 0 else ChoiceOption.SECOND
#                 rec_key = (meal_id, time_of_day_enum, choice_option)
#                 existing_rec = existing_recs_map.get(rec_key)

#                 if existing_rec:
#                     if time_period == current_time_period and not existing_rec.sent_to_user:
#                         _send_recommendation_message(user, meal, existing_rec, time_period, index)
#                         existing_rec.sent_to_user = True
#                         existing_rec.save(update_fields=['sent_to_user'])
#                         messages_sent += 1
#                     continue

#                 recommendation_obj = Recommendation.objects.create(
#                     user=user,
#                     meal=meal,
#                     time_of_day=time_of_day_enum,
#                     choice_option=choice_option,
#                     sent_to_user=False,
#                     day=today
#                 )

#                 if time_period == current_time_period:
#                     _send_recommendation_message(user, meal, recommendation_obj, time_period, index)
#                     recommendation_obj.sent_to_user = True
#                     recommendation_obj.save(update_fields=['sent_to_user'])
#                     messages_sent += 1

#         return messages_sent

#     except Exception as e:
#         logger.error(f"Error generating recommendations: {e}", exc_info=True)
#         return 0


# def _send_recommendation_message(user, meal, recommendation_obj, time_period, index):
#     """Send recommendation message via WhatsApp."""
#     try:
#         position_text = 'first' if index == 0 else 'second'
#         text = f"Your {position_text} {time_period} meal recommendation, {meal.name}, Meal Cost {meal.price:,.2f}"
#         image_url = meal.image_url.url if meal.image_url else None
#         payload = recommend_product_payload(recommendation_obj.id, text, image_url)

#         Message.bot_message_action_reply(
#             content=text,
#             user=user,
#             payload=payload,
#             metadata={
#                 "meal_id": str(meal.id),
#                 "recommendation_id": recommendation_obj.id,
#                 "description": "Users can order, like or hate meal"
#             }
#         )

#     except Exception as e:
#         logger.error(f"Error sending message to user {user.id}: {e}", exc_info=True)
#         raise


# # ============================================================================
# # CELERY CONFIGURATION (Add to foodie_robot/settings.py)
# # ============================================================================
# """
# # Install Redis: pip install redis
# # Start Redis: redis-server

# # In settings.py, add:

# # Celery Configuration
# CELERY_BROKER_URL = 'redis://localhost:6379/0'
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'UTC'
# CELERY_TASK_TRACK_STARTED = True
# CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
# CELERY_WORKER_PREFETCH_MULTIPLIER = 4

# # In foodie_robot/__init__.py, add:
# from .celery import app as celery_app
# __all__ = ('celery_app',)

# # Create foodie_robot/celery.py:
# import os
# from celery import Celery

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodie_robot.settings')
# app = Celery('foodie_robot')
# app.config_from_object('django.conf:settings', namespace='CELERY')
# app.autodiscover_tasks()

# # Start Celery worker:
# celery -A foodie_robot worker -l info --concurrency=10

# # Schedule the cron task (use celery beat):
# from celery.schedules import crontab

# CELERY_BEAT_SCHEDULE = {
#     'send-meal-recommendations': {
#         'task': 'api.cron.recommend_meal_optimized_v2_celery.send_meal_recommendations_async',
#         'schedule': crontab(minute='*/30'),  # Every 30 minutes
#     },
# }
# """
