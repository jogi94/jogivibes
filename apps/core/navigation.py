
from apps.trips.enums import Season, TripStatus
from apps.trips.models.trip import Trip, TripCategory


def get_navigation():
    """
    Build the public navigation structure.
    Only categories with published content are exposed.
    """

    published_trips = Trip.objects.filter(
        status=TripStatus.PUBLISHED
    )

    trip_categories = TripCategory.objects.filter(
        trips__status=TripStatus.PUBLISHED
    ).distinct().order_by("name")

    trips = [
        {
            "label": category.name,
            "url": "/#trips",
        }
        for category in trip_categories
    ]

    seasonal_categories = [
        {
            "label": "Winter Holidays",
            "season": Season.WINTER,
        },
        {
            "label": "Summer Holidays",
            "season": Season.SUMMER,
        },
    ]

    seasonal_trips = [
        {
            "label": category["label"],
            "url": "/#seasonal",
        }
        for category in seasonal_categories
        if published_trips.filter(
            seasons__contains=[category["season"]]
        ).exists()
    ]

    return {
        "brand": {
            "label": "JOGI VIBES",
            "url": "/",
        },
        "groups": [
            {
                "label": "Trips",
                "url": "/trips/",
                "items": trips,
            },
            {
                "label": "Seasonal Trips",
                "items": seasonal_trips,
            },
        ],
        "links": [
            {"label": "About", "url": "/#about"},
            {"label": "Safety", "url": "/#safety"},
            {"label": "FAQ", "url": "/#faq"},
            {"label": "Contact", "url": "/#contact"},
            {"label": "Dashbaord", "url": "/dashboard"},
        ],
        "cta": {
            "label": "WhatsApp",
            "url": "https://wa.me/918527003014",
            "external": True,
        },
    }
