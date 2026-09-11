from django.db import transaction
from django.utils import timezone

from apps.bookings.enums import WaitlistOfferStatus
from apps.bookings.models import WaitlistOffer


@transaction.atomic
def expire_waitlist_offer(*, offer_id):
    offer_ref = (
        WaitlistOffer.objects
        .select_related("waitlist_entry__trip_schedule")
        .get(pk=offer_id)
    )
    schedule_model = offer_ref.waitlist_entry.trip_schedule.__class__
    schedule = schedule_model.objects.select_for_update().get(
        pk=offer_ref.waitlist_entry.trip_schedule_id
    )
    offer = WaitlistOffer.objects.select_for_update().get(pk=offer_id)

    if offer.status != WaitlistOfferStatus.PENDING:
        return offer
    if offer.expires_at > timezone.now():
        raise ValueError("The waitlist offer has not expired.")

    offer.status = WaitlistOfferStatus.EXPIRED
    offer.save(update_fields=["status", "modified"])
    return offer


@transaction.atomic
def decline_waitlist_offer(*, offer_id):
    offer_ref = (
        WaitlistOffer.objects
        .select_related("waitlist_entry__trip_schedule")
        .get(pk=offer_id)
    )
    schedule_model = offer_ref.waitlist_entry.trip_schedule.__class__
    schedule = schedule_model.objects.select_for_update().get(
        pk=offer_ref.waitlist_entry.trip_schedule_id
    )
    offer = WaitlistOffer.objects.select_for_update().get(pk=offer_id)

    if offer.status != WaitlistOfferStatus.PENDING:
        return offer

    offer.status = WaitlistOfferStatus.DECLINED
    offer.declined_at = timezone.now()
    offer.save(update_fields=["status", "declined_at", "modified"])
    return offer
