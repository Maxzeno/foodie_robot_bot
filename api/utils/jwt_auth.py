import jwt
from datetime import datetime, timedelta
from django.conf import settings
from api.models.user import User
from api.models.refresh_token import RefreshToken
from ninja.errors import HttpError


class JWTAuth:
    """JWT authentication utilities for generating and validating tokens."""

    @staticmethod
    def generate_access_token(user):
        """
        Generate access token (24hr expiry).

        Returns:
            str: JWT access token
        """
        payload = {
            'user_id': user.id,
            'email': user.email,
            'exp': datetime.utcnow() + timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRY_HOURS),
            'iat': datetime.utcnow(),
            'type': 'access'
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm='HS256'
        )

    @staticmethod
    def generate_refresh_token(user):
        """
        Generate refresh token (30-day expiry, stored in DB).

        Returns:
            str: Refresh token string
        """
        refresh_token_obj = RefreshToken.generate_token(user, expires_days=30)
        return refresh_token_obj.token

    @staticmethod
    def decode_access_token(token):
        """
        Decode and validate access token.

        Args:
            token (str): JWT token to decode

        Returns:
            dict: Decoded payload

        Raises:
            ValueError: If token is expired or invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=['HS256']
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HttpError(401, "Token has expired. Try to login again.")
        except jwt.InvalidTokenError:
            raise HttpError(401, "Invalid token. Try to login again.")

    @staticmethod
    def verify_refresh_token(token):
        """
        Verify refresh token from database.

        Args:
            token (str): Refresh token to verify

        Returns:
            User: User object if token is valid

        Raises:
            ValueError: If token is invalid or expired
        """
        try:
            refresh_token_obj = RefreshToken.objects.get(token=token)

            if not refresh_token_obj.is_valid():
                raise ValueError("Refresh token expired or revoked")

            return refresh_token_obj.user
        except RefreshToken.DoesNotExist:
            raise ValueError("Invalid refresh token")
