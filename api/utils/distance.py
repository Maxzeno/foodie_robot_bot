import math
import requests
from django.conf import settings
from decimal import Decimal, ROUND_UP


# def haversine(lat1, lon1, lat2, lon2):
#     R = 6371  # Earth radius in kilometers. Use 3956 for miles.

#     dlat = math.radians(lat2 - lat1)
#     dlon = math.radians(lon2 - lon1)

#     a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) \
#         * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2

#     c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

#     return math.ceil(R * c) # km


def road_distance_km(start_lat, start_lng, end_lat, end_lng):
    MAPBOX_TOKEN = settings.MAPBOX_TOKEN
    url = (
        "https://api.mapbox.com/directions/v5/mapbox/driving/"
        f"{start_lng},{start_lat};{end_lng},{end_lat}"
    )

    params = {
        "access_token": MAPBOX_TOKEN,
        "overview": "false"
    }

    res = requests.get(url, params=params, timeout=10)
    data = res.json()

    if "routes" not in data:
        return None
    try:
        meters = data["routes"][0]["distance"]
        return meters / 1000  # km
    except (IndexError, KeyError):
        return None
    

def cal_delivery_fee(price_per_km, min_delivery_fee, lat1, lon1, lat2, lon2):
    distance = road_distance_km(lat1, lon1, lat2, lon2)
    if distance is None:
        raise Exception("Failed to get road distance for delivery fee calculation.")

    fee = Decimal(str(price_per_km)) * Decimal(str(distance))
    # round to whole number
    fee = fee.quantize(Decimal("1"), rounding=ROUND_UP)

    return max(fee, Decimal(min_delivery_fee))
