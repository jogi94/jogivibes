from django.db import models

from apps.core.models import TrackedModel
from apps.trips.models.package import Package
from apps.bookings.models import TripSchedule
from django.core.exceptions import ValidationError


class SchedulePackage(TrackedModel):
    trip_schedule = models.ForeignKey(TripSchedule, on_delete=models.PROTECT, related_name="schedule_packages")
    package = models.ForeignKey(Package, on_delete=models.PROTECT, related_name="schedule_packages")
    is_available = models.BooleanField(default=True, db_index=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["trip_schedule", "package"], name="unique_package_per_schedule")]
        indexes = [models.Index(fields=["trip_schedule", "is_available"], name="schedule_package_available_idx")]

    def __str__(self):
        return f"{self.trip_schedule} - {self.package.name}"

    def clean(self):
        super().clean()
        if (self.package_id and self.trip_schedule_id and self.package.trip_id != self.trip_schedule.trip_id):
            raise ValidationError(
                "Package must belong to the same Trip as the TripSchedule."
            )