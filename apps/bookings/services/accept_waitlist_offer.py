from django.db import transaction
from django.utils import timezone

from apps.bookings.enums import WaitlistEntryStatus, WaitlistOfferStatus
from apps.bookings.models import WaitlistOffer
from apps.bookings.services.create_booking import _create_confirmed_booking_locked


@transaction.atomic
def accept_waitlist_offer(
    *,
    offer_id,
    booked_by,
    pricing,
    created_by=None,
):
    offer_ref = (
        WaitlistOffer.objects
        .select_related("waitlist_entry__trip_schedule")
        .get(pk=offer_id)
    )
    schedule_model = offer_ref.waitlist_entry.trip_schedule.__class__
    schedule = schedule_model.objects.select_for_update().get(
        pk=offer_ref.waitlist_entry.trip_schedule_id
    )
    offer = (
        WaitlistOffer.objects
        .select_for_update()
        .select_related("waitlist_entry")
        .get(pk=offer_id)
    )

    if offer.status != WaitlistOfferStatus.PENDING:
        raise ValueError("Only a pending waitlist offer can be accepted.")

    # Prevent acceptance if the associated waitlist entry was cancelled.
    if offer.waitlist_entry.status != WaitlistEntryStatus.WAITING:
        raise ValueError("The waitlist entry is no longer waiting.")

    if offer.expires_at <= timezone.now():
        raise ValueError("The waitlist offer has expired.")

    booking = _create_confirmed_booking_locked(
        schedule=schedule,
        booked_by=booked_by,
        pricing=pricing,
        capacity_quantity=offer.offered_quantity,
        quantity=offer.offered_quantity,
        created_by=created_by,
        reserved_capacity_quantity=offer.offered_quantity,
    )
    offer.status = WaitlistOfferStatus.ACCEPTED
    offer.accepted_at = timezone.now()
    offer.save(update_fields=["status", "accepted_at", "modified"])

    entry = offer.waitlist_entry
    if offer.offered_quantity >= entry.requested_quantity:
        entry.status = WaitlistEntryStatus.CANCELLED
        entry.cancelled_at = timezone.now()
        entry.save(update_fields=["status", "cancelled_at", "modified"])
    else:
        entry.requested_quantity -= offer.offered_quantity
        entry.save(update_fields=["requested_quantity", "modified"])

    return booking
