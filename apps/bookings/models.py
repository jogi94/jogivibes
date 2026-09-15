from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from decimal import Decimal
from apps.bookings.enums import (
    BookingHoldStatus,
    BookingStatus,
    TripScheduleStatus,
    WaitlistEntryStatus,
    WaitlistOfferStatus,
    CancellationStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    RefundStatus,
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


class Payment(TimeStampedModel):
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
    )
    provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        default=PaymentProvider.MANUAL,
    )

    provider_order_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    provider_transaction_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    provider_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    paid_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_payments",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="payment_amount_gt_zero",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(paid_at__isnull=True)
                    | models.Q(
                        status__in=[
                            PaymentStatus.PAID,
                            PaymentStatus.REFUNDED,
                        ]
                    )
                ),
                name="payment_paid_at_only_after_payment",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(
                        status__in=[
                            PaymentStatus.PAID,
                            PaymentStatus.REFUNDED,
                        ]
                    )
                    | models.Q(paid_at__isnull=False)
                ),
                name="payment_paid_status_requires_paid_at",
            ),
            models.UniqueConstraint(
                fields=["provider", "provider_transaction_id"],
                condition=models.Q(provider_transaction_id__isnull=False),
                name="unique_payment_provider_transaction",
            ),
        ]
        indexes = [
            models.Index(
                fields=["booking", "status"],
                name="payment_booking_status_idx",
            ),
            models.Index(
                fields=["status", "created"],
                name="payment_status_created_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.currency != self.currency.upper():
            raise ValidationError(
                {"currency": "Currency must use uppercase ISO-4217 format."}
            )

        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError(
                {"currency": "Currency must be a 3-letter ISO-4217 code."}
            )

    def __str__(self):
        return f"Payment #{self.pk} - {self.amount} {self.currency}"


class CancellationPolicy(TimeStampedModel):
    trip_schedule = models.OneToOneField(
        "bookings.TripSchedule",
        on_delete=models.PROTECT,
        related_name="cancellation_policy",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - Schedule {self.trip_schedule_id}"


class CancellationPolicyRule(TimeStampedModel):
    policy = models.ForeignKey(
        CancellationPolicy,
        on_delete=models.PROTECT,
        related_name="rules",
    )
    minimum_days_before_departure = models.PositiveIntegerField()
    refund_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    minimum_days_before_departure__gte=0
                ),
                name="cancel_rule_days_gte_zero",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(refund_percentage__gte=Decimal("0.00"))
                    & models.Q(refund_percentage__lte=Decimal("100.00"))
                ),
                name="cancel_rule_refund_pct_valid",
            ),
            models.UniqueConstraint(
                fields=[
                    "policy",
                    "minimum_days_before_departure",
                ],
                name="unique_cancel_policy_threshold",
            ),
        ]

    def __str__(self):
        return (
            f"{self.policy_id}: "
            f"{self.minimum_days_before_departure} days -> "
            f"{self.refund_percentage}%"
        )


class Cancellation(TimeStampedModel):
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="cancellations",
    )

    status = models.CharField(
        max_length=20,
        choices=CancellationStatus.choices,
        default=CancellationStatus.REQUESTED,
    )

    reason = models.TextField()
    requested_at = models.DateTimeField()

    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_cancellations",
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="processed_cancellations",
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(null=True, blank=True)

    cancellation_policy = models.ForeignKey(
        CancellationPolicy,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cancellations",
    )
    cancellation_policy_rule = models.ForeignKey(
        CancellationPolicyRule,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cancellations",
    )

    policy_id_snapshot = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
    policy_name_snapshot = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    rule_min_days_snapshot = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    refund_percentage_snapshot = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    days_before_departure = models.IntegerField(
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["booking"],
                condition=models.Q(
                    status__in=[
                        CancellationStatus.REQUESTED,
                        CancellationStatus.APPROVED,
                    ]
                ),
                name="unique_active_booking_cancellation",
            ),
        ]
        indexes = [
            models.Index(
                fields=["booking", "status"],
                name="cancel_booking_status_idx",
            ),
            models.Index(
                fields=["status", "created"],
                name="cancel_status_created_idx",
            ),
        ]

    def __str__(self):
        return f"Cancellation #{self.pk} - Booking {self.booking_id}"


class Refund(TimeStampedModel):
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="refunds",
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="refunds",
    )
    cancellation = models.ForeignKey(
        Cancellation,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="refunds",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    currency = models.CharField(max_length=3)

    status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
    )

    calculated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    approved_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    override_reason = models.TextField(
        null=True,
        blank=True,
    )
    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="refund_overrides",
        null=True,
        blank=True,
    )

    provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        default=PaymentProvider.MANUAL,
    )
    provider_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    reason = models.TextField()

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    failure_reason = models.TextField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_refunds",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="refund_amount_gt_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(calculated_amount__gte=Decimal("0.00")),
                name="refund_calculated_amount_gte_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(approved_amount__gte=Decimal("0.00")),
                name="refund_approved_amount_gte_zero",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        approved_amount=models.F("calculated_amount")
                    )
                    | (
                        models.Q(override_reason__isnull=False)
                        & ~models.Q(override_reason="")
                        & models.Q(override_by__isnull=False)
                    )
                ),
                name="refund_override_requires_reason_and_user",
            ),
        ]
        indexes = [
            models.Index(
                fields=["booking", "status"],
                name="refund_booking_status_idx",
            ),
            models.Index(
                fields=["payment", "status"],
                name="refund_payment_status_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.currency != self.currency.upper():
            raise ValidationError(
                {"currency": "Currency must use uppercase ISO-4217 format."}
            )

        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValidationError(
                {"currency": "Currency must be a 3-letter ISO-4217 code."}
            )

    def __str__(self):
        return f"Refund #{self.pk} - {self.amount} {self.currency}"