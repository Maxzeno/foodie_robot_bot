from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Q, F
import pytz

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


def get_calorie_stats(user: User, period: str = "day") -> bool:
    """
    Show user's calorie consumption stats for a given period.
    Compares against fitness goal recommendations.

    Args:
        user: The user requesting stats
        period: One of "day", "week", "month", "year"

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate and normalize period
        valid_periods = ["day", "week", "month", "year"]
        if period not in valid_periods:
            period = "day"

        # Calculate period boundaries
        start_local = _get_period_start(user, period)
        start_utc = start_local.astimezone(pytz.UTC)

        # Calculate number of days for averaging
        now_local = user.get_local_time()
        period_days = (now_local.date() - start_local.date()).days + 1

        # Query paid orders with calorie data
        orders = Order.objects.filter(
            user=user,
            paid=True,
            created_at__gte=start_utc,
            meal__calories__isnull=False
        ).select_related('meal')

        # Calculate total calories (meal calories × quantity)
        total_calories = sum(
            float(order.meal.calories) * order.quantity
            for order in orders
        )

        order_count = orders.count()

        # Get fitness goal info
        if user.fitness_goals:
            goal_name = user.fitness_goals.name
            goal_display = user.fitness_goals.get_name_display()
        else:
            goal_name = "maintenance"  # Default
            goal_display = "Not set (using Maintenance)"

        daily_target = _get_calorie_target(goal_name)

        # Period display names
        period_labels = {
            "day": "Today",
            "week": "This Week",
            "month": "This Month",
            "year": "This Year"
        }
        period_label = period_labels.get(period, "Today")

        # Handle no tracked meals
        if order_count == 0:
            message = f"""📊 *Nutrition Stats - {period_label}*

No meals tracked yet for this period.

Start ordering meals and we'll automatically track your nutrition progress! 🍽️

━━━━━━━━━━━━━━━━━━━━
💡 Fitness Goal: {goal_display}
🎯 Daily Target: {daily_target:,.0f} kcal

_Ask for "this week" or "this month" to see more._
"""
            Message.bot_message(message.strip(), user=user)
            return True

        # Calculate status
        status, emoji, difference = _calculate_status(
            total_calories,
            daily_target,
            period_days
        )

        # Calculate percentage
        avg_calories = total_calories / period_days if period_days > 1 else total_calories
        percentage = (avg_calories / daily_target) * 100 if daily_target > 0 else 0

        # Build status headline
        if status == "on track":
            headline = f"✅ *You're on track!* ({goal_display})"
        elif difference < -200:
            headline = f"⚠️ *Below target* ({goal_display})"
        else:
            headline = f"⚠️ *Above target* ({goal_display})"

        message = f"{headline}\n\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n"

        # Period-specific formatting
        if period == "day":
            message += "*TODAY'S CALORIES*\n"
            message += f"{total_calories:,.0f} / {daily_target:,.0f} kcal ({percentage:.0f}%)\n"
            message += f"{_get_progress_bar(total_calories, daily_target)}\n\n"

            # Show remaining or overage
            remaining = daily_target - total_calories
            if remaining > 0:
                message += f"✨ *{remaining:,.0f} kcal remaining*\n\n"
            else:
                message += f"⚠️ *{abs(remaining):,.0f} kcal over target*\n\n"

        else:
            # Multi-day periods
            period_upper = period_label.upper()
            message += f"*{period_upper}'S CALORIES*\n"
            message += f"{total_calories:,.0f} kcal total\n"
            message += f"{avg_calories:,.0f} kcal daily average\n\n"
            message += f"Target: {daily_target:,.0f} kcal/day ({percentage:.0f}%)\n"
            message += f"{_get_progress_bar(avg_calories, daily_target)}\n\n"

        message += "━━━━━━━━━━━━━━━━━━━━\n"
        message += f"🍽️ {order_count} meal{'s' if order_count != 1 else ''} tracked\n\n"

        # Add contextual encouragement
        if difference < -200:
            if period == "day":
                message += "💡 Consider adding a nutritious meal to meet your energy needs!"
            else:
                message += f"💡 You're averaging {abs(difference):.0f} kcal below target. Consider adding more nutritious meals."
        elif difference > 200:
            if period == "day":
                message += "💡 Maybe opt for lighter options if you plan to eat more today."
            else:
                message += f"💡 You're averaging {difference:.0f} kcal over target. Try lighter options to stay on track."
        else:
            motivations = [
                "Great job! Keep it up! 🎉",
                "You're crushing it! 💪",
                "Perfect balance! Keep going! 🌟",
                "Excellent work! Stay consistent! ✨"
            ]
            # Use order count to pick a consistent message per user session
            message += motivations[order_count % len(motivations)]

        # Add discovery tip (softer format)
        period_to_exclude = {
            "day": "daily",
            "week": "weekly",
            "month": "monthly",
            "year": "yearly"
        }

        current_period_ly = period_to_exclude.get(period)
        all_period_options = ["daily", "weekly", "monthly", "yearly"]
        other_periods = [p for p in all_period_options if p != current_period_ly]

        if len(other_periods) > 0:
            period_hints = {
                "daily": "today",
                "weekly": "this week",
                "monthly": "this month",
                "yearly": "this year"
            }
            available = [period_hints.get(p, p) for p in other_periods]

            if len(available) == 2:
                hint = f"'{available[0]}' or '{available[1]}'"
            elif len(available) == 3:
                hint = f"'{available[0]}', '{available[1]}', or '{available[2]}'"
            else:
                hint = f"'{available[0]}'"

            message += f"\n\n_Ask for {hint} to see more._"

        Message.bot_message(message.strip(), user=user)
        return True

    except Exception as e:
        print(f"Error getting calorie stats: {e}")
        Message.bot_message(
            "Sorry, I couldn't retrieve your nutrition stats right now. Please try again.",
            user=user
        )
        return False
