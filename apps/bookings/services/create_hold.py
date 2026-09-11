from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.bookings.enums import BookingHoldStatus
from apps.bookings.models import BookingHold, TripSchedule
from apps.bookings.services.availability import get_schedule_availability
from apps.bookings.services.create_booking import CapacityError

DEFAULT_HOLD_DURATION = timedelta(minutes=15)


@transaction.atomic
def create_hold(*, schedule_id, quantity, created_by, expires_at=None, duration=None):
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero.")

    schedule = TripSchedule.objects.select_for_update().get(pk=schedule_id)
    availability = get_schedule_availability(schedule.id)
    if quantity > availability.available_quantity:
        raise CapacityError("Insufficient capacity for this hold.")

    if expires_at is None:
        expires_at = timezone.now() + (duration or DEFAULT_HOLD_DURATION)
    if expires_at <= timezone.now():
        raise ValueError("expires_at must be in the future.")

    return BookingHold.objects.create(
        trip_schedule=schedule,
        quantity=quantity,
        status=BookingHoldStatus.ACTIVE,
        expires_at=expires_at,
        created_by=created_by,
    )
