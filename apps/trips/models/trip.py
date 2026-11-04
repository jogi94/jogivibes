from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.urls import reverse
from apps.core.models import TrackedModel
from apps.trips.enums import (
    Season,
    TripDifficulty,
    TripStatus
)
from apps.trips.models.destination import Destination


from django.db import models
from apps.core.models import TrackedModel


class TripCategory(TrackedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="trip_categories/",
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Trip Category"
        verbose_name_plural = "Trip Categories"

    def __str__(self):
        return self.name


class Trip(TrackedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    category = models.ForeignKey("trips.TripCategory", on_delete=models.PROTECT, related_name="trips",
                                 null=True, blank=True)
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
            models.Index(fields=["status"], name="trip_status_idx"),
            models.Index(fields=["difficulty"], name="trip_difficulty_idx"),
            models.Index(fields=["destination", "status"], name="trip_destination_status_idx"),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("trips:trip_detail", args=(self.slug,))

    def get_create_url(self):
        return reverse("trips:trip_create", args=(self.slug,))

    def get_update_url(self):
        return reverse("trips:trip_update", args=(self.slug,))

    def get_delete_url(self):
        return reverse("trips:trip_delete", args=(self.slug,))

