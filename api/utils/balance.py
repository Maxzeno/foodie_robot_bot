"""
Utility functions for managing user balances.
"""
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum


def sync_referral_earnings_to_balance(user):
    """
    Sync all referral earnings for a user to their UserBalance.

    This function aggregates all ReferralEarning records by currency
    and updates the corresponding UserBalance records.

    Args:
        user: User instance

    Returns:
        dict: Summary of synced balances {currency_code: amount}
    """
    from api.models.referral_earning import ReferralEarning
    from api.models.user_balance import UserBalance, BalanceType

    # Aggregate referral earnings by currency
    earnings_by_currency = (
        ReferralEarning.objects
        .filter(user=user)
        .values('currency')
        .annotate(total=Sum('amount'))
    )

    synced_balances = {}

    with transaction.atomic():
        for earning in earnings_by_currency:
            currency_id = earning['currency']
            total_amount = earning['total'] or Decimal('0.00')

            # Get or create the currency object
            from api.models.currency import Currency
            currency = Currency.objects.get(id=currency_id)

            # Update or create the UserBalance
            balance, created = UserBalance.objects.update_or_create(
                user=user,
                balance_type=BalanceType.REFERRAL,
                currency=currency,
                defaults={'amount': total_amount}
            )

            synced_balances[currency.code] = total_amount

    return synced_balances


def sync_all_users_referral_earnings():
    """
    Sync referral earnings to UserBalance for all users.

    This is useful for one-time migration or periodic sync operations.

    Returns:
        dict: Summary of all synced users
    """
    from api.models.user import User

    results = {
        'total_users': 0,
        'users_with_earnings': 0,
        'total_balances_created': 0,
    }

    users = User.objects.all()
    results['total_users'] = users.count()

    for user in users:
        synced = sync_referral_earnings_to_balance(user)
        if synced:
            results['users_with_earnings'] += 1
            results['total_balances_created'] += len(synced)

    return results


def add_referral_earning(referred_by_user, referred_user, city):
    """
    Add a referral earning when a new user is referred.

    This function:
    1. Creates a ReferralEarning record
    2. Updates the UserBalance for the referrer

    Args:
        referred_by_user: User who referred (the one earning)
        referred_user: User who was referred
        city: City instance (contains referral_bonus and currency)

    Returns:
        tuple: (ReferralEarning instance, UserBalance instance)
    """
    from api.models.referral_earning import ReferralEarning
    from api.models.user_balance import UserBalance, BalanceType

    with transaction.atomic():
        # Create the referral earning record
        referral_earning = ReferralEarning.objects.create(
            user=referred_by_user,
            referred_user=referred_user,
            amount=city.referral_bonus,
            currency=city.currency,
            city=city
        )

        # Update the user's balance
        balance = UserBalance.add_balance(
            user=referred_by_user,
            balance_type=BalanceType.REFERRAL,
            amount=city.referral_bonus,
            currency=city.currency
        )

    return referral_earning, balance


def get_user_balance_summary(user):
    """
    Get a comprehensive summary of all user balances.

    Args:
        user: User instance

    Returns:
        dict: {
            'referral': {currency_code: amount},
            'wallet': {currency_code: amount},
            'bonus': {currency_code: amount},
        }
    """
    from api.models.user_balance import UserBalance, BalanceType

    summary = {}

    for balance_type in BalanceType:
        balances = UserBalance.get_total_balance_by_type(user, balance_type.value)
        if balances:
            summary[balance_type.value] = balances

    return summary
