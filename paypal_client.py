"""Minimal PayPal Orders API v2 client (create + capture), using the
REST API directly via `requests` so no extra SDK dependency is needed.

Credentials come from admin-configured settings (Global Settings -> Integrations):
- paypal_client  (public Client ID, safe to expose to the frontend)
- PAYPAL_SECRET  (env var only, never stored in the DB or exposed to the frontend)
"""
import os

import requests

SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
LIVE_BASE = "https://api-m.paypal.com"


def is_configured(settings):
    return bool(settings.get("paypal_client")) and bool(os.environ.get("PAYPAL_SECRET"))


def _base_url(settings):
    return SANDBOX_BASE if settings.get("paypal_sandbox", True) else LIVE_BASE


def _get_access_token(settings):
    client_id = settings.get("paypal_client", "")
    secret = os.environ.get("PAYPAL_SECRET", "")
    response = requests.post(
        f"{_base_url(settings)}/v1/oauth2/token",
        auth=(client_id, secret),
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_order(settings, amount, currency="CAD", reference_id=""):
    """Create a PayPal order for the given amount. Returns the PayPal order id, or None on failure."""
    token = _get_access_token(settings)
    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": reference_id or "aluye-order",
                "amount": {"currency_code": currency, "value": f"{amount:.2f}"},
            }
        ],
    }
    response = requests.post(
        f"{_base_url(settings)}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def capture_order(settings, paypal_order_id):
    """Capture an approved PayPal order. Returns the capture response dict."""
    token = _get_access_token(settings)
    response = requests.post(
        f"{_base_url(settings)}/v2/checkout/orders/{paypal_order_id}/capture",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def extract_capture_id(capture_response):
    try:
        return capture_response["purchase_units"][0]["payments"]["captures"][0]["id"]
    except (KeyError, IndexError, TypeError):
        return capture_response.get("id", "")
