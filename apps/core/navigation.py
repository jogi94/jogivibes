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

    trips = [
        {
            "label": "Trips",
            "children": [
                {"label": label, "value": value, "url": url}
                for label, value, url in trip_categories
                if published.filter(type=value).exists()
            ],
        }
    ]
    trips = [item for item in trips if item["children"]]

    seasonal = [
        {
            "label": "Seasonal Trips",
            "children": [
                {"label": label, "value": value, "url": url}
                for label, value, url in seasonal_categories
                if published.filter(seasons__contains=[value]).exists()
            ],
        }
    ]
    seasonal = [item for item in seasonal if item["children"]]

    utility = [
        {"label": "About", "url": "/#about"},
        {"label": "Safety", "url": "/#safety"},
        {"label": "FAQ", "url": "/#faq"},
        {"label": "Contact", "url": "/#contact"},
        {"label": "WhatsApp", "url": "https://wa.me/918537003014", "external": True},
    ]

    return {
        "trips": trips,
        "seasonal": seasonal,
        "utility": utility,
    }
