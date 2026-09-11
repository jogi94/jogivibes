from django.db import transaction
from django.utils import timezone

from apps.bookings.enums import BookingHoldStatus
from apps.bookings.models import BookingHold


@transaction.atomic
def release_hold(*, hold_id):
    hold_ref = BookingHold.objects.select_related("trip_schedule").get(pk=hold_id)
    schedule = type(hold_ref.trip_schedule).objects.select_for_update().get(pk=hold_ref.trip_schedule_id)
    hold = BookingHold.objects.select_for_update().get(pk=hold_id)

    if hold.status != BookingHoldStatus.ACTIVE:
        return hold

    hold.status = BookingHoldStatus.RELEASED
    hold.released_at = timezone.now()
    hold.save(update_fields=["status", "released_at", "modified"])
    return hold


@transaction.atomic
def expire_hold(*, hold_id):
    hold_ref = BookingHold.objects.select_related("trip_schedule").get(pk=hold_id)
    schedule = type(hold_ref.trip_schedule).objects.select_for_update().get(pk=hold_ref.trip_schedule_id)
    hold = BookingHold.objects.select_for_update().get(pk=hold_id)

    if hold.status != BookingHoldStatus.ACTIVE:
        return hold
    if hold.expires_at > timezone.now():
        raise ValueError("The hold has not expired.")

    hold.status = BookingHoldStatus.EXPIRED
    hold.released_at = timezone.now()
    hold.save(update_fields=["status", "released_at", "modified"])
    return hold
