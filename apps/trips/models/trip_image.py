from django.db import models

from apps.core.models import TrackedModel
from apps.trips.models.trip import Trip


class TripImage(TrackedModel):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="trips/%Y/%m/")
    caption = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_cover = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["trip", "sort_order"], name="trip_image_order_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["trip"], condition=models.Q(is_cover=True),
                name="unique_trip_cover_image",
            ),
        ]

    def __str__(self):
        return f"{self.trip.name} - Image {self.sort_order}"
