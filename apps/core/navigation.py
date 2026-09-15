from apps.trips.enums import Season, TripStatus, TripType
from apps.trips.models import Trip


def get_navigation():
    published = Trip.objects.filter(status=TripStatus.PUBLISHED)
    return {
        "trips": [
            ("Treks", TripType.TREK),
            ("Expeditions", TripType.EXPEDITION),
            ("Road Trips", TripType.BIKE_ROADTRIP),
            ("Family Holidays", TripType.FAMILY_HOLIDAYS),
        ],
        "seasonal": [
            ("Winter Holidays", Season.WINTER),
            ("Summer Holidays", Season.SUMMER),
        ],
        "published": published,
    }
