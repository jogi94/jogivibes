from django.db import transaction

from apps.bookings.enums import BookingHoldStatus, BookingStatus, WaitlistOfferStatus
from apps.bookings.models import CapacityOverride, TripSchedule
from apps.bookings.services.availability import get_schedule_availability


@transaction.atomic
def override_capacity(*, schedule_id, new_capacity, reason, created_by):
    if new_capacity <= 0:
        raise ValueError("new_capacity must be greater than zero.")

    schedule = TripSchedule.objects.select_for_update().get(pk=schedule_id)
    previous_capacity = schedule.capacity
    if previous_capacity == new_capacity:
        raise ValueError("new_capacity must differ from current capacity.")

    availability = get_schedule_availability(schedule.id)
    committed = (
        availability.confirmed_quantity
        + availability.held_quantity
        + availability.pending_offer_quantity
    )
    if new_capacity < committed:
        raise ValueError("Capacity cannot be reduced below currently committed allocation.")

    audit = CapacityOverride.objects.create(
        trip_schedule=schedule,
        previous_capacity=previous_capacity,
        new_capacity=new_capacity,
        reason=reason,
        created_by=created_by,
    )
    schedule.capacity = new_capacity
    schedule.save(update_fields=["capacity", "modified"])
    return audit
