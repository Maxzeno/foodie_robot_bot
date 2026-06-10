# Import all tasks so they get registered with Huey
from api.tasks.remind_user_to_reply import remind_users_to_reply_task
from api.tasks.recommend_meal import send_meal_recommendations_task
from api.tasks.send_template_to_important_users import (
    send_template_to_important_users,
    send_template_to_important_users_task,
    get_important_users_preview
)

__all__ = [
    'remind_users_to_reply_task',
    'send_meal_recommendations_task',
    'send_template_to_important_users',
    'send_template_to_important_users_task',
    'get_important_users_preview',
]
