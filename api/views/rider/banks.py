"""Banks endpoint for rider/company withdrawals."""

from ninja import Router
from django.core.cache import cache
from ninja.errors import HttpError

from api.models.user import User
from api.schemas.rider_schemas import BanksResponse
from api.models.location import City

router = Router(tags=["Banks"])


# Mock bank data by country
# TODO: Replace with actual API call to bank service
MOCK_BANKS_BY_COUNTRY = {
    'Nigeria': [
        {'code': '044', 'name': 'Access Bank'},
        {'code': '063', 'name': 'Access Bank (Diamond)'},
        {'code': '050', 'name': 'Ecobank Nigeria'},
        {'code': '070', 'name': 'Fidelity Bank'},
        {'code': '011', 'name': 'First Bank of Nigeria'},
        {'code': '214', 'name': 'First City Monument Bank'},
        {'code': '058', 'name': 'Guaranty Trust Bank'},
        {'code': '030', 'name': 'Heritage Bank'},
        {'code': '301', 'name': 'Jaiz Bank'},
        {'code': '082', 'name': 'Keystone Bank'},
        {'code': '526', 'name': 'Parallex Bank'},
        {'code': '076', 'name': 'Polaris Bank'},
        {'code': '101', 'name': 'Providus Bank'},
        {'code': '221', 'name': 'Stanbic IBTC Bank'},
        {'code': '068', 'name': 'Standard Chartered Bank'},
        {'code': '232', 'name': 'Sterling Bank'},
        {'code': '100', 'name': 'Suntrust Bank'},
        {'code': '032', 'name': 'Union Bank of Nigeria'},
        {'code': '033', 'name': 'United Bank For Africa'},
        {'code': '215', 'name': 'Unity Bank'},
        {'code': '035', 'name': 'Wema Bank'},
        {'code': '057', 'name': 'Zenith Bank'},
    ],
    'Ghana': [
        {'code': 'GH001', 'name': 'Access Bank Ghana'},
        {'code': 'GH002', 'name': 'Ecobank Ghana'},
        {'code': 'GH003', 'name': 'Fidelity Bank Ghana'},
        {'code': 'GH004', 'name': 'First National Bank Ghana'},
        {'code': 'GH005', 'name': 'GCB Bank Limited'},
        {'code': 'GH006', 'name': 'Guaranty Trust Bank Ghana'},
        {'code': 'GH007', 'name': 'Standard Chartered Bank Ghana'},
        {'code': 'GH008', 'name': 'Stanbic Bank Ghana'},
        {'code': 'GH009', 'name': 'United Bank for Africa Ghana'},
        {'code': 'GH010', 'name': 'Zenith Bank Ghana'},
    ],
    'Kenya': [
        {'code': 'KE001', 'name': 'Kenya Commercial Bank'},
        {'code': 'KE002', 'name': 'Equity Bank'},
        {'code': 'KE003', 'name': 'Cooperative Bank of Kenya'},
        {'code': 'KE004', 'name': 'Standard Chartered Bank Kenya'},
        {'code': 'KE005', 'name': 'Barclays Bank of Kenya'},
        {'code': 'KE006', 'name': 'Diamond Trust Bank'},
        {'code': 'KE007', 'name': 'I&M Bank'},
        {'code': 'KE008', 'name': 'Stanbic Bank Kenya'},
    ],
    'United States': [
        {'code': 'US001', 'name': 'Bank of America'},
        {'code': 'US002', 'name': 'Chase Bank'},
        {'code': 'US003', 'name': 'Wells Fargo'},
        {'code': 'US004', 'name': 'Citibank'},
        {'code': 'US005', 'name': 'U.S. Bank'},
        {'code': 'US006', 'name': 'PNC Bank'},
        {'code': 'US007', 'name': 'Capital One'},
        {'code': 'US008', 'name': 'TD Bank'},
    ],
    # Default fallback banks
    'Default': [
        {'code': 'DEF001', 'name': 'International Bank'},
        {'code': 'DEF002', 'name': 'Global Bank'},
        {'code': 'DEF003', 'name': 'Universal Bank'},
    ]
}


def get_banks_for_country(country_name: str):
    """
    Get banks for a specific country from mock data.

    Args:
        country_name: Name of the country

    Returns:
        List of banks for that country
    """
    # Try to get exact match first
    if country_name in MOCK_BANKS_BY_COUNTRY:
        return MOCK_BANKS_BY_COUNTRY[country_name]

    # Fallback to default banks
    return MOCK_BANKS_BY_COUNTRY['Default']


@router.get("/", response={200: BanksResponse, 400: dict})
def get_banks(request):
    user: User = request.user
    city_id = user.city.id if user.city else ''
    
    # Create cache key based on city_id
    cache_key = f"banks_city_{city_id}"

    # Try to get from cache first
    cached_data = cache.get(cache_key)
    if cached_data:
        cached_data['cached'] = True
        return cached_data

    # Get city and its country
    try:
        city = City.objects.select_related('state__country').get(id=city_id)
    except City.DoesNotExist:
        raise HttpError(400, f"City with id {city_id} not found")

    # Get country name
    country_name = city.state.country.name if city.state and city.state.country else 'Default'

    # Get banks for this country
    banks = get_banks_for_country(country_name)

    # Prepare response
    response_data = {
        'banks': banks,
        'country': country_name,
        'cached': False
    }

    # Cache for 24 hours (86400 seconds)
    cache.set(cache_key, response_data, 86400)

    return response_data
