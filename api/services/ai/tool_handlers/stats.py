from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Q, F, Count
import pytz
import calendar

from api.models.order import Order
from api.models.user import User
from api.models.message import Message


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


def _get_user_display_name(user: User) -> str:
    """Get a display name for leaderboard (anonymized for privacy)."""
    if user.username:
        return user.username
    return f"Foodie #{user.code[-4:]}"


def _format_leaderboard_section(leaderboard: list, user_rank: int, user_order_count: int, user: User) -> str:
    """Format the leaderboard section of the message with engaging visuals."""
    local_now = user.get_local_time()
    month_name = local_now.strftime("%B")

    lines = []
    lines.append(f"*{month_name} Top Foodies*")
    lines.append("")

    if not leaderboard:
        lines.append("No one on the board yet!")
        lines.append("Be the first to claim the crown!")
        return "\n".join(lines)

    # Rank decorations
    rank_icons = ["1.", "2.", "3."]

    for idx, leader in enumerate(leaderboard):
        icon = rank_icons[idx] if idx < 3 else f"{idx + 1}."
        name = _get_user_display_name(leader)
        orders = leader.order_count
        order_text = "order" if orders == 1 else "orders"

        # Highlight current user
        if leader.id == user.id:
            lines.append(f"{icon} *{name}* ({orders} {order_text}) <- You")
        else:
            lines.append(f"{icon} {name} ({orders} {order_text})")

    # Show user's position if not in top 3
    if user_rank and user_rank > 3:
        gap = user_rank - 3
        lines.append("")
        lines.append(f"---")
        lines.append(f"{user_rank}. You ({user_order_count} orders)")
        if gap <= 5:
            orders_needed = leaderboard[-1].order_count - user_order_count + 1 if leaderboard else 1
            if orders_needed > 0:
                lines.append(f"   {orders_needed} more to reach top 3!")
    elif user_rank is None or user_order_count == 0:
        lines.append("")
        lines.append("You're not on the board yet!")

    return "\n".join(lines)


def _get_calorie_target(fitness_goal_name: str) -> int:
    """Get recommended daily calorie target based on fitness goal."""
    targets = {
        "weight_loss": 1800,
        "maintenance": 2200,
        "muscle_gain": 2800,
    }
    return targets.get(fitness_goal_name, 2200)


def _calculate_status(actual: float, target: float, period_days: int = 1):
    """Determine if user is on track with their calorie goals."""
    # For multi-day periods, use average per day
    avg_per_day = actual / period_days if period_days > 0 else actual
    difference = avg_per_day - target

    # Allow 200 calorie buffer for "on track"
    if difference < -200:
        return "below target", "⚠️", difference
    elif difference > 200:
        return "above target", "⚠️", difference
    else:
        return "on track", "✅", difference


def _get_progress_bar(current: float, target: float, width: int = 10) -> str:
    """Generate a visual progress bar using Unicode characters."""
    if target <= 0:
        return "░" * width

    percentage = min(current / target, 1.5)  # Allow up to 150% to show overage
    filled = int(percentage * width)

    # Cap filled blocks at width
    filled = min(filled, width)
    empty = width - filled

    return "▓" * filled + "░" * empty


def _get_user_display_name_for_image(u: User) -> str:
    """Get display name for image leaderboard."""
    if u.username:
        return u.username
    return f"Foodie #{u.code[-4:]}"


def get_progress_stats(user: User) -> bool:
    """
    Show user's daily progress stats including calories, streak, and leaderboard.
    Generates a shareable image and sends it via WhatsApp.

    Args:
        user: The user requesting stats

    Returns:
        bool: True if successful, False otherwise
    """
    from api.utils.progress_image_generator import generate_progress_image, upload_progress_image

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
            brand_name="Foodie"
        )

        # Upload to Cloudinary
        image_url = upload_progress_image(image_bytes, user.code)

        # Build text caption for the image
        caption_lines = []
        caption_lines.append(f"Day {day_number}")
        if streak > 1:
            caption_lines.append(f"{streak}-day streak!")
        caption_lines.append("")
        caption_lines.append(f"Calories: {total_calories:,} / {daily_target:,}")
        if user_rank:
            caption_lines.append(f"Rank: #{user_rank} this month")
        caption_lines.append("")
        caption_lines.append("Share your progress!")

        caption = "\n".join(caption_lines)

        # Send image if upload succeeded, otherwise send text
        if image_url:
            Message.bot_message_image(
                content=caption,
                user=user,
                current_intent="progress_stats",
                preview_media=image_url
            )
        else:
            # Fallback to text-only message
            _send_text_progress_stats(
                user, day_number, streak, total_calories, daily_target,
                order_count, leaderboard, user_rank, user_monthly_orders
            )

        return True

    except Exception as e:
        print(f"Error getting progress stats: {e}")
        Message.bot_message(
            "Sorry, couldn't load your stats. Try again!",
            user=user
        )
        return False


def _send_text_progress_stats(
    user: User,
    day_number: int,
    streak: int,
    total_calories: int,
    daily_target: int,
    order_count: int,
    leaderboard: list,
    user_rank: int,
    user_monthly_orders: int
):
    """Send text-only progress stats as fallback."""
    lines = []

    # Header
    lines.append("*Your Progress*")
    lines.append("")

    # Day & Streak section
    if streak >= 7:
        lines.append(f"*Day {day_number}* | {streak}-day streak!")
        lines.append("You're unstoppable!")
    elif streak >= 3:
        lines.append(f"*Day {day_number}* | {streak}-day streak")
        lines.append("Keep the momentum going!")
    elif streak > 1:
        lines.append(f"*Day {day_number}* | {streak}-day streak")
    else:
        lines.append(f"*Day {day_number}*")
        if day_number == 1:
            lines.append("Welcome! Your journey starts now.")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Today's Calories Section
    lines.append("*Today's Calories*")
    lines.append("")

    if order_count == 0:
        lines.append("No meals yet today")
        lines.append(f"Target: {daily_target:,.0f} kcal")
        lines.append("")
        lines.append("Order your first meal to start tracking!")
    else:
        percentage = (total_calories / daily_target) * 100 if daily_target > 0 else 0
        remaining = daily_target - total_calories

        lines.append(f"{total_calories:,.0f} / {daily_target:,.0f} kcal")
        lines.append(f"{_get_progress_bar(total_calories, daily_target)} {percentage:.0f}%")
        lines.append("")

        if remaining > 0:
            lines.append(f"{remaining:,.0f} kcal left for today")
        else:
            lines.append(f"{abs(remaining):,.0f} kcal over - go light!")

        lines.append(f"{order_count} meal{'s' if order_count != 1 else ''} tracked")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Leaderboard Section
    leaderboard_text = _format_leaderboard_section(leaderboard, user_rank, user_monthly_orders, user)
    lines.append(leaderboard_text)

    # Call to action
    lines.append("")
    if user_rank == 1:
        lines.append("You're leading the pack! Stay on top!")
    elif user_rank and user_rank <= 3:
        lines.append("So close to #1 - one more order could do it!")
    elif user_monthly_orders > 0:
        lines.append("Order more to climb the leaderboard!")
    else:
        lines.append("Make your first order to get on the board!")

    Message.bot_message("\n".join(lines), user=user)


# Keep old function name as alias for backwards compatibility
def get_calorie_stats(user: User, period: str = "day") -> bool:
    """Backwards compatible alias for get_progress_stats."""
    return get_progress_stats(user)
