# """
# OPTIMIZED VERSION 1: Parallel Processing with ThreadPoolExecutor
# Expected speedup: 5-10x faster for 1000 users

# Changes:
# - Parallel user processing with thread pool
# - Optimized database queries with prefetch_related
# - Batch operations where possible
# """

# from django.utils import timezone
# from datetime import timedelta
# from django.db.models import Max, Q, Prefetch
# from api.models.user import User
# from api.models.message import Message, RoleChoices
# from api.models.meal import Meal, TimeOfDayChoices
# from api.models.recommendation import Recommendation, ChoiceOption
# from api.services.recommendation.meal_recommendation import MealRecommendationService
# from api.utils.whatsapp_payload_helper.recommend_product import recommend_product_payload
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from threading import Lock
# import logging

# logger = logging.getLogger(__name__)

# # Thread-safe counters
# stats_lock = Lock()


# def send_meal_recommendations():
#     """
#     Optimized version using parallel processing.
#     Processes multiple users concurrently using ThreadPoolExecutor.
#     """
#     now = timezone.now()
#     twenty_four_hours_ago = now - timedelta(hours=24)

#     # OPTIMIZATION 1: Prefetch related data to avoid N+1 queries
#     active_users = User.objects.annotate(
#         last_user_message_time=Max(
#             'messages__created_at',
#             filter=Q(messages__role=RoleChoices.USER)
#         )
#     ).filter(
#         last_user_message_time__gte=twenty_four_hours_ago
#     ).select_related(
#         'city',  # Prefetch city to avoid separate queries
#         'fitness_goals',
#     ).prefetch_related(
#         'preferred_cuisine',
#         'allergies',
#         'health_conditions',
#     )

#     total_users = active_users.count()

#     if total_users == 0:
#         return {
#             "total_users": 0,
#             "users_sent": 0,
#             "users_skipped_no_city": 0,
#             "users_skipped_already_sent": 0,
#             "users_failed": 0,
#             "total_messages_sent": 0
#         }

#     # Thread-safe statistics
#     stats = {
#         "users_sent": 0,
#         "users_skipped_no_city": 0,
#         "users_skipped_already_sent": 0,
#         "users_failed": 0,
#         "total_messages_sent": 0,
#     }

#     # OPTIMIZATION 2: Parallel processing with ThreadPoolExecutor
#     # Adjust max_workers based on your server capacity
#     # Rule of thumb: 2-5x number of CPU cores for I/O-bound tasks
#     max_workers = 10  # Process 10 users concurrently

#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         # Submit all user processing tasks
#         future_to_user = {
#             executor.submit(_process_user_safe, user): user
#             for user in active_users
#         }

#         # Collect results as they complete
#         for future in as_completed(future_to_user):
#             user = future_to_user[future]
#             try:
#                 result = future.result()

#                 # Thread-safe update of statistics
#                 with stats_lock:
#                     if result['status'] == 'sent':
#                         stats['users_sent'] += 1
#                         stats['total_messages_sent'] += result['messages_sent']
#                     elif result['status'] == 'no_city':
#                         stats['users_skipped_no_city'] += 1
#                     elif result['status'] == 'already_sent':
#                         stats['users_skipped_already_sent'] += 1
#                     elif result['status'] == 'failed':
#                         stats['users_failed'] += 1

#             except Exception as e:
#                 logger.error(f"Error processing user {user.id}: {e}", exc_info=True)
#                 with stats_lock:
#                     stats['users_failed'] += 1

#     # Summary
#     result = {
#         "total_users": total_users,
#         **stats
#     }

#     logger.info(f"Recommendation cron completed: {result}")
#     return result


# def _process_user_safe(user: User):
#     """
#     Thread-safe wrapper for processing a single user.
#     Returns a dict with status and messages_sent.
#     """
#     try:
#         # Get user's current time period
#         time_period = user.get_time_period()
#         today = user.get_local_time().date()

#         # Check if user has city set
#         if not user.city:
#             return {'status': 'no_city', 'messages_sent': 0}

#         # OPTIMIZATION 3: Check if recommendations already exist (optimized query)
#         existing_count = Recommendation.objects.filter(
#             user=user,
#             time_of_day=TimeOfDayChoices.get_period(time_period),
#             day=today,
#             sent_to_user=True
#         ).count()

#         if existing_count > 0:
#             return {'status': 'already_sent', 'messages_sent': 0}

#         # Generate and send recommendations
#         messages_sent = _generate_and_send_recommendations(user, time_period, today)

#         if messages_sent > 0:
#             return {'status': 'sent', 'messages_sent': messages_sent}
#         else:
#             return {'status': 'failed', 'messages_sent': 0}

#     except Exception as e:
#         logger.error(f"Error processing user {user.id}: {e}", exc_info=True)
#         return {'status': 'failed', 'messages_sent': 0}


# def _generate_and_send_recommendations(user, current_time_period, today):
#     """
#     Generate and send meal recommendations for a user.
#     Optimized with batch queries.
#     """
#     try:
#         # Initialize recommendation service
#         service = MealRecommendationService()

#         # Generate recommendations for all time periods
#         recommended_meal_dict = service.get_recommendations(
#             user=user,
#             num_recommendations_per_period=2,
#         )

#         messages_sent = 0

#         # OPTIMIZATION 4: Collect all meal IDs first to batch-fetch
#         all_meal_ids = []
#         for time_period in ['morning', 'afternoon', 'evening']:
#             all_meal_ids.extend(recommended_meal_dict.get(time_period, []))

#         if not all_meal_ids:
#             return 0

#         # Batch fetch all meals at once (avoids N+1)
#         meals_by_id = {
#             meal.id: meal
#             for meal in Meal.objects.filter(id__in=all_meal_ids).select_related('restaurant', 'city')
#         }

#         # OPTIMIZATION 5: Check existing recommendations in one query
#         existing_recs = Recommendation.objects.filter(
#             user=user,
#             day=today,
#             meal_id__in=all_meal_ids
#         ).select_related('meal')

#         existing_recs_map = {
#             (rec.meal_id, rec.time_of_day, rec.choice_option): rec
#             for rec in existing_recs
#         }

#         # Process recommendations for all time periods
#         for time_period in ['morning', 'afternoon', 'evening']:
#             meal_ids = recommended_meal_dict.get(time_period, [])

#             if not meal_ids:
#                 continue

#             time_of_day_enum = TimeOfDayChoices.get_period(time_period)

#             # Create recommendation objects and send messages
#             for index, meal_id in enumerate(meal_ids):
#                 meal = meals_by_id.get(meal_id)
#                 if not meal:
#                     continue

#                 # Determine choice option (first or second)
#                 choice_option = ChoiceOption.FIRST if index == 0 else ChoiceOption.SECOND

#                 # Check if this recommendation already exists (from pre-fetched map)
#                 rec_key = (meal_id, time_of_day_enum, choice_option)
#                 existing_rec = existing_recs_map.get(rec_key)

#                 if existing_rec:
#                     # Recommendation already exists, just check if we need to send it
#                     if time_period == current_time_period and not existing_rec.sent_to_user:
#                         _send_recommendation_message(user, meal, existing_rec, time_period, index)
#                         existing_rec.sent_to_user = True
#                         existing_rec.save(update_fields=['sent_to_user'])
#                         messages_sent += 1
#                     continue

#                 # Create new recommendation object
#                 recommendation_obj = Recommendation.objects.create(
#                     user=user,
#                     meal=meal,
#                     time_of_day=time_of_day_enum,
#                     choice_option=choice_option,
#                     sent_to_user=False,  # FIXED: Set to False first
#                     day=today
#                 )

#                 # Send message only if this is the current time period
#                 if time_period == current_time_period:
#                     _send_recommendation_message(user, meal, recommendation_obj, time_period, index)
#                     # FIXED: Only mark as sent AFTER successful send
#                     recommendation_obj.sent_to_user = True
#                     recommendation_obj.save(update_fields=['sent_to_user'])
#                     messages_sent += 1

#         return messages_sent

#     except Exception as e:
#         logger.error(f"Error generating recommendations for user {user.id}: {e}", exc_info=True)
#         return 0


# def _send_recommendation_message(user, meal, recommendation_obj, time_period, index):
#     """Send recommendation message via WhatsApp."""
#     try:
#         # Format message text
#         position_text = 'first' if index == 0 else 'second'
#         text = f"Your {position_text} {time_period} meal recommendation, {meal.name}, Meal Cost {meal.price:,.2f}"

#         # Get image URL
#         image_url = meal.image_url.url if meal.image_url else None

#         # Create WhatsApp payload with action buttons
#         payload = recommend_product_payload(recommendation_obj.id, text, image_url)

#         # Send message
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
