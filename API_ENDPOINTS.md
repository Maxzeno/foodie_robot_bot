# FoodieRobot Rider App - API Endpoints Documentation

This document outlines all the API endpoints required for the FoodieRobot Rider mobile application.

## Base URL

```ini
https://api.foodierobot.com/api/v1
```

---

## Response Format

### Success Responses with Data (200, 201)
Returns only the data without "success" or "message" fields:
```json
{
  "user": { ... },
  "accessToken": "...",
  "refreshToken": "..."
}
```

### Success Responses without Data (200, 201)
Returns a simple details message:
```json
{
  "details": "Operation completed successfully"
}
```

### Error Responses (4xx, 5xx)
Returns a simple details message:
```json
{
  "details": "Error message describing what went wrong"
}
```

---

## Authentication Endpoints

### 1. Login
**POST** `/auth/login`

Authenticate rider or company user and return access token.

**Request Body:**
```json
{
  "email": "rider@test.com",
  "password": "123456"
}
```

**Response (200 OK):**
```json
{
  "user": {
    "id": "user_123",
    "name": "John Rider",
    "email": "rider@test.com",
    "phone": "+1234567890",
    "role": "rider",
    "balance": 125.50
  },
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "refresh_token_here"
}
```

**Response (401 Unauthorized):**
```json
{
  "details": "Invalid email or password"
}
```

---

### 2. Logout
**POST** `/auth/logout`

Invalidate user's access token and refresh token.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "details": "Logged out successfully"
}
```

---

### 3. Send Password Reset Code
**POST** `/auth/forgot-password/send-code`

Send an 8-digit reset code to user's email.

**Request Body:**
```json
{
  "email": "rider@test.com"
}
```

**Response (200 OK):**
```json
{
  "details": "Reset code sent to email",
  "codeExpiresAt": "2026-01-04T12:30:00Z"
}
```

**Response (404 Not Found):**
```json
{
  "details": "No account found with this email"
}
```

---

### 4. Verify Reset Code
**POST** `/auth/forgot-password/verify-code`

Verify the 8-digit reset code before allowing password reset.

**Request Body:**
```json
{
  "email": "rider@test.com",
  "resetCode": "12345678"
}
```

**Response (200 OK):**
```json
{
  "details": "Code verified successfully"
}
```

**Response (400 Bad Request):**
```json
{
  "details": "Reset code is invalid or expired"
}
```

---

### 5. Reset Password
**POST** `/auth/forgot-password/reset`

Reset user password using the verified code.

**Request Body:**
```json
{
  "email": "rider@test.com",
  "resetCode": "12345678",
  "newPassword": "newSecurePassword123"
}
```

**Response (200 OK):**
```json
{
  "details": "Password reset successfully"
}
```

**Response (400 Bad Request):**
```json
{
  "details": "Reset code is invalid or expired"
}
```

---

### 6. Refresh Token
**POST** `/auth/refresh-token`

Get a new access token using refresh token.

**Request Body:**
```json
{
  "refreshToken": "refresh_token_here"
}
```

**Response (200 OK):**
```json
{
  "accessToken": "new_access_token_here",
  "refreshToken": "new_refresh_token_here"
}
```

**Response (401 Unauthorized):**
```json
{
  "details": "Invalid or expired refresh token"
}
```

---

## Order Management Endpoints

### 7. Get Order History
**GET** `/orders/history`

Retrieve rider/company order history with pagination.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)
- `status` (optional): Filter by status (pending, accepted, delivered, etc.)

**Response (200 OK):**
```json
{
  "orders": [
    {
      "id": "ORD-1001",
      "restaurantName": "Pizza House",
      "restaurantPhone": "+234 802 345 6789",
      "pickupAddress": "789 Elm St, Downtown",
      "dropoffAddress": "321 Pine Ave, Midtown",
      "customerName": "John Doe",
      "customerPhone": "+234 805 123 4567",
      "deliveryFee": 15.00,
      "status": "delivered",
      "confirmationCode": "1234",
      "mealName": "Pepperoni Pizza",
      "mealQuantity": 1,
      "mealPrice": 25.00,
      "paymentCompleted": true,
      "createdAt": "2026-01-03T10:30:00Z",
      "completedAt": "2026-01-03T11:15:00Z"
    }
  ],
  "pagination": {
    "currentPage": 1,
    "totalPages": 5,
    "totalItems": 100,
    "itemsPerPage": 20
  }
}
```

---

### 8. Get Order Details
**GET** `/orders/{orderId}`

Get detailed information about a specific order.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "id": "ORD-1004",
  "restaurantName": "Chinese Dragon",
  "restaurantPhone": "+234 803 456 7894",
  "pickupAddress": "555 Beijing Ave, Chinatown",
  "dropoffAddress": "888 Canton St, Westside",
  "customerName": "Emily Chen",
  "customerPhone": "+234 801 234 5678",
  "deliveryFee": 18.00,
  "status": "accepted",
  "confirmationCode": "4567",
  "mealName": "Sweet and Sour Chicken",
  "mealQuantity": 2,
  "mealPrice": 32.00,
  "paymentCompleted": false,
  "createdAt": "2026-01-04T09:00:00Z"
}
```

**Response (404 Not Found):**
```json
{
  "details": "Order not found"
}
```

---

### 9. Get New Order (For Riders)
**GET** `/orders/new`

Poll for new available orders for riders.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Response (200 OK - Order Available):**
```json
{
  "id": "ORD-1005",
  "restaurantName": "Burger Palace",
  "restaurantPhone": "+234 810 555 1234",
  "pickupAddress": "123 Main St, Downtown",
  "dropoffAddress": "456 Oak Ave, Uptown",
  "customerName": "Sarah Johnson",
  "customerPhone": "+234 811 222 3333",
  "deliveryFee": 12.50,
  "confirmationCode": "1234",
  "mealName": "Cheeseburger Combo",
  "mealQuantity": 2,
  "mealPrice": 28.00,
  "estimatedDistance": "2.5 km",
  "estimatedDuration": "15 minutes"
}
```

**Response (200 OK - No Orders):**
```json
{
  "details": "No orders available at the moment"
}
```

---

### 10. Accept Order
**POST** `/orders/{orderId}/accept`

Rider accepts a new order.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "details": "Order accepted successfully",
  "orderId": "ORD-1005",
  "status": "accepted"
}
```

**Response (409 Conflict):**
```json
{
  "details": "This order has been accepted by another rider"
}
```

---

### 11. Update Order Status
**PUT** `/orders/{orderId}/status`

Update order status (arrived at restaurant, picked up, on the way, etc.).

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "status": "atRestaurant"
}
```

**Valid statuses:**
- `accepted`
- `atRestaurant`
- `onTheWay`
- `delivered`

**Response (200 OK):**
```json
{
  "details": "Order status updated successfully",
  "orderId": "ORD-1005",
  "status": "atRestaurant",
  "updatedAt": "2026-01-04T10:30:00Z"
}
```

**Response (400 Bad Request):**
```json
{
  "details": "Invalid status value"
}
```

---

### 12. Confirm Delivery
**POST** `/orders/{orderId}/confirm-delivery`

Confirm order delivery using customer's confirmation code.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "confirmationCode": "1234"
}
```

**Response (200 OK):**
```json
{
  "details": "Delivery confirmed successfully",
  "orderId": "ORD-1005",
  "status": "delivered",
  "deliveryFee": 12.50,
  "completedAt": "2026-01-04T11:00:00Z"
}
```

**Response (400 Bad Request):**
```json
{
  "details": "The confirmation code is incorrect"
}
```

---

## Payment Endpoints

### 13. Verify Bank Account
**POST** `/payments/verify-account`

Verify bank account details and fetch account name.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "bankName": "GTBank",
  "accountNumber": "0123456789"
}
```

**Response (200 OK):**
```json
{
  "accountName": "John Rider",
  "accountNumber": "0123456789",
  "bankName": "GTBank",
  "bankCode": "058"
}
```

**Response (404 Not Found):**
```json
{
  "details": "Could not verify account details"
}
```

---

### 14. Pay Restaurant
**POST** `/payments/restaurant-payment`

Transfer meal payment to restaurant's account.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "orderId": "ORD-1005",
  "bankDetails": {
    "bankName": "GTBank",
    "accountNumber": "0123456789",
    "accountName": "Restaurant Owner Ltd"
  },
  "amount": 28.00
}
```

**Response (200 OK):**
```json
{
  "details": "Payment successful",
  "transactionId": "TXN-123456",
  "orderId": "ORD-1005",
  "amount": 28.00,
  "status": "completed",
  "paidAt": "2026-01-04T10:45:00Z"
}
```

**Response (400 Bad Request):**
```json
{
  "details": "Insufficient funds to complete payment"
}
```

---

## Withdrawal Endpoints

### 15. Get Company Balance
**GET** `/company/balance`

Get current balance for company account.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "balance": 1250.50,
  "currency": "USD",
  "pendingWithdrawals": 0,
  "availableForWithdrawal": 1250.50
}
```

---

### 16. Withdraw Funds
**POST** `/company/withdraw`

Initiate withdrawal of company earnings.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "amount": 1250.50,
  "bankDetails": {
    "bankName": "Access Bank",
    "accountNumber": "0987654321",
    "accountName": "Company Holdings Ltd"
  }
}
```

**Response (200 OK):**
```json
{
  "details": "Withdrawal initiated successfully",
  "withdrawalId": "WD-123456",
  "amount": 1250.50,
  "status": "pending",
  "estimatedCompletionTime": "1-2 business days",
  "createdAt": "2026-01-04T12:00:00Z"
}
```

**Response (400 Bad Request):**
```json
{
  "details": "Insufficient balance for withdrawal"
}
```

---

### 17. Get Withdrawal History
**GET** `/company/withdrawals`

Get history of company withdrawals.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Query Parameters:**
- `page` (optional): Page number
- `limit` (optional): Items per page

**Response (200 OK):**
```json
{
  "withdrawals": [
    {
      "id": "WD-123456",
      "amount": 1250.50,
      "status": "completed",
      "bankDetails": {
        "bankName": "Access Bank",
        "accountNumber": "0987654321",
        "accountName": "Company Holdings Ltd"
      },
      "createdAt": "2026-01-03T12:00:00Z",
      "completedAt": "2026-01-04T10:00:00Z"
    }
  ],
  "pagination": {
    "currentPage": 1,
    "totalPages": 3,
    "totalItems": 50
  }
}
```

---

## Rider Status Endpoints

### 18. Toggle Online Status
**PUT** `/riders/online-status`

Toggle rider's online/offline status for receiving orders.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Request Body:**
```json
{
  "isOnline": true
}
```

**Response (200 OK):**
```json
{
  "isOnline": true,
  "updatedAt": "2026-01-04T09:00:00Z"
}
```

---

### 19. Get Rider Profile
**GET** `/riders/profile`

Get rider's profile information and statistics.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "id": "user_123",
  "name": "John Rider",
  "email": "rider@test.com",
  "phone": "+1234567890",
  "balance": 125.50,
  "isOnline": true,
  "stats": {
    "totalDeliveries": 150,
    "completedToday": 5,
    "averageRating": 4.8,
    "totalEarnings": 2500.00
  }
}
```

---

### 20. Get Company Profile
**GET** `/company/profile`

Get company profile information and statistics.

**Headers:**
```sh
Authorization: Bearer {accessToken}
```

**Response (200 OK):**
```json
{
  "id": "company_456",
  "name": "Fast Delivery Co.",
  "email": "c@test.com",
  "phone": "+1234567891",
  "balance": 1250.50,
  "stats": {
    "totalOrders": 500,
    "activeRiders": 25,
    "completedToday": 45,
    "totalRevenue": 15000.00
  }
}
```

---

## Common HTTP Status Codes

- **200 OK** - Request succeeded
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Missing or invalid authentication
- **403 Forbidden** - User doesn't have permission
- **404 Not Found** - Resource not found
- **409 Conflict** - Request conflicts with current state
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

---

## Authentication

All endpoints except `/auth/login`, `/auth/forgot-password/*` require authentication using JWT Bearer tokens:

```sh
Authorization: Bearer {accessToken}
```

Access tokens expire after 24 hours. Use the refresh token endpoint to get a new access token.

---

## Rate Limiting

- Authentication endpoints: 5 requests per minute
- Order polling (`/orders/new`): 1 request every 5 seconds
- All other endpoints: 60 requests per minute

Rate limit exceeded response (429):
```json
{
  "details": "Too many requests. Please try again in 60 seconds"
}
```

---

## Webhooks (Optional)

For real-time order notifications instead of polling:

**POST** `{your_webhook_url}`

```json
{
  "event": "order.created",
  "timestamp": "2026-01-04T10:00:00Z",
  "data": {
    "orderId": "ORD-1005",
    ...order details
  }
}
```

**Event types:**
- `order.created` - New order available
- `order.accepted` - Order accepted by rider
- `order.completed` - Order delivered
- `payment.completed` - Payment processed
- `withdrawal.completed` - Withdrawal completed

---

## Notes

1. All timestamps are in ISO 8601 format with UTC timezone
2. All monetary amounts are in USD (2 decimal places)
3. Phone numbers include country code (e.g., +234)
4. Order IDs follow format: ORD-{timestamp/sequence}
5. The 8-digit password reset code expires after 15 minutes
6. Delivery confirmation codes are 4 digits
7. For production, use HTTPS only
8. Implement request signing for sensitive operations
9. Log all financial transactions for audit trail
10. Implement proper data encryption for sensitive information
