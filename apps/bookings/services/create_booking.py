from decimal import Decimal

from django.db import transaction

from apps.bookings.enums import BookingStatus
from apps.bookings.models import Booking, TripSchedule
from apps.bookings.services.availability import get_schedule_availability


class CapacityError(Exception):
    """Raised when a capacity allocation cannot be completed."""


def _validate_pricing_for_schedule(pricing, schedule):
    if pricing.schedule_package.trip_schedule_id != schedule.id:
        raise ValueError("Pricing must belong to a package offered on this TripSchedule.")
    if not pricing.schedule_package.is_available:
        raise ValueError("The SchedulePackage is not available.")


def _create_confirmed_booking_locked(
    *,
    schedule,
    booked_by,
    pricing,
    capacity_quantity,
    quantity=None,
    discount_amount=Decimal("0"),
    adjustment_amount=Decimal("0"),
    created_by=None,
    reserved_capacity_quantity=0,
):
    if capacity_quantity <= 0:
        raise ValueError("capacity_quantity must be greater than zero.")

    availability = get_schedule_availability(schedule.id)
    available_for_booking = availability.available_quantity + reserved_capacity_quantity
    if capacity_quantity > available_for_booking:
        raise CapacityError("Insufficient capacity for this booking.")

    _validate_pricing_for_schedule(pricing, schedule)

    quantity = capacity_quantity if quantity is None else quantity
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero.")

    unit_price = pricing.amount
    subtotal = unit_price * quantity
    final_amount = subtotal - discount_amount + adjustment_amount

    return Booking.objects.create(
        booked_by=booked_by,
        trip_schedule=schedule,
        pricing=pricing,
        status=BookingStatus.CONFIRMED,
        capacity_quantity=capacity_quantity,
        package_id_snapshot=pricing.schedule_package.package_id,
        package_name_snapshot=pricing.schedule_package.package.name,
        package_slug_snapshot=pricing.schedule_package.package.slug,
        unit_price=unit_price,
        price_currency=pricing.currency,
        quantity=quantity,
        subtotal=subtotal,
        discount_amount=discount_amount,
        adjustment_amount=adjustment_amount,
        final_amount=final_amount,
        created_by=created_by,
        modified_by=created_by,
    )


@transaction.atomic
def create_booking(
    *,
    schedule_id,
    booked_by,
    pricing,
    capacity_quantity,
    quantity=None,
    discount_amount=Decimal("0"),
    adjustment_amount=Decimal("0"),
    created_by=None,
):
    schedule = TripSchedule.objects.select_for_update().get(pk=schedule_id)
    return _create_confirmed_booking_locked(
        schedule=schedule,
        booked_by=booked_by,
        pricing=pricing,
        capacity_quantity=capacity_quantity,
        quantity=quantity,
        discount_amount=discount_amount,
        adjustment_amount=adjustment_amount,
        created_by=created_by,
    )
