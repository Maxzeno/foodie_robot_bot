from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Q, F, Count
import pytz
import calendar

from api.models.order import Order
from api.models.user import User
from api.models.message import Message
from api.utils.progress_image_generator import generate_progress_image, upload_progress_image


def _get_period_start(user: User, period: str):
    """Calculate start datetime for the given period in user's timezone."""
    local_now = user.get_local_time()

    if period == "week":
        # Start of the week (Monday)
        days_since_monday = local_now.weekday()
        start = local_now - timedelta(days=days_since_monday)
        return start.replace(hour=0, minute=0, second=0, microsecond=0)

    elif period == "month":
        # First day of current month
        return local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    elif period == "year":
        # First day of current year
        return local_now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    else:  # Default to "day"
        # Start of today
        return local_now.replace(hour=0, minute=0, second=0, microsecond=0)


def _get_month_boundaries_utc(user: User):
    """Get the start and end of current month in UTC."""
    local_now = user.get_local_time()
    month_start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get last day of month
    last_day = calendar.monthrange(local_now.year, local_now.month)[1]
    month_end = local_now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

    return month_start.astimezone(pytz.UTC), month_end.astimezone(pytz.UTC)


def _get_monthly_leaderboard(user: User, limit: int = 3):
    """
    Get the monthly leaderboard based on paid order count.
    Returns top users and current user's rank.
    """
    month_start_utc, month_end_utc = _get_month_boundaries_utc(user)

    # Get users with their order counts for this month, filtered by user's city
    leaderboard_query = User.objects.filter(
        orders__paid=True,
        orders__created_at__gte=month_start_utc,
        orders__created_at__lte=month_end_utc,
    )

    # Filter by city if user has one
    if user.city:
        leaderboard_query = leaderboard_query.filter(city=user.city)

    leaderboard = leaderboard_query.annotate(
        order_count=Count('orders', filter=Q(
            orders__paid=True,
            orders__created_at__gte=month_start_utc,
            orders__created_at__lte=month_end_utc,
        ))
    ).filter(order_count__gt=0).order_by('-order_count')[:limit]

    # Get current user's rank
    user_order_count = Order.objects.filter(
        user=user,
        paid=True,
        created_at__gte=month_start_utc,
        created_at__lte=month_end_utc,
    ).count()

    # Count users with more orders than current user
    users_ahead = User.objects.filter(
        orders__paid=True,
        orders__created_at__gte=month_start_utc,
        orders__created_at__lte=month_end_utc,
    )
    if user.city:
        users_ahead = users_ahead.filter(city=user.city)

    users_ahead = users_ahead.annotate(
        order_count=Count('orders', filter=Q(
            orders__paid=True,
            orders__created_at__gte=month_start_utc,
            orders__created_at__lte=month_end_utc,
        ))
    ).filter(order_count__gt=user_order_count).count()

    user_rank = users_ahead + 1 if user_order_count > 0 else None

    return list(leaderboard), user_rank, user_order_count

def _get_calorie_target(fitness_goal_name: str) -> int:
    """Get recommended daily calorie target based on fitness goal."""
    targets = {
        "weight_loss": 1800,
        "maintenance": 2200,
        "muscle_gain": 2800,
    }
    return targets.get(fitness_goal_name, 2200)


def _get_user_display_name_for_image(u: User) -> str:
    if u.username:
        return u.username
    return f"Foodie #{u.code[-4:]}"


def get_progress_stats(user: User) -> bool:
    try:
        # Always use today's data to encourage daily check-ins
        start_local = _get_period_start(user, "day")
        start_utc = start_local.astimezone(pytz.UTC)
        local_now = user.get_local_time()
        month_name = local_now.strftime("%B")

        # Query today's paid orders with calorie data
        orders = Order.objects.filter(
            user=user,
            paid=True,
            created_at__gte=start_utc,
            meal__calories__isnull=False
        ).select_related('meal')

        # Calculate total calories
        total_calories = int(sum(
            float(order.meal.calories) * order.quantity
            for order in orders
        ))
        order_count = orders.count()

        # Get user's streak and day info
        day_number = user.get_recommendation_day_number()
        streak = user.get_recommendation_streak()

        # Get leaderboard data
        leaderboard, user_rank, user_monthly_orders = _get_monthly_leaderboard(user)

        # Get fitness goal info
        goal_name = user.fitness_goals.name if user.fitness_goals else "maintenance"
        daily_target = _get_calorie_target(goal_name)

        # Prepare leaderboard data for image
        leaderboard_for_image = []
        for leader in leaderboard[:3]:
            leaderboard_for_image.append({
                'name': _get_user_display_name_for_image(leader),
                'orders': leader.order_count,
                'is_user': leader.id == user.id
            })

        # Generate the shareable image
        image_bytes = generate_progress_image(
            day_number=day_number,
            streak=streak,
            calories_consumed=total_calories,
            calories_target=daily_target,
            leaderboard=leaderboard_for_image,
            user_rank=user_rank,
            user_orders=user_monthly_orders,
            month_name=month_name,
            brand_name="Foodie Robot"
        )

        # Upload to Cloudinary
        image_url = upload_progress_image(image_bytes, user.code)

        caption = "Your Progress Stats \n\nShare your achievements with friends!"

        # Send image if upload succeeded, otherwise send text
        if image_url:
            Message.bot_message_image(
                content=caption,
                user=user,
                preview_media=image_url
            )
        else:
            Message.bot_message(
                content="Sorry, couldn't load your stats. Try again!!!",
                user=user,
            )

        return True

    except Exception as e:
        print(f"Error getting progress stats: {e}")
        Message.bot_message(
            "Sorry, couldn't load your stats. Try again!",
            user=user
        )
        return False
