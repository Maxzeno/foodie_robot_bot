# DEPRECATED: This module is deprecated. Use api.tasks instead.
# These imports are kept for backwards compatibility.
from api.tasks.remind_user_to_reply import remind_users_to_reply_task
from api.tasks.recommend_meal import send_meal_recommendations_task

# Deprecated aliases
def remind_users_to_reply():
    """Deprecated: Use remind_users_to_reply_task from api.tasks instead."""
    import warnings
    warnings.warn(
        "remind_users_to_reply is deprecated. Use remind_users_to_reply_task from api.tasks instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return remind_users_to_reply_task.call_local()


def send_meal_recommendations():
    """Deprecated: Use send_meal_recommendations_task from api.tasks instead."""
    import warnings
    warnings.warn(
        "send_meal_recommendations is deprecated. Use send_meal_recommendations_task from api.tasks instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return send_meal_recommendations_task.call_local()
