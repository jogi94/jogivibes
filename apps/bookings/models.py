from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from apps.bookings.enums import (
    BookingHoldStatus,
    BookingStatus,
    TripScheduleStatus,
    WaitlistEntryStatus,
    WaitlistOfferStatus,
)
from apps.core.models import TimeStampedModel, TrackedModel
from apps.trips.models.trip import Trip


class TripSchedule(TrackedModel):
    trip = models.ForeignKey(Trip, on_delete=models.PROTECT, related_name="schedules")
    capacity = models.PositiveIntegerField(default=25)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=TripScheduleStatus.choices,
        default=TripScheduleStatus.DRAFT,
        db_index=True,
    )

    class Meta:
        ordering = ["start_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacity__gt=0),
                name="trip_schedule_capacity_gt_zero",
            ),
        ]
        indexes = [
            models.Index(fields=["trip", "start_date"], name="trip_schedule_trip_start_idx"),
            models.Index(fields=["status", "start_date"], name="trip_schedule_status_start_idx"),
        ]

    def __str__(self):
        return f"{self.trip.name} - {self.start_date}"


class Booking(TrackedModel):
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    trip_schedule = models.ForeignKey(
        TripSchedule,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    pricing = models.ForeignKey(
        "trips.Pricing",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.CONFIRMED,
        db_index=True,
    )
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

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacity_quantity__gt=0),
                name="booking_capacity_quantity_gt_zero",
            ),
        ]
        indexes = [
            models.Index(
                fields=["trip_schedule", "status"],
                name="booking_schedule_status_idx",
            ),
        ]


class BookingHold(TimeStampedModel):
    trip_schedule = models.ForeignKey(
        TripSchedule,
        on_delete=models.PROTECT,
        related_name="holds",
    )
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=BookingHoldStatus.choices,
        default=BookingHoldStatus.ACTIVE,
        db_index=True,
    )
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="booking_holds_created",
    )
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="booking_hold_quantity_gt_zero",
            ),
        ]
        indexes = [
            models.Index(
                fields=["trip_schedule", "status"],
                name="hold_schedule_status_idx",
            ),
            models.Index(
                fields=["trip_schedule", "status", "expires_at"],
                name="hold_schedule_status_exp_idx",
            ),
        ]


class WaitlistEntry(TimeStampedModel):
    trip_schedule = models.ForeignKey(
        TripSchedule,
        on_delete=models.PROTECT,
        related_name="waitlist_entries",
    )
    traveler = models.ForeignKey(
        "bookings.Traveler",
        on_delete=models.PROTECT,
        related_name="waitlist_entries",
    )
    requested_quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=WaitlistEntryStatus.choices,
        default=WaitlistEntryStatus.WAITING,
        db_index=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(requested_quantity__gt=0),
                name="waitlist_entry_quantity_gt_zero",
            ),
        ]
        indexes = [
            models.Index(
                fields=["trip_schedule", "status", "created", "id"],
                name="wait_entry_fifo_idx",
            ),
        ]


class WaitlistOffer(TimeStampedModel):
    waitlist_entry = models.ForeignKey(
        WaitlistEntry,
        on_delete=models.PROTECT,
        related_name="offers",
    )
    offered_quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=WaitlistOfferStatus.choices,
        default=WaitlistOfferStatus.PENDING,
        db_index=True,
    )
    offered_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(offered_quantity__gt=0),
                name="wait_offer_quantity_gt_zero",
            ),
            models.UniqueConstraint(
                fields=["waitlist_entry"],
                condition=models.Q(status=WaitlistOfferStatus.PENDING),
                name="unique_pending_wait_offer",
            ),
        ]
        indexes = [
            models.Index(
                fields=["waitlist_entry", "status"],
                name="offer_entry_status_idx",
            ),
            models.Index(
                fields=["status", "expires_at"],
                name="offer_status_exp_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.waitlist_entry_id and self.offered_quantity > self.waitlist_entry.requested_quantity:
            raise ValidationError("offered_quantity cannot exceed requested_quantity.")


class CapacityOverride(TimeStampedModel):
    trip_schedule = models.ForeignKey(
        TripSchedule,
        on_delete=models.PROTECT,
        related_name="capacity_overrides",
    )
    previous_capacity = models.PositiveIntegerField()
    new_capacity = models.PositiveIntegerField()
    reason = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="capacity_overrides_created",
    )

    class Meta:
        ordering = ["-created", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(previous_capacity__gt=0),
                name="capacity_override_previous_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(new_capacity__gt=0),
                name="capacity_override_new_gt_zero",
            ),
            models.CheckConstraint(
                condition=~models.Q(previous_capacity=models.F("new_capacity")),
                name="capacity_override_capacity_changed",
            ),
        ]
        indexes = [
            models.Index(
                fields=["trip_schedule", "created"],
                name="capacity_override_schedule_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("CapacityOverride records are append-only and cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("CapacityOverride records are append-only and cannot be deleted.")


class Traveler(TrackedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="traveler_profile",
    )
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
            models.Index(fields=["booking"], name="booking_traveler_booking_idx"),
            models.Index(fields=["traveler"], name="booking_traveler_traveler_idx"),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()
