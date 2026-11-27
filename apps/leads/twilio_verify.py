"""Minimal Twilio Verify REST client; credentials stay in Django settings."""

import base64
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _request(resource, data):
    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
    service_sid = getattr(settings, "TWILIO_VERIFY_SERVICE_SID", "")
    if not account_sid or not auth_token or not service_sid:
        raise ImproperlyConfigured("Twilio Verify credentials are not configured.")

    token = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
    url = f"https://verify.twilio.com/v2/Services/{service_sid}/{resource}"
    request = Request(
        url,
        data=urlencode(data).encode(),
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read())
    except HTTPError as error:
        if resource == "VerificationCheck" and error.code == 404:
            return {"status": "not_found"}
        raise
    except URLError:
        raise


def send_sms_verification(*, phone_number):
    return _request("Verifications", {"To": phone_number, "Channel": "sms"})


def check_sms_verification(*, verification_sid, code):
    result = _request(
        "VerificationCheck",
        {"VerificationSid": verification_sid, "Code": code},
    )
    return result.get("status") == "approved"
