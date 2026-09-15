from apps.trips.enums import Season, TripStatus, TripType
from apps.trips.models import Trip


def navigation(request):
    published = Trip.objects.filter(status=TripStatus.PUBLISHED)

    trip_categories = [
        ("Treks", TripType.TREK),
        ("Expeditions", TripType.EXPEDITION),
        ("Road Trips", TripType.BIKE_ROADTRIP),
        ("Family Holidays", TripType.FAMILY_HOLIDAYS),
    ]
    seasonal_categories = [
        ("Winter Holidays", Season.WINTER),
        ("Summer Holidays", Season.SUMMER),
    ]

    return {
        "navigation_trips": [
            (label, value)
            for label, value in trip_categories
            if published.filter(type=value).exists()
        ],
        "navigation_seasonal": [
            (label, value)
            for label, value in seasonal_categories
            if published.filter(seasons__contains=[value]).exists()
        ],
    }
