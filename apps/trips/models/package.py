from django.db import models

from apps.core.models import TrackedModel
from apps.trips.models.trip import Trip


class Package(TrackedModel):
    trip = models.ForeignKey(Trip, on_delete=models.PROTECT, related_name="packages")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["trip", "slug"], name="unique_package_slug_per_trip")]
        indexes = [models.Index(fields=["trip", "is_active"], name="package_trip_active_idx"),]

    def __str__(self):
        return f"{self.trip.name} - {self.name}"
