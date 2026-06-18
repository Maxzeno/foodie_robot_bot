"""Pydantic schemas for Rider/Company API endpoints."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ============ AUTH SCHEMAS ============

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    role: str  # Primary role for this session
    balance: float


class LoginResponse(BaseModel):
    user: UserResponse
    accessToken: str
    refreshToken: str


class SendResetCodeRequest(BaseModel):
    email: EmailStr


class SendResetCodeResponse(BaseModel):
    details: str
    codeExpiresAt: datetime


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    resetCode: str  # 8 digits


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    resetCode: str
    newPassword: str


class RefreshTokenRequest(BaseModel):
    refreshToken: str


class RefreshTokenResponse(BaseModel):
    accessToken: str
    refreshToken: str


class SimpleResponse(BaseModel):
    """For endpoints that return only a details message."""
    details: str


# ============ ORDER SCHEMAS ============

class OrderItemResponse(BaseModel):
    id: str
    restaurantName: str
    restaurantPhone: str
    pickupAddress: str
    dropoffAddress: str
    customerName: str
    customerPhone: str
    deliveryFee: float
    status: str
    confirmationCode: Optional[str] = None
    mealName: str
    mealQuantity: int
    mealPrice: float
    paymentCompleted: bool
    createdAt: datetime
    completedAt: Optional[datetime] = None


class PaginationResponse(BaseModel):
    currentPage: int
    totalPages: int
    totalItems: int
    itemsPerPage: int


class OrderHistoryResponse(BaseModel):
    orders: List[OrderItemResponse]
    pagination: PaginationResponse


class NewOrderResponse(BaseModel):
    id: str
    restaurantName: str
    restaurantPhone: str
    pickupAddress: str
    dropoffAddress: str
    customerName: str
    customerPhone: str
    deliveryFee: float
    confirmationCode: str
    mealName: str
    mealQuantity: int
    mealPrice: float
    estimatedDistance: str
    estimatedDuration: str


class AcceptOrderResponse(BaseModel):
    details: str
    orderId: str
    status: str


class UpdateStatusRequest(BaseModel):
    status: str  # accepted, atRestaurant, onTheWay, delivered


class UpdateStatusResponse(BaseModel):
    details: str
    orderId: str
    status: str
    updatedAt: datetime


class ConfirmDeliveryRequest(BaseModel):
    confirmationCode: str  # 4 digits


class ConfirmDeliveryResponse(BaseModel):
    details: str
    orderId: str
    status: str
    deliveryFee: float
    completedAt: datetime


# ============ PAYMENT SCHEMAS ============

class VerifyAccountRequest(BaseModel):
    bankName: str
    accountNumber: str  # 10 digits


class VerifyAccountResponse(BaseModel):
    accountName: str
    accountNumber: str
    bankName: str
    bankCode: str


class BankDetails(BaseModel):
    bankName: str
    accountNumber: str
    accountName: str


class RestaurantPaymentRequest(BaseModel):
    orderId: str
    bankDetails: BankDetails


class RestaurantPaymentResponse(BaseModel):
    details: str
    transactionId: str
    orderId: str
    amount: float
    status: str
    paidAt: datetime


# ============ COMPANY/RIDER SCHEMAS ============

class CompanyBalanceResponse(BaseModel):
    balance: float
    currency: str
    pendingWithdrawals: float
    availableForWithdrawal: float


class WithdrawRequest(BaseModel):
    amount: float
    bankDetails: BankDetails


class WithdrawResponse(BaseModel):
    details: str
    withdrawalId: str
    amount: float
    status: str
    estimatedCompletionTime: str
    createdAt: datetime


class WithdrawalItem(BaseModel):
    id: str
    amount: float
    status: str
    bankDetails: BankDetails
    createdAt: datetime
    completedAt: Optional[datetime] = None


class WithdrawalHistoryResponse(BaseModel):
    withdrawals: List[WithdrawalItem]
    pagination: PaginationResponse


class OnlineStatusRequest(BaseModel):
    isOnline: bool


class OnlineStatusResponse(BaseModel):
    isOnline: bool
    updatedAt: datetime


class RiderStatsResponse(BaseModel):
    totalDeliveries: int
    completedToday: int
    averageRating: float
    totalEarnings: float


class RiderProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    balance: float
    isOnline: bool
    role: str
    currency: str
    currency_symbol: str
    city_id: int
    city: str
