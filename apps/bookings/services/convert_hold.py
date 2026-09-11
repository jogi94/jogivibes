from django.db import transaction
from django.utils import timezone

from apps.bookings.enums import BookingHoldStatus
from apps.bookings.models import BookingHold
from apps.bookings.services.create_booking import _create_confirmed_booking_locked


@transaction.atomic
def convert_hold_to_booking(
    *,
    hold_id,
    booked_by,
    pricing,
    discount_amount=0,
    adjustment_amount=0,
    created_by=None,
):
    hold_ref = BookingHold.objects.select_related("trip_schedule").get(pk=hold_id)
    schedule_model = hold_ref.trip_schedule.__class__
    schedule = schedule_model.objects.select_for_update().get(pk=hold_ref.trip_schedule_id)
    hold = BookingHold.objects.select_for_update().get(pk=hold_id)

    if hold.status != BookingHoldStatus.ACTIVE:
        raise ValueError("Only an active hold can be converted.")
    if hold.expires_at <= timezone.now():
        raise ValueError("The hold has expired.")

    capacity_quantity = hold.quantity

    booking = _create_confirmed_booking_locked(
        schedule=schedule,
        booked_by=booked_by,
        pricing=pricing,
        capacity_quantity=capacity_quantity,
        quantity=capacity_quantity,
        discount_amount=discount_amount,
        adjustment_amount=adjustment_amount,
        created_by=created_by,
        reserved_capacity_quantity=hold.quantity,
    )
    hold.status = BookingHoldStatus.CONVERTED
    hold.released_at = timezone.now()
    hold.save(update_fields=["status", "released_at", "modified"])
    return booking
