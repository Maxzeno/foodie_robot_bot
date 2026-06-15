import logging
from django import db
from django.utils import timezone
from huey.contrib.djhuey import task

logger = logging.getLogger(__name__)


@task()
def send_broadcast_message_task(broadcast_message_id):
    """
    Task to send a broadcast message to all eligible users in selected cities.
    Only sends to users within the 24-hour free service window.

    Args:
        broadcast_message_id: ID of the BroadcastMessage to send
    """
    logger.info(f"Starting send_broadcast_message_task for message {broadcast_message_id}")

    # Close stale database connections
    db.close_old_connections()

    try:
        from api.models.admin_message import BroadcastMessage, MessageStatusChoices
        from api.models.message import Message, CurrentIntentChoices

        # Fetch the broadcast message
        try:
            broadcast = BroadcastMessage.objects.get(pk=broadcast_message_id)
        except BroadcastMessage.DoesNotExist:
            logger.error(f"BroadcastMessage {broadcast_message_id} not found")
            return

        # Update status to sending
        broadcast.status = MessageStatusChoices.SENDING
        broadcast.sent_at = timezone.now()
        broadcast.save(update_fields=['status', 'sent_at'])

        # Get eligible users
        eligible_users = broadcast.get_eligible_users()
        broadcast.total_eligible = eligible_users.count()
        broadcast.save(update_fields=['total_eligible'])

        logger.info(f"Found {broadcast.total_eligible} eligible users for broadcast {broadcast_message_id}")

        sent_count = 0
        failed_count = 0

        for user in eligible_users:
            try:
                if broadcast.image_url:
                    # Send message with image
                    Message.bot_message_image(
                        content=broadcast.content,
                        user=user,
                        preview_media=broadcast.image_url,
                        current_intent=CurrentIntentChoices.NO_INTENT
                    )
                else:
                    # Send text message
                    Message.bot_message(
                        content=broadcast.content,
                        user=user,
                        current_intent=CurrentIntentChoices.NO_INTENT,
                        metadata={"type": "broadcast", "broadcast_id": broadcast_message_id}
                    )
                sent_count += 1
                logger.debug(f"Sent broadcast to user {user.code}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to send broadcast to user {user.code}: {e}")

        # Update final status
        broadcast.sent_count = sent_count
        broadcast.failed_count = failed_count
        broadcast.status = MessageStatusChoices.COMPLETED
        broadcast.completed_at = timezone.now()
        broadcast.save(update_fields=['sent_count', 'failed_count', 'status', 'completed_at'])

        logger.info(
            f"Broadcast {broadcast_message_id} completed: "
            f"sent={sent_count}, failed={failed_count}, total_eligible={broadcast.total_eligible}"
        )

    except Exception as e:
        logger.error(f"Error in send_broadcast_message_task: {e}", exc_info=True)
        try:
            broadcast = BroadcastMessage.objects.get(pk=broadcast_message_id)
            broadcast.status = MessageStatusChoices.FAILED
            broadcast.error_message = str(e)
            broadcast.save(update_fields=['status', 'error_message'])
        except Exception:
            pass


@task()
def send_single_user_message_task(single_message_id):
    """
    Task to send a message to a single user.
    Only sends if the user is within the 24-hour free service window.

    Args:
        single_message_id: ID of the SingleUserMessage to send
    """
    logger.info(f"Starting send_single_user_message_task for message {single_message_id}")

    # Close stale database connections
    db.close_old_connections()

    try:
        from api.models.admin_message import SingleUserMessage, MessageStatusChoices
        from api.models.message import Message, CurrentIntentChoices

        # Fetch the message
        try:
            single_msg = SingleUserMessage.objects.get(pk=single_message_id)
        except SingleUserMessage.DoesNotExist:
            logger.error(f"SingleUserMessage {single_message_id} not found")
            return

        # Check if user is active (within 24-hour window)
        if not single_msg.is_user_active():
            single_msg.status = MessageStatusChoices.FAILED
            single_msg.error_message = "User is not within the 24-hour free service window"
            single_msg.save(update_fields=['status', 'error_message'])
            logger.warning(f"User {single_msg.user.code} is not active, message not sent")
            return

        # Update status to sending
        single_msg.status = MessageStatusChoices.SENDING
        single_msg.save(update_fields=['status'])

        try:
            if single_msg.image_url:
                # Send message with image
                Message.bot_message_image(
                    content=single_msg.content,
                    user=single_msg.user,
                    preview_media=single_msg.image_url,
                    current_intent=CurrentIntentChoices.NO_INTENT
                )
            else:
                # Send text message
                Message.bot_message(
                    content=single_msg.content,
                    user=single_msg.user,
                    current_intent=CurrentIntentChoices.NO_INTENT,
                    metadata={"type": "admin_single_message", "message_id": single_message_id}
                )

            single_msg.status = MessageStatusChoices.COMPLETED
            single_msg.sent_at = timezone.now()
            single_msg.save(update_fields=['status', 'sent_at'])
            logger.info(f"Successfully sent message to user {single_msg.user.code}")

        except Exception as e:
            single_msg.status = MessageStatusChoices.FAILED
            single_msg.error_message = str(e)
            single_msg.save(update_fields=['status', 'error_message'])
            logger.error(f"Failed to send message to user {single_msg.user.code}: {e}")

    except Exception as e:
        logger.error(f"Error in send_single_user_message_task: {e}", exc_info=True)
