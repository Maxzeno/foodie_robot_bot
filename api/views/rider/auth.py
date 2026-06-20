"""Authentication endpoints for Rider/Company API."""

from ninja import Router
from django.utils import timezone

from api.schemas.rider_schemas import (
    LoginRequest, LoginResponse, SimpleResponse,
    SendResetCodeRequest, SendResetCodeResponse,
    VerifyResetCodeRequest, ResetPasswordRequest,
    RefreshTokenRequest, RefreshTokenResponse
)
from api.models.user import User
from api.models.otp_code import OTPcode
from api.models.refresh_token import RefreshToken
from api.models.user_balance import UserBalance
from api.models.currency import Currency
from api.utils.email import send_email
from api.utils.jwt_auth import JWTAuth
from api.utils.rate_limit import check_rate_limit, RateLimitExceeded
from ninja.errors import HttpError

router = Router(tags=["Rider Auth"])


@router.post("/login", response={200: LoginResponse, 401: SimpleResponse, 403: SimpleResponse}, auth=None)
def login(request, payload: LoginRequest):
    """
    Authenticate rider and return JWT tokens.
    Rate limit: 5 requests per minute.
    """
    try:
        check_rate_limit(payload.email, endpoint='login', max_requests=5, window_seconds=60)
    except RateLimitExceeded as e:
        print("Rate limit exceeded for login:", str(e))
        raise HttpError(429, str(e))

    # Authenticate user by email
    try:
        user = User.objects.get(email=payload.email)
        if not user.check_password(payload.password):
            raise HttpError(401, "Invalid email or password")
    except User.DoesNotExist:
        raise HttpError(401, "Invalid email or password")

    # Check if user has rider profile
    if not user.is_rider:
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

    # All authenticated users in this endpoint are riders
    # Companies are just riders with company capabilities
    primary_role = 'company' if user.is_company else 'rider'
    
    currency_code = 'NGN'
    currency_symbol = "₦"
    if user.city and user.city.currency:
        currency_code = user.city.currency.code
        currency_symbol = user.city.currency.symbol

    return {
        'user': {
            'id': user.id,
            'name': user.get_full_name() or user.username or '',
            'email': user.email,
            'phone': user.phone,
            'role': primary_role,
            'balance': balance,
            'isOnline': user.is_online,
            'city': user.city.name if user.city else None,
            'cityId': user.city.id if user.city else None,
            'currency': currency_code,
            'currencySymbol': currency_symbol,
        },
        'accessToken': access_token,
        'refreshToken': refresh_token
    }


@router.post("/logout", response={200: SimpleResponse})
def logout(request):
    """Invalidate refresh tokens for the user."""
    # Revoke all active refresh tokens
    RefreshToken.objects.filter(
        user=request.user,
        is_revoked=False
    ).update(is_revoked=True)

    return {'detail': 'Logged out successfully'}


@router.post("/forgot-password/send-code", response={200: SendResetCodeResponse, 404: SimpleResponse}, auth=None)
def send_reset_code(request, payload: SendResetCodeRequest):
    """
    Send 8-digit reset code to user's email.
    Rate limit: 5 requests per minute.
    """
    
    try:
        check_rate_limit(payload.email, endpoint="forgot-password/send-code", max_requests=5, window_seconds=60)
    except RateLimitExceeded as e:
        raise HttpError(429, str(e))

    try:
        user = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        raise HttpError(404, "No account found with this email")

    # Generate reset code
    reset_code = OTPcode.generate_code(user)

    send_email(
        to_email=user.email,
        to_name=user.get_full_name() or user.username or '',
        subject="Your Password Reset Code",
        html_body=f"Your password reset code is: {reset_code.code}\nIt expires at {reset_code.expires_at}.")

    return {
        'detail': 'Reset code sent to email',
        'codeExpiresAt': reset_code.expires_at
    }


@router.post("/forgot-password/verify-code", response={200: SimpleResponse, 400: SimpleResponse}, auth=None)
def verify_reset_code(request, payload: VerifyResetCodeRequest):
    """Verify 8-digit reset code."""
    try:
        check_rate_limit(payload.email, endpoint="forgot-password/verify-code", max_requests=5, window_seconds=60)
    except RateLimitExceeded as e:
        raise HttpError(429, str(e))

    try:
        user = User.objects.get(email=payload.email)
        reset_code = OTPcode.objects.get(
            user=user,
            code=payload.resetCode,
            purpose=OTPcode.PurposeChoices.PASSWORD_RESET
        )

        if not reset_code.is_valid():
            raise HttpError(400, "Reset code is invalid or expired")

        # Mark as verified
        reset_code.is_verified = True
        reset_code.save()

        return {'detail': 'Code verified successfully'}

    except (User.DoesNotExist, OTPcode.DoesNotExist):
        raise HttpError(400, "Reset code is invalid or expired")


@router.post("/forgot-password/reset", response={200: SimpleResponse, 400: SimpleResponse}, auth=None)
def reset_password(request, payload: ResetPasswordRequest):
    """Reset password using verified code."""
    try:
        check_rate_limit(payload.email, endpoint="forgot-password/reset", max_requests=5, window_seconds=60)
    except RateLimitExceeded as e:
        raise HttpError(429, str(e))

    try:
        user = User.objects.get(email=payload.email)
        reset_code = OTPcode.objects.get(
            user=user,
            code=payload.resetCode,
            is_verified=True,
            purpose=OTPcode.PurposeChoices.PASSWORD_RESET
        )

        if not reset_code.is_valid():
            raise HttpError(400, "Reset code is invalid or expired")

        # Reset password
        user.set_password(payload.newPassword)
        user.save()

        # Mark code as used
        reset_code.is_used = True
        reset_code.save()

        return {'detail': 'Password reset successfully'}

    except (User.DoesNotExist, OTPcode.DoesNotExist):
        raise HttpError(400, "Reset code is invalid or expired")


@router.post("/refresh-token", response={200: RefreshTokenResponse, 401: SimpleResponse}, auth=None)
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
