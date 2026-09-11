from django.db import transaction
from django.utils import timezone

from apps.bookings.enums import WaitlistEntryStatus, WaitlistOfferStatus
from apps.bookings.models import WaitlistEntry, WaitlistOffer


@transaction.atomic
def cancel_waitlist_entry(*, entry_id):
    entry_ref = (
        WaitlistEntry.objects
        .select_related("trip_schedule")
        .get(pk=entry_id)
    )

    schedule_model = entry_ref.trip_schedule.__class__
    schedule_model.objects.select_for_update().get(
        pk=entry_ref.trip_schedule_id
    )

    entry = WaitlistEntry.objects.select_for_update().get(pk=entry_id)

    if entry.status == WaitlistEntryStatus.CANCELLED:
        return entry

    pending_offer = (
        WaitlistOffer.objects
        .select_for_update()
        .filter(
            waitlist_entry_id=entry.id,
            status=WaitlistOfferStatus.PENDING,
        )
        .first()
    )

    if pending_offer is not None:
        pending_offer.status = WaitlistOfferStatus.DECLINED
        pending_offer.declined_at = timezone.now()
        pending_offer.save(
            update_fields=["status", "declined_at", "modified"]
        )

    entry.status = WaitlistEntryStatus.CANCELLED
    entry.cancelled_at = timezone.now()
    entry.save(
        update_fields=["status", "cancelled_at", "modified"]
    )

    return entry