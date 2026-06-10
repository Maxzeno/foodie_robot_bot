import logging
from huey.contrib.djhuey import task

from django.utils import timezone
from datetime import timedelta
from django.db.models import Max, Min, Q, Count, Sum, Case, When, Value, IntegerField

logger = logging.getLogger(__name__)


def _calculate_user_importance_scores_internal(limit=100):
    """
    Calculate importance scores for users based on multiple factors.
    Only includes users OUTSIDE the 24-hour WhatsApp free messaging window.

    Scoring weights:
    - Has ordered before: 50 points (very important per requirement)
    - Total orders count: 5 points per order (max 50)
    - Total spending: 1 point per 1000 units spent (max 30)
    - Message count: 1 point per 10 messages (max 20)
    - Days active: 2 points per day active (max 30)
    - Reviews written: 5 points per review (max 20)
    - Referrals made: 10 points per referral (max 30)
    - Recommendation acceptance rate: up to 20 points
    """
    from api.models.user import User
    from api.models.message import RoleChoices

    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)

    # Get users with their last user message time - must be OUTSIDE 24-hour window
    users_outside_window = User.objects.annotate(
        last_user_message_time=Max(
            'messages__created_at',
            filter=Q(messages__role=RoleChoices.USER)
        )
    ).filter(
        # Must have sent at least one message (they're a real user)
        last_user_message_time__isnull=False,
        # Must be outside the 24-hour free window
        last_user_message_time__lt=twenty_four_hours_ago
    )

    # Annotate with activity metrics
    users_with_metrics = users_outside_window.annotate(
        # Order metrics
        total_orders=Count('orders', distinct=True),
        has_ordered=Case(
            When(total_orders__gt=0, then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        ),
        total_spending=Sum('orders__total_price'),

        # Message metrics
        total_messages=Count(
            'messages',
            filter=Q(messages__role=RoleChoices.USER),
            distinct=True
        ),

        # Days active (first message to last message span)
        first_message_time=Min(
            'messages__created_at',
            filter=Q(messages__role=RoleChoices.USER)
        ),

        # Review metrics
        total_reviews=Count('reviews', distinct=True),

        # Referral metrics
        total_referrals=Count('referrals', distinct=True),

        # Recommendation metrics
        total_recommendations=Count('recommendations', distinct=True),
        accepted_recommendations=Count(
            'recommendations',
            filter=Q(recommendations__accepted=True),
            distinct=True
        ),
    )

    # Calculate scores in Python for more complex logic
    scored_users = []

    for user in users_with_metrics:
        score = 0
        score_breakdown = {}

        # Has ordered before - VERY IMPORTANT (50 points)
        if user.has_ordered:
            score += 50
            score_breakdown['has_ordered'] = 50

        # Total orders (5 points per order, max 50)
        order_score = min(user.total_orders * 5, 50)
        score += order_score
        score_breakdown['orders'] = order_score

        # Total spending (1 point per 1000, max 30)
        if user.total_spending:
            spending_score = min(int(user.total_spending / 1000), 30)
            score += spending_score
            score_breakdown['spending'] = spending_score

        # Message count (1 point per 10 messages, max 20)
        message_score = min(user.total_messages // 10, 20)
        score += message_score
        score_breakdown['messages'] = message_score

        # Days active (2 points per day, max 30)
        if user.first_message_time and user.last_user_message_time:
            days_active = (user.last_user_message_time - user.first_message_time).days + 1
            days_score = min(days_active * 2, 30)
            score += days_score
            score_breakdown['days_active'] = days_score

        # Reviews written (5 points per review, max 20)
        review_score = min(user.total_reviews * 5, 20)
        score += review_score
        score_breakdown['reviews'] = review_score

        # Referrals made (10 points per referral, max 30)
        referral_score = min(user.total_referrals * 10, 30)
        score += referral_score
        score_breakdown['referrals'] = referral_score

        # Recommendation acceptance rate (up to 20 points)
        if user.total_recommendations > 0:
            acceptance_rate = user.accepted_recommendations / user.total_recommendations
            acceptance_score = int(acceptance_rate * 20)
            score += acceptance_score
            score_breakdown['acceptance_rate'] = acceptance_score

        scored_users.append({
            'user': user,
            'score': score,
            'breakdown': score_breakdown,
            'metrics': {
                'total_orders': user.total_orders,
                'total_spending': float(user.total_spending) if user.total_spending else 0,
                'total_messages': user.total_messages,
                'total_reviews': user.total_reviews,
                'total_referrals': user.total_referrals,
                'last_activity': user.last_user_message_time,
                'hours_since_last_activity': (now - user.last_user_message_time).total_seconds() / 3600 if user.last_user_message_time else None
            }
        })

    # Sort by score descending and return top users
    scored_users.sort(key=lambda x: x['score'], reverse=True)
    return scored_users[:limit]


def send_template_to_important_users(template_name: str, language_code: str = "en_US", limit: int = 10):
    """
    Send a template message to the most important/active users.

    Only targets users OUTSIDE the 24-hour WhatsApp free messaging window.

    Args:
        template_name: The WhatsApp template name to send
        language_code: Template language code (default: en_US)
        limit: Maximum number of users to send to (default: 100)

    Returns:
        dict with statistics about the operation
    """
    from api.models.message import Message, CurrentIntentChoices

    logger.info(f"Starting send_template_to_important_users with template: {template_name}")

    # Get top important users
    try:
        scored_users = _calculate_user_importance_scores_internal(limit)
    except Exception as e:
        logger.error(f"Error calculating user importance scores: {e}")
        return {
            "success": False,
            "error": str(e),
            "sent_count": 0,
            "failed_count": 0
        }

    if not scored_users:
        logger.info("No eligible users found outside 24-hour window")
        return {
            "success": True,
            "sent_count": 0,
            "failed_count": 0,
            "message": "No eligible users found outside 24-hour window"
        }

    sent_count = 0
    failed_count = 0
    sent_users = []
    failed_users = []

    for user_data in scored_users:
        user = user_data['user']
        try:
            Message.bot_message_template(
                template_name=template_name,
                user=user,
                language_code=language_code,
                current_intent=CurrentIntentChoices.NO_INTENT
            )
            sent_count += 1
            sent_users.append({
                'user_id': user.id,
                'user_code': user.code,
                'phone': user.phone,
                'score': user_data['score'],
                'metrics': user_data['metrics']
            })
            logger.info(f"Sent template to user {user.code} (score: {user_data['score']})")
        except Exception as e:
            failed_count += 1
            failed_users.append({
                'user_id': user.id,
                'user_code': user.code,
                'error': str(e)
            })
            logger.error(f"Failed to send template to user {user.code}: {e}")

    result = {
        "success": True,
        "template_name": template_name,
        "total_eligible_users": len(scored_users),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "sent_users": sent_users,
        "failed_users": failed_users
    }

    logger.info(f"send_template_to_important_users completed: sent={sent_count}, failed={failed_count}")
    return result


@task()
def send_template_to_important_users_task(template_name: str, language_code: str = "en_US", limit: int = 100):
    """
    Huey task wrapper for send_template_to_important_users.
    Use this for async/background execution.
    """
    return send_template_to_important_users(template_name, language_code, limit)


def get_important_users_preview(limit=100):
    """
    Preview function to see which users would receive the template.
    Useful for testing before actually sending.

    Returns a list of user data with their importance scores.
    """
    scored_users = _calculate_user_importance_scores_internal(limit)

    preview = []
    for user_data in scored_users:
        user = user_data['user']
        preview.append({
            'user_id': user.id,
            'user_code': user.code,
            'phone': user.phone,
            'score': user_data['score'],
            'score_breakdown': user_data['breakdown'],
            'metrics': user_data['metrics']
        })

    return preview
