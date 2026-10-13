
"""Import trip models so Django registers the complete trips domain."""

from .destination import Destination
from .trip import Trip
from .trip_image import TripImage
from .itinerary import Itinerary
from .package import Package
from .package_item import PackageItem
from .schedule_package import SchedulePackage
from .pricing import Pricing

__all__ = [
    "Destination",
    "Trip",
    "TripImage",
    "Itinerary",
    "Package",
    "PackageItem",
    "SchedulePackage",
    "Pricing",
]
