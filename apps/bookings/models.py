from django.conf import settings
from django.db import models
from apps.core.models import TrackedModel
from apps.trips.models.trip import Trip
from apps.bookings.enums import TripScheduleStatus


# Create your models here.


class TripSchedule(TrackedModel):
    trip = models.ForeignKey(Trip, on_delete=models.PROTECT, related_name="schedules")
    capacity = models.PositiveIntegerField(default=25)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=TripScheduleStatus.choices, default=TripScheduleStatus.DRAFT,
                              db_index=True)

    class Meta:
        ordering = ["start_date"]
        indexes = [
            models.Index(fields=["trip", "start_date"], name="trip_schedule_trip_start_idx"),
            models.Index(fields=["status", "start_date"], name="trip_schedule_status_start_idx"),
        ]

    def __str__(self):
        return f"{self.trip.name} - {self.start_date}"


class Booking(TrackedModel):
    booked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings")
    trip_schedule = models.ForeignKey(TripSchedule, on_delete=models.PROTECT, related_name="bookings")
    pricing = models.ForeignKey("trips.Pricing", on_delete=models.PROTECT, related_name="bookings")
    capacity_quantity = models.PositiveIntegerField(default=1)

    package_id_snapshot = models.PositiveBigIntegerField()
    package_name_snapshot = models.CharField(max_length=255)
    package_slug_snapshot = models.CharField(max_length=280)

    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    price_currency = models.CharField(max_length=3)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    adjustment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2)


class Traveler(TrackedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="traveler_profile",)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "travelers_traveler"
        ordering = ["first_name", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class BookingTraveler(TrackedModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="booking_travelers")
    traveler = models.ForeignKey(Traveler, on_delete=models.PROTECT, related_name="booking_travelers")
    # ─── Booking-time snapshot ─────────────────────────────
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        db_table = "bookings_booking_traveler"

        constraints = [
            models.UniqueConstraint(
                fields=["booking", "traveler"],
                name="unique_traveler_per_booking",
            ),
        ]

        indexes = [
            models.Index(
                fields=["booking"],
                name="booking_traveler_booking_idx",
            ),
            models.Index(
                fields=["traveler"],
                name="booking_traveler_traveler_idx",
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()