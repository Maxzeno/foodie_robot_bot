from ninja.security import HttpBearer
from api.utils.jwt_auth import JWTAuth
from api.models.user import User


class AuthBearer(HttpBearer):
    """
    JWT Bearer authentication for Django Ninja.

    Usage in endpoints:
        @router.get("/protected", auth=jwt_auth)
        def protected_route(request):
            user = request.user  # Authenticated user
            return {"message": "Hello " + user.email}
    """

    def authenticate(self, request, token):
        """
        Authenticate request using JWT token.

        Args:
            request: Django request object
            token (str): JWT token from Authorization header

        Returns:
            User: Authenticated user if token is valid, None otherwise
        """
        try:
            payload = JWTAuth.decode_access_token(token)
            # Eagerly load rider_profile to avoid N+1 queries
            user = User.objects.select_related('rider_profile').get(id=payload['user_id'])

            # Attach user and payload to request
            request.user = user
            request.auth_payload = payload

            return user
        except (ValueError, User.DoesNotExist):
            return None


# Create global instance for use in endpoints
jwt_auth = AuthBearer()
