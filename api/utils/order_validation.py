"""Order status transition validation."""

# Valid status transitions
VALID_STATUS_TRANSITIONS = {
    'pending': ['accepted'],
    'accepted': ['atRestaurant'],
    'atRestaurant': ['onTheWay'],
    'onTheWay': ['delivered'],
    'delivered': []  # Terminal state
}


def validate_status_transition(current_status, new_status):
    """
    Validate order status transition.

    Args:
        current_status (str): Current order status
        new_status (str): Desired new status

    Returns:
        bool: True if transition is valid

    Raises:
        ValueError: If transition is invalid

    Example:
        validate_status_transition('accepted', 'atRestaurant')  # OK
        validate_status_transition('pending', 'onTheWay')  # Raises ValueError
    """
    allowed_statuses = VALID_STATUS_TRANSITIONS.get(current_status, [])

    if new_status not in allowed_statuses:
        raise ValueError(
            f"Cannot transition from {current_status} to {new_status}. "
            f"Allowed: {', '.join(allowed_statuses) if allowed_statuses else 'none (terminal state)'}"
        )

    return True
