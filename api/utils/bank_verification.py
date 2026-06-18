"""Mock bank account verification for Nigerian banks."""

# Mock bank codes (Nigerian banks)
BANK_CODES = {
    'GTBank': '058',
    'Access Bank': '044',
    'Zenith Bank': '057',
    'First Bank': '011',
    'UBA': '033',
    'Fidelity Bank': '070',
    'Ecobank': '050',
    'Sterling Bank': '232',
    'Union Bank': '032',
    'Wema Bank': '035',
    'Stanbic IBTC': '221',
    'Polaris Bank': '076',
    'Keystone Bank': '082',
    'FCMB': '214',
}

# Mock account names for testing
MOCK_NAMES = [
    'John Doe',
    'Jane Smith',
    'Restaurant Owner Ltd',
    'Fast Foods Inc',
    'Delivery Services Co',
    'Acme Corporation',
    'Smith & Sons Restaurant',
    'Global Enterprises',
    'Coastal Ventures',
    'Metro Trading Co',
]


def verify_bank_account(bank_name, account_number):
    """
    Mock bank verification (for testing/development).

    In production, integrate with:
    - Paystack: https://paystack.com/docs/api/#verification-resolve-account-number
    - Flutterwave: https://developer.flutterwave.com/reference/account-verification
    - Mono: https://docs.mono.co/reference/account-verification

    Args:
        bank_name (str): Name of the bank
        account_number (str): 10-digit account number

    Returns:
        dict: Account information with accountName, accountNumber, bankName, bankCode

    Raises:
        ValueError: If account number is invalid or bank is not supported

    Example:
        verify_bank_account('GTBank', '0123456789')
        # Returns: {
        #     'accountName': 'John Doe',
        #     'accountNumber': '0123456789',
        #     'bankName': 'GTBank',
        #     'bankCode': '058'
        # }
    """
    # Validate account number
    if not account_number.isdigit() or len(account_number) != 10:
        raise ValueError("Invalid account number. Must be 10 digits.")

    # Get bank code
    bank_code = BANK_CODES.get(bank_name)
    if not bank_code:
        raise ValueError(f"Unsupported bank: {bank_name}")

    # Generate deterministic dummy account name based on account number
    name_index = int(account_number[-1]) % len(MOCK_NAMES)
    account_name = MOCK_NAMES[name_index]

    return {
        'accountName': account_name,
        'accountNumber': account_number,
        'bankName': bank_name,
        'bankCode': bank_code
    }
