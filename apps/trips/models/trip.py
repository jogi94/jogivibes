from django.contrib.postgres.fields import ArrayField
from django.db import models

from apps.core.models import TrackedModel
from apps.trips.enums import (
    Season,
    TripDifficulty,
    TripStatus,
    TripType
)
from apps.trips.models.destination import Destination


class Trip(TrackedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    type = models.CharField(max_length=30, choices=TripType.choices)
    status = models.CharField(max_length=20, choices=TripStatus.choices, default=TripStatus.DRAFT, db_index=True)
    description = models.TextField(blank=True)
    destination = models.ForeignKey(Destination, on_delete=models.PROTECT, related_name="trips")
    difficulty = models.CharField(max_length=20, choices=TripDifficulty.choices, blank=True)
    seasons = ArrayField(models.CharField(max_length=20, choices=Season.choices), default=list, blank=True)
    duration_days = models.PositiveSmallIntegerField()
    max_altitude_m = models.PositiveIntegerField(null=True, blank=True)
    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["type"], name="trip_type_idx"),
            models.Index(fields=["status"], name="trip_status_idx"),
            models.Index(fields=["difficulty"], name="trip_difficulty_idx"),
            models.Index(fields=["destination", "status"], name="trip_destination_status_idx"),
        ]

    def __str__(self):
        return self.name

