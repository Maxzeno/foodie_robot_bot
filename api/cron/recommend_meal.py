# DEPRECATED: This module is deprecated. Use api.tasks.recommend_meal instead.
import warnings

from api.tasks.recommend_meal import send_meal_recommendations_task


def send_meal_recommendations():
    """
    DEPRECATED: Use send_meal_recommendations_task from api.tasks instead.

    This function is kept for backwards compatibility but will be removed in a future version.
    """
    warnings.warn(
        "send_meal_recommendations from api.cron is deprecated. "
        "Use send_meal_recommendations_task from api.tasks instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return send_meal_recommendations_task.call_local()
