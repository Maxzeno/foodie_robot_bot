from functools import wraps
from ninja.errors import HttpError


def require_rider(func):
    """
    Decorator to check user is a rider (has rider profile).

    Usage:
        @router.get("/orders/new", auth=jwt_auth)
        @require_rider
        def get_new_order(request):
            return {"message": "New order"}
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.user

        if not user.is_rider:
            raise HttpError(403, "You don't have permission to access this resource")

        return func(request, *args, **kwargs)
    return wrapper


def require_company(func):
    """
    Decorator to check user is a company (rider with company capabilities).

    Usage:
        @router.get("/company/balance", auth=jwt_auth)
        @require_company
        def get_company_balance(request):
            return {"balance": 1000}
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.user

        if not user.is_company:
            raise HttpError(403, "You don't have permission to access this resource")

        return func(request, *args, **kwargs)
    return wrapper
