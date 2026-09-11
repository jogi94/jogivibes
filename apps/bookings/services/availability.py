from dataclasses import dataclass

from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce

from apps.bookings.enums import BookingHoldStatus, BookingStatus, WaitlistOfferStatus
from apps.bookings.models import Booking, BookingHold, TripSchedule, WaitlistOffer


@dataclass(frozen=True)
class ScheduleAvailability:
    capacity: int
    confirmed_quantity: int
    held_quantity: int
    pending_offer_quantity: int
    available_quantity: int


def get_schedule_availability(schedule_id: int) -> ScheduleAvailability:
    schedule = TripSchedule.objects.only("id", "capacity").get(pk=schedule_id)

    confirmed = Booking.objects.filter(
        trip_schedule_id=schedule_id,
        status=BookingStatus.CONFIRMED,
    ).aggregate(total=Coalesce(Sum("capacity_quantity"), Value(0)))["total"]

    held = BookingHold.objects.filter(
        trip_schedule_id=schedule_id,
        status=BookingHoldStatus.ACTIVE,
    ).aggregate(total=Coalesce(Sum("quantity"), Value(0)))["total"]

    pending_offers = WaitlistOffer.objects.filter(
        waitlist_entry__trip_schedule_id=schedule_id,
        status=WaitlistOfferStatus.PENDING,
    ).aggregate(total=Coalesce(Sum("offered_quantity"), Value(0)))["total"]

    consumed = confirmed + held + pending_offers
    return ScheduleAvailability(
        capacity=schedule.capacity,
        confirmed_quantity=confirmed,
        held_quantity=held,
        pending_offer_quantity=pending_offers,
        available_quantity=max(schedule.capacity - consumed, 0),
    )
