from django.db.models import Prefetch

from apps.trips.models.trip import Trip, TripCategory
from apps.trips.models import TripImage
from apps.trips.enums import TripStatus


def get_homepage_carousel_trips():
    return Trip.objects.filter(status=TripStatus.PUBLISHED, images__is_cover=True).distinct().prefetch_related(
            Prefetch("images",
                queryset=(TripImage.objects.exclude(image="").order_by("-is_cover","sort_order","id",)),
                     to_attr="carousel_images",))


def get_homepage_carousel_slides():
    carousel_slides = []
    for trip in get_homepage_carousel_trips():
        trip_image = next(iter(trip.carousel_images), None)
        if trip_image is None:
            continue
        trip.carousel_image_url = trip_image.image.url
        trip.carousel_image_alt = (trip_image.caption or trip.name)
        carousel_slides.append(trip)
    return carousel_slides


def get_trip_categories():
    return (
        TripCategory.objects
        .filter(
            trips__status=TripStatus.PUBLISHED,
            image__isnull=False,
        )
        .exclude(image="")
        .distinct()
        .order_by("name")
    )