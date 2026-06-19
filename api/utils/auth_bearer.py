from ninja.security import HttpBearer
from api.utils.jwt_auth import JWTAuth
from api.models.user import User
from django.http import HttpResponseForbidden

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
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
        
    def on_auth_fail(self, response):
        return HttpResponseForbidden("Failed to authenticate! or maybe you requested for a password change.")

