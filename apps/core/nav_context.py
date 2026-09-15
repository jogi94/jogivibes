from apps.core.navigation import get_navigation


def navigation(request):
    data = get_navigation()
    published = data["published"]
    data["trips"] = [
        (label, value)
        for label, value in data["trips"]
        if published.filter(type=value).exists()
    ]
    data["seasonal"] = [
        (label, value)
        for label, value in data["seasonal"]
        if published.filter(seasons__contains=[value]).exists()
    ]
    return {"navigation_trips": data["trips"], "navigation_seasonal": data["seasonal"]}
