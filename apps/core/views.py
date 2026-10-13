from django.db.models import Prefetch
from django.views.generic import TemplateView

from apps.trips.enums import TripStatus
from apps.trips.models.trip import Trip
from apps.trips.models.trip_image import TripImage

# Create your views here.


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        trips = Trip.objects.filter(status=TripStatus.PUBLISHED,
        ).prefetch_related(
            Prefetch(
                "images",
                queryset=TripImage.objects.order_by(
                    "-is_cover",
                    "sort_order",
                    "id",
                ),
                to_attr="carousel_images",
            )
        )

        featured_trips = []

        for trip in trips:
            # The cover image is preferred. The ordered queryset
            # supplies the fallback if no cover image exists.
            trip_image = next((image for image in trip.carousel_images if image.image), None,)

            # Don't display trips without an uploaded image.
            if trip_image is None:
                continue

            trip.carousel_image_url = trip_image.image.url
            trip.carousel_image_alt = (
                    trip_image.caption or trip.name
            )

            featured_trips.append(trip)

        context["featured_trips"] = featured_trips

        return context
