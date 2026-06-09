# Import all tasks so they get registered with Huey
from api.tasks.remind_user_to_reply import remind_users_to_reply_task
from api.tasks.recommend_meal import send_meal_recommendations_task

__all__ = [
    'remind_users_to_reply_task',
    'send_meal_recommendations_task',
]
