from math import ceil


def paginate_queryset(queryset, page=1, limit=20):
    """
    Paginate a Django queryset.

    Args:
        queryset: Django QuerySet to paginate
        page (int): Page number (1-indexed)
        limit (int): Items per page (max 100)

    Returns:
        tuple: (paginated_qs, pagination_data)
            - paginated_qs: Sliced queryset for the current page
            - pagination_data: Dict with currentPage, totalPages, totalItems, itemsPerPage

    Example:
        orders = Order.objects.filter(user=user)
        paginated_orders, pagination = paginate_queryset(orders, page=1, limit=20)
    """
    page = max(1, page)  # Ensure page >= 1
    limit = min(100, max(1, limit))  # Limit between 1-100

    total_items = queryset.count()
    total_pages = ceil(total_items / limit) if total_items > 0 else 1

    offset = (page - 1) * limit
    paginated_qs = queryset[offset:offset + limit]

    pagination_data = {
        'currentPage': page,
        'totalPages': total_pages,
        'totalItems': total_items,
        'itemsPerPage': limit
    }

    return paginated_qs, pagination_data
