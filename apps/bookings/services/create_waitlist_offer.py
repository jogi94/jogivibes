from datetime import timedelta

from django.db import models, transaction
from django.utils import timezone

from apps.bookings.enums import WaitlistEntryStatus, WaitlistOfferStatus
from apps.bookings.models import TripSchedule, WaitlistEntry, WaitlistOffer
from apps.bookings.services.availability import get_schedule_availability

DEFAULT_OFFER_DURATION = timedelta(minutes=15)


@transaction.atomic
def create_waitlist_offer(*, schedule_id, expires_at=None, duration=None):
    schedule = TripSchedule.objects.select_for_update().get(pk=schedule_id)
    availability = get_schedule_availability(schedule.id)
    if availability.available_quantity <= 0:
        return None

    entry = (
        WaitlistEntry.objects
        .select_for_update()
        .filter(
            trip_schedule_id=schedule.id,
            status=WaitlistEntryStatus.WAITING,
            requested_quantity__gt=0,
        )
        .filter(~models.Exists(WaitlistOffer.objects.filter(
            waitlist_entry_id=models.OuterRef("pk"),
            status=WaitlistOfferStatus.PENDING,
        )))
        .order_by("created", "id")
        .first()
    )
    if entry is None:
        return None

    offered_quantity = min(entry.requested_quantity, availability.available_quantity)
    if offered_quantity <= 0:
        return None

    now = timezone.now()
    if expires_at is None:
        expires_at = now + (duration or DEFAULT_OFFER_DURATION)
    if expires_at <= now:
        raise ValueError("expires_at must be in the future.")

    return WaitlistOffer.objects.create(
        waitlist_entry=entry,
        offered_quantity=offered_quantity,
        status=WaitlistOfferStatus.PENDING,
        offered_at=now,
        expires_at=expires_at,
    )
