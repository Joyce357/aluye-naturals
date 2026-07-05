"""Google Maps Distance Matrix API client for distance-based shipping.

The API key comes from admin-configured settings (Global Settings -> Integrations)
or the GOOGLE_MAPS_API_KEY environment variable. All lookups degrade gracefully —
returning None — when the key is missing or the request fails, so callers can fall
back to the zone-based shipping calculator.
"""
import os

import requests

DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


def get_api_key(settings):
    return os.environ.get("GOOGLE_MAPS_API_KEY") or settings.get("google_maps_key", "")


def is_configured(settings):
    return bool(get_api_key(settings))


def get_distance_km(origin, destination, settings):
    """Driving distance in kilometres between origin and destination, or None if
    the API key is missing, the address can't be resolved, or the request fails."""
    api_key = get_api_key(settings)
    if not api_key or not origin.strip() or not destination.strip():
        return None
    try:
        response = requests.get(
            DISTANCE_MATRIX_URL,
            params={
                "origins": origin,
                "destinations": destination,
                "units": "metric",
                "key": api_key,
            },
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "OK":
            return None
        element = data["rows"][0]["elements"][0]
        if element.get("status") != "OK":
            return None
        return element["distance"]["value"] / 1000
    except (requests.RequestException, KeyError, IndexError, ValueError, TypeError):
        return None
