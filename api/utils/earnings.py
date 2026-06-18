"""Rider and company earnings management."""

from django.db import transaction
from api.models.user_balance import UserBalance


@transaction.atomic
def process_delivery_completion(order):
    """
    Process earnings when delivery is confirmed.

    Logic:
    1. Add delivery fee to rider's balance (or company if rider belongs to company)
    2. Update rider statistics
    3. Update company statistics if applicable

    Args:
        order: Order object that was just delivered

    Returns:
        tuple: (rider_balance, company_balance or None)
    """
    rider = order.rider

    if not rider:
        return None, None

    # Determine who gets the delivery fee
    if rider.company:
        # Add to company balance
        company_balance = UserBalance.add_balance(
            rider.company.user,
            order.delivery_fee,
            order.currency
        )

        # Update company stats
        rider.company.total_orders += 1
        rider.company.completed_today += 1
        rider.company.total_revenue += order.delivery_fee
        rider.company.save()

        rider_balance = None
    else:
        # Add to rider balance (independent rider)
        rider_balance = UserBalance.add_balance(
            rider.user,
            order.delivery_fee,
            order.currency
        )
        company_balance = None

    # Update rider stats (regardless of company affiliation)
    rider.total_deliveries += 1
    rider.completed_today += 1
    rider.total_earnings += order.delivery_fee
    rider.save()

    return rider_balance, company_balance
