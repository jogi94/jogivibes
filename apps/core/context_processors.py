from django.conf import settings
from apps.core.navigation import get_navigation


def navigation(request):
    return {
        "navigation": get_navigation(),
        "public_enquiry_only": settings.PUBLIC_ENQUIRY_ONLY,
    }
