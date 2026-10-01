from apps.trips.enums import Season, TripStatus, TripType
from apps.trips.models.trip import Trip


def get_navigation():
    published = Trip.objects.filter(status=TripStatus.PUBLISHED)

    trip_categories = [
        ("Treks", TripType.TREK, "/#trips"),
        ("Expeditions", TripType.EXPEDITION, "/#trips"),
        ("Road Trips", TripType.BIKE_ROADTRIP, "/#trips"),
        ("Family Holidays", TripType.FAMILY_HOLIDAYS, "/#trips"),
    ]
    seasonal_categories = [
        ("Winter Holidays", Season.WINTER, "/#seasonal"),
        ("Summer Holidays", Season.SUMMER, "/#seasonal"),
    ]

    trip_children = [
        {"label": label, "value": value, "url": url}
        for label, value, url in trip_categories
        if published.filter(type=value).exists()
    ]
    seasonal_children = [
        {"label": label, "value": value, "url": url}
        for label, value, url in seasonal_categories
        if published.filter(seasons__contains=[value]).exists()
    ]

    return {
        "trips": [{"label": "Trips", "children": trip_children}] if trip_children else [],
        "seasonal": [{"label": "Seasonal Trips", "children": seasonal_children}] if seasonal_children else [],
        "utility": [
            {"label": "About", "url": "/#about"},
            {"label": "Safety", "url": "/#safety"},
            {"label": "FAQ", "url": "/#faq"},
            {"label": "Contact", "url": "/#contact"},
            {"label": "WhatsApp", "url": "https://wa.me/918537003014", "external": True},
        ],
    }
