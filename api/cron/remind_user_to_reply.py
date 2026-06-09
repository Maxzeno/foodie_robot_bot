# DEPRECATED: This module is deprecated. Use api.tasks.remind_user_to_reply instead.
import warnings

from api.tasks.remind_user_to_reply import remind_users_to_reply_task


def remind_users_to_reply():
    """
    DEPRECATED: Use remind_users_to_reply_task from api.tasks instead.

    This function is kept for backwards compatibility but will be removed in a future version.
    """
    warnings.warn(
        "remind_users_to_reply from api.cron is deprecated. "
        "Use remind_users_to_reply_task from api.tasks instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return remind_users_to_reply_task.call_local()
