from functools import wraps
from ninja.errors import HttpError


def require_role(*required_roles):
    """
    Decorator to check user has required role(s).

    Usage:
        @router.get("/rider-only", auth=jwt_auth)
        @require_role('rider')
        def rider_endpoint(request):
            return {"message": "Hello rider"}

        @router.get("/multi-role", auth=jwt_auth)
        @require_role('rider', 'company')
        def multi_role_endpoint(request):
            return {"message": "Hello rider or company"}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user

            if not any(role in user.roles for role in required_roles):
                raise HttpError(403, "You don't have permission to access this resource")

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_rider(func):
    """
    Shortcut decorator for rider-only endpoints.

    Usage:
        @router.get("/orders/new", auth=jwt_auth)
        @require_rider
        def get_new_order(request):
            return {"message": "New order"}
    """
    return require_role('rider')(func)


def require_company(func):
    """
    Shortcut decorator for company-only endpoints.

    Usage:
        @router.get("/company/balance", auth=jwt_auth)
        @require_company
        def get_company_balance(request):
            return {"balance": 1000}
    """
    return require_role('company')(func)
