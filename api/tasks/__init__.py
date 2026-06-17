# Import all tasks so they get registered with Huey
from api.tasks.remind_user_to_reply import remind_users_to_reply_task
from api.tasks.recommend_meal import send_meal_recommendations_task
from api.tasks.send_template_to_important_users import (
    send_template_to_important_users,
    send_template_to_important_users_task,
    get_important_users_preview
)
from api.tasks.analyze_meal_with_ai import analyze_meal_with_ai_task
from api.tasks.send_admin_message import (
    send_broadcast_message_task,
    send_single_user_message_task
)
from api.tasks.send_referral_message import send_referral_invitation_messages
from api.tasks.remind_incomplete_registration import remind_incomplete_registration

__all__ = [
    'remind_users_to_reply_task',
    'send_meal_recommendations_task',
    'send_template_to_important_users',
    'send_template_to_important_users_task',
    'get_important_users_preview',
    'analyze_meal_with_ai_task',
    'send_broadcast_message_task',
    'send_single_user_message_task',
    'send_referral_invitation_messages',
    'remind_incomplete_registration',
]
