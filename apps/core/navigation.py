from apps.trips.enums import Season, TripStatus, TripType
from apps.trips.models.trip import Trip


def get_navigation():
    """
    Build the public navigation structure.

    Navigation data is kept separate from template presentation.
    Only categories with published content are exposed.
    """

    published_trips = Trip.objects.filter(
        status=TripStatus.PUBLISHED
    )

    trip_categories = [
        {
            "label": "Treks",
            "type": TripType.TREK,
        },
        {
            "label": "Expeditions",
            "type": TripType.EXPEDITION,
        },
        {
            "label": "Road Trips",
            "type": TripType.BIKE_ROADTRIP,
        },
        {
            "label": "Family Holidays",
            "type": TripType.FAMILY_HOLIDAYS,
        },
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

    trips = [
        {
            "label": category["label"],
            "url": "/#trips",
        }
        for category in trip_categories
        if published_trips.filter(
            type=category["type"]
        ).exists()
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
                "items": trips,
            },
            {
                "label": "Seasonal Trips",
                "items": seasonal_trips,
            },
        ],
        "links": [
            {
                "label": "About",
                "url": "/#about",
            },
            {
                "label": "Safety",
                "url": "/#safety",
            },
            {
                "label": "FAQ",
                "url": "/#faq",
            },
            {
                "label": "Contact",
                "url": "/#contact",
            },
        ],
        "cta": {
            "label": "WhatsApp",
            "url": "https://wa.me/918527003014",
            "external": True,
        },
    }