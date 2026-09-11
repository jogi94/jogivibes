from django.db import models

from apps.core.models import TrackedModel
from apps.trips.models.trip import Trip


class Itinerary(TrackedModel):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name="itinerary")
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.trip.name} - Itinerary"