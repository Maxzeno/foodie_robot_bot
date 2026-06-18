"""Authentication endpoints for Rider/Company API."""

from ninja import Router
from django.contrib.auth import authenticate
from django.utils import timezone

from api.schemas.rider_schemas import (
    LoginRequest, LoginResponse, SimpleResponse,
    SendResetCodeRequest, SendResetCodeResponse,
    VerifyResetCodeRequest, ResetPasswordRequest,
    RefreshTokenRequest, RefreshTokenResponse
)
from api.models.user import User
from api.models.password_reset import PasswordReset
from api.models.refresh_token import RefreshToken
from api.models.user_balance import UserBalance
from api.models.currency import Currency
from api.utils.jwt_auth import JWTAuth
from api.utils.auth_bearer import jwt_auth
from api.utils.rate_limit import check_rate_limit, RateLimitExceeded
from ninja.errors import HttpError

router = Router(tags=["Rider Auth"])


@router.post("/login", response={200: LoginResponse, 401: SimpleResponse, 403: SimpleResponse})
def login(request, payload: LoginRequest):
    """
    Authenticate rider/company and return JWT tokens.
    Rate limit: 5 requests per minute.
    """
    try:
        check_rate_limit(payload.email, max_requests=5, window_seconds=60)
    except RateLimitExceeded as e:
        raise HttpError(429, str(e))

    # Authenticate user
    user = authenticate(username=payload.email, password=payload.password)

    if not user:
        raise HttpError(401, "Invalid email or password")

    # Check if user has rider or company role
    if not ('rider' in user.roles or 'company' in user.roles):
        raise HttpError(403, "You don't have permission to access this resource")

    # Generate tokens
    access_token = JWTAuth.generate_access_token(user)
    refresh_token = JWTAuth.generate_refresh_token(user)

    # Get user balance (default to NGN currency)
    currency = Currency.objects.filter(code='NGN').first()
    if not currency:
        currency = Currency.objects.first()  # Fallback to any currency

    balance = 0
    if currency:
        user_balance = UserBalance.get_balance(user, currency)
        balance = float(user_balance.amount)

    # Determine primary role
    primary_role = 'rider' if 'rider' in user.roles else 'company'

    return {
        'user': {
            'id': user.id,
            'name': user.get_full_name() or user.username or '',
            'email': user.email,
            'phone': user.phone,
            'role': primary_role,
            'balance': balance
        },
        'accessToken': access_token,
        'refreshToken': refresh_token
    }


@router.post("/logout", auth=jwt_auth, response={200: SimpleResponse})
def logout(request):
    """Invalidate refresh tokens for the user."""
    # Revoke all active refresh tokens
    RefreshToken.objects.filter(
        user=request.user,
        is_revoked=False
    ).update(is_revoked=True)

    return {'details': 'Logged out successfully'}


@router.post("/forgot-password/send-code", response={200: SendResetCodeResponse, 404: SimpleResponse})
def send_reset_code(request, payload: SendResetCodeRequest):
    """
    Send 8-digit reset code to user's email.
    Rate limit: 5 requests per minute.
    """
    try:
        check_rate_limit(payload.email, max_requests=5, window_seconds=60)
    except RateLimitExceeded as e:
        raise HttpError(429, str(e))

    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        raise HttpError(404, "No account found with this email")

    # Generate reset code
    reset_code = PasswordReset.generate_code(user)

    # TODO: Send email with reset code using Celery task
    # For now, just log it (in production, use an email service)
    print(f"[PASSWORD RESET] Code for {user.email}: {reset_code.code}")

    return {
        'details': 'Reset code sent to email',
        'codeExpiresAt': reset_code.expires_at
    }


@router.post("/forgot-password/verify-code", response={200: SimpleResponse, 400: SimpleResponse})
def verify_reset_code(request, payload: VerifyResetCodeRequest):
    """Verify 8-digit reset code."""
    try:
        user = User.objects.get(email=payload.email)
        reset_code = PasswordReset.objects.get(
            user=user,
            code=payload.resetCode
        )

        if not reset_code.is_valid():
            raise HttpError(400, "Reset code is invalid or expired")

        # Mark as verified
        reset_code.is_verified = True
        reset_code.save()

        return {'details': 'Code verified successfully'}

    except (User.DoesNotExist, PasswordReset.DoesNotExist):
        raise HttpError(400, "Reset code is invalid or expired")


@router.post("/forgot-password/reset", response={200: SimpleResponse, 400: SimpleResponse})
def reset_password(request, payload: ResetPasswordRequest):
    """Reset password using verified code."""
    try:
        user = User.objects.get(email=payload.email)
        reset_code = PasswordReset.objects.get(
            user=user,
            code=payload.resetCode,
            is_verified=True
        )

        if not reset_code.is_valid():
            raise HttpError(400, "Reset code is invalid or expired")

        # Reset password
        user.set_password(payload.newPassword)
        user.save()

        # Mark code as used
        reset_code.is_used = True
        reset_code.save()

        return {'details': 'Password reset successfully'}

    except (User.DoesNotExist, PasswordReset.DoesNotExist):
        raise HttpError(400, "Reset code is invalid or expired")


@router.post("/refresh-token", response={200: RefreshTokenResponse, 401: SimpleResponse})
def refresh_token(request, payload: RefreshTokenRequest):
    """Get new access token using refresh token."""
    try:
        user = JWTAuth.verify_refresh_token(payload.refreshToken)

        # Generate new tokens
        new_access_token = JWTAuth.generate_access_token(user)
        new_refresh_token = JWTAuth.generate_refresh_token(user)

        # Revoke old refresh token
        RefreshToken.objects.filter(
            token=payload.refreshToken
        ).update(is_revoked=True)

        return {
            'accessToken': new_access_token,
            'refreshToken': new_refresh_token
        }

    except ValueError as e:
        raise HttpError(401, str(e))
