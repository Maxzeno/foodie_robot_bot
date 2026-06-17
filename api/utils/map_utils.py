import requests
from django.conf import settings


def get_place_name(lat, lng):
    MAPBOX_TOKEN = settings.MAPBOX_TOKEN

    url = (
        f"https://api.mapbox.com/geocoding/v5/mapbox.places/"
        f"{lng},{lat}.json"
    )

    params = {
        "access_token": MAPBOX_TOKEN,
        "language": "en",
        "limit": 1
    }

    res = requests.get(url, params=params, timeout=10)
    data = res.json()

    if not data.get("features"):
        return None

    try:
        feature = data["features"][0]
        return {
            "full_address": feature["place_name"],
            "name": feature["text"],
        }
    except (IndexError, KeyError):
        return None
