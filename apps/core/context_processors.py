from apps.core.navigation import get_navigation


def navigation(request):
    return {"navigation": get_navigation()}
