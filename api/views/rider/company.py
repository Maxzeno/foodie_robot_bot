"""Company profile, balance, and withdrawal endpoints."""

from ninja import Router
from django.utils import timezone
from django.db import models
from decimal import Decimal

from api.schemas.rider_schemas import (
    CompanyBalanceResponse, SimpleResponse,
    WithdrawRequest, WithdrawResponse,
    WithdrawalHistoryResponse
)
from api.models.company import Company
from api.models.withdrawal import Withdrawal, WithdrawalStatus
from api.models.user_balance import UserBalance
from api.models.currency import Currency
from api.utils.auth_bearer import jwt_auth
from api.utils.permissions import require_company
from api.utils.pagination import paginate_queryset
from ninja.errors import HttpError

router = Router(tags=["Company Balance & Withdrawal"])


@router.get("/balance", auth=jwt_auth, response={200: CompanyBalanceResponse})
@require_company
def get_company_balance(request):
    """Get current balance for company account."""
    try:
        company = request.user.company_profile
    except Company.DoesNotExist:
        raise HttpError(400, "Company profile not found")

    # Get default currency (NGN)
    currency = Currency.objects.filter(code='NGN').first()
    if not currency:
        currency = Currency.objects.first()

    if not currency:
        raise HttpError(500, "No currency configured")

    # Get balance
    balance = UserBalance.get_balance(request.user, currency)

    # Calculate pending withdrawals
    pending_withdrawals = Withdrawal.objects.filter(
        user=request.user,
        status=WithdrawalStatus.PENDING,
        currency=currency
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    available = balance.amount - pending_withdrawals

    return {
        'balance': float(balance.amount),
        'currency': currency.code,
        'pendingWithdrawals': float(pending_withdrawals),
        'availableForWithdrawal': float(available)
    }


@router.post("/withdraw", auth=jwt_auth, response={200: WithdrawResponse, 400: SimpleResponse})
@require_company
def withdraw_funds(request, payload: WithdrawRequest):
    """Initiate withdrawal of company earnings."""
    try:
        company = request.user.company_profile
    except Company.DoesNotExist:
        raise HttpError(400, "Company profile not found")

    # Get default currency
    currency = Currency.objects.filter(code='NGN').first()
    if not currency:
        currency = Currency.objects.first()

    if not currency:
        raise HttpError(500, "No currency configured")

    # Get balance
    balance = UserBalance.get_balance(request.user, currency)

    # Calculate pending withdrawals
    pending_withdrawals = Withdrawal.objects.filter(
        user=request.user,
        status=WithdrawalStatus.PENDING,
        currency=currency
    ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

    available = balance.amount - pending_withdrawals

    # Check if sufficient balance
    if available < Decimal(str(payload.amount)):
        raise HttpError(400, "Insufficient balance for withdrawal")

    # Create withdrawal request
    withdrawal = Withdrawal.objects.create(
        user=request.user,
        amount=Decimal(str(payload.amount)),
        currency=currency,
        account_name=payload.bankDetails.accountName,
        account_number=payload.bankDetails.accountNumber,
        bank_name=payload.bankDetails.bankName,
        status=WithdrawalStatus.PENDING
    )

    return {
        'details': 'Withdrawal initiated successfully',
        'withdrawalId': f"WD-{withdrawal.id}",
        'amount': float(withdrawal.amount),
        'status': withdrawal.status,
        'estimatedCompletionTime': '1-2 business days',
        'createdAt': withdrawal.created_at
    }


@router.get("/withdrawals", auth=jwt_auth, response={200: WithdrawalHistoryResponse})
@require_company
def get_withdrawal_history(request, page: int = 1, limit: int = 20):
    """Get history of company withdrawals."""
    # Get withdrawals
    queryset = Withdrawal.objects.filter(
        user=request.user
    ).select_related('currency').order_by('-created_at')

    # Paginate
    withdrawals, pagination = paginate_queryset(queryset, page, limit)

    # Serialize
    withdrawal_items = [
        {
            'id': f"WD-{w.id}",
            'amount': float(w.amount),
            'status': w.status,
            'bankDetails': {
                'bankName': w.bank_name,
                'accountNumber': w.account_number,
                'accountName': w.account_name
            },
            'createdAt': w.created_at,
            'completedAt': w.processed_at
        }
        for w in withdrawals
    ]

    return {
        'withdrawals': withdrawal_items,
        'pagination': pagination
    }


@router.get("/profile", auth=jwt_auth, response={200: dict})
@require_company
def get_company_profile(request):
    """Get company profile information and statistics."""
    try:
        company = request.user.company_profile
    except Company.DoesNotExist:
        raise HttpError(400, "Company profile not found")

    user = request.user

    # Get balance
    currency = Currency.objects.filter(code='NGN').first()
    if not currency:
        currency = Currency.objects.first()

    balance = 0
    if currency:
        user_balance = UserBalance.get_balance(user, currency)
        balance = float(user_balance.amount)

    return {
        'id': company.id,
        'name': company.name,
        'email': user.email,
        'phone': user.phone or '',
        'balance': balance,
        # 'stats': {
        #     'totalOrders': company.total_orders,
        #     'activeRiders': company.active_riders,
        #     'completedToday': company.completed_today,
        #     'totalRevenue': float(company.total_revenue)
        # }
    }
