from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.bookings.enums import BookingStatus, CancellationStatus
from apps.bookings.models import Booking, Cancellation
from apps.bookings.services.policy import (
    select_cancellation_policy_rule,
)


def _lock_booking(booking_id):
    return (
        Booking.objects
        .select_for_update()
        .get(pk=booking_id)
    )


def _get_cancellation(cancellation_id):
    """
    Fetch cancellation without locking.

    Booking must be locked first.
    """
    return Cancellation.objects.get(pk=cancellation_id)


def request_cancellation(
    *,
    booking_id,
    reason,
    requested_by,
):
    with transaction.atomic():

        booking = _lock_booking(booking_id)

        if booking.status != BookingStatus.CONFIRMED:
            raise ValidationError(
                "Only CONFIRMED bookings can be cancelled."
            )

        if Cancellation.objects.filter(
            booking_id=booking.id,
            status__in=[
                CancellationStatus.REQUESTED,
                CancellationStatus.APPROVED,
            ],
        ).exists():
            raise ValidationError(
                "This booking already has an active cancellation."
            )

        return Cancellation.objects.create(
            booking=booking,
            status=CancellationStatus.REQUESTED,
            reason=reason,
            requested_at=timezone.now(),
            requested_by=requested_by,
        )


def approve_cancellation(
    *,
    cancellation_id,
    processed_by,
):
    """
    REQUESTED -> APPROVED

    Lock order:
        Booking -> Cancellation
    """
    with transaction.atomic():

        cancellation = _get_cancellation(cancellation_id)

        booking = _lock_booking(cancellation.booking_id)

        cancellation = (
            Cancellation.objects
            .select_for_update()
            .get(pk=cancellation_id)
        )

        if cancellation.status != CancellationStatus.REQUESTED:
            raise ValidationError(
                "Only REQUESTED cancellations can be approved."
            )

        if booking.status != BookingStatus.CONFIRMED:
            raise ValidationError(
                "Only CONFIRMED bookings can be approved."
            )

        policy, rule, days_before_departure = (
            select_cancellation_policy_rule(
                trip_schedule=booking.trip_schedule,
                cancellation_at=timezone.now(),
            )
        )

        now = timezone.now()

        cancellation.status = CancellationStatus.APPROVED
        cancellation.approved_at = now
        cancellation.processed_by = processed_by

        cancellation.cancellation_policy = policy
        cancellation.cancellation_policy_rule = rule

        cancellation.policy_id_snapshot = policy.id
        cancellation.policy_name_snapshot = policy.name
        cancellation.rule_min_days_snapshot = (
            rule.minimum_days_before_departure
        )
        cancellation.refund_percentage_snapshot = (
            rule.refund_percentage
        )
        cancellation.days_before_departure = days_before_departure

        cancellation.save()

        return cancellation


def reject_cancellation(
    *,
    cancellation_id,
    processed_by,
    rejection_reason,
):
    """
    REQUESTED -> REJECTED

    Lock order:
        Booking -> Cancellation
    """
    with transaction.atomic():

        cancellation = _get_cancellation(cancellation_id)

        booking = _lock_booking(cancellation.booking_id)

        cancellation = (
            Cancellation.objects
            .select_for_update()
            .get(pk=cancellation_id)
        )

        if cancellation.status != CancellationStatus.REQUESTED:
            raise ValidationError(
                "Only REQUESTED cancellations can be rejected."
            )

        cancellation.status = CancellationStatus.REJECTED
        cancellation.processed_by = processed_by
        cancellation.rejection_reason = rejection_reason

        cancellation.save()

        return cancellation


def cancel_cancellation_request(
    *,
    cancellation_id,
    processed_by,
):
    """
    REQUESTED -> CANCELLED

    Lock order:
        Booking -> Cancellation
    """
    with transaction.atomic():

        cancellation = _get_cancellation(cancellation_id)

        booking = _lock_booking(cancellation.booking_id)

        cancellation = (
            Cancellation.objects
            .select_for_update()
            .get(pk=cancellation_id)
        )

        if cancellation.status != CancellationStatus.REQUESTED:
            raise ValidationError(
                "Only REQUESTED cancellations can be withdrawn."
            )

        cancellation.status = CancellationStatus.CANCELLED
        cancellation.processed_by = processed_by

        cancellation.save()

        return cancellation


def complete_cancellation(
    *,
    cancellation_id,
    processed_by,
):
    """
    APPROVED -> COMPLETED

    Only here:
        Booking CONFIRMED -> CANCELLED
    """
    with transaction.atomic():

        cancellation = _get_cancellation(cancellation_id)

        booking = _lock_booking(cancellation.booking_id)

        cancellation = (
            Cancellation.objects
            .select_for_update()
            .get(pk=cancellation_id)
        )

        if cancellation.status != CancellationStatus.APPROVED:
            raise ValidationError(
                "Only APPROVED cancellations can be completed."
            )

        if booking.status != BookingStatus.CONFIRMED:
            raise ValidationError(
                "Only CONFIRMED bookings can complete cancellation."
            )

        now = timezone.now()

        cancellation.status = CancellationStatus.COMPLETED
        cancellation.completed_at = now
        cancellation.processed_by = processed_by

        cancellation.save()

        booking.status = BookingStatus.CANCELLED
        booking.save(update_fields=["status"])

        return cancellation