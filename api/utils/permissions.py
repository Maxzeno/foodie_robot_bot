from functools import wraps
from ninja.errors import HttpError


def require_rider(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.user

        if not user.is_rider:
            raise HttpError(403, "You don't have permission to access this resource")

        return func(request, *args, **kwargs)
    return wrapper


def require_company(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.user

        if not user.is_company:
            raise HttpError(403, "You don't have permission to access this resource")

        return func(request, *args, **kwargs)
    return wrapper
