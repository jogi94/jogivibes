from datetime import timedelta
from decimal import Decimal

from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.bookings.enums import BookingHoldStatus, BookingStatus, WaitlistEntryStatus, WaitlistOfferStatus
from apps.bookings.models import Booking, BookingHold, Traveler, TripSchedule, WaitlistEntry, WaitlistOffer
from apps.bookings.services.availability import get_schedule_availability
from apps.bookings.services.create_booking import CapacityError, create_booking
from apps.bookings.services.create_hold import create_hold
from apps.bookings.services.create_waitlist_offer import create_waitlist_offer
from apps.bookings.services.override_capacity import override_capacity
from apps.trips.models.destination import Destination
from apps.trips.models.package import Package
from apps.trips.models.schedule_package import SchedulePackage
from apps.trips.models.trip import Trip
from apps.trips.models.pricing import Pricing
from apps.users.models import CustomUser


class CapacityTestMixin:
    def setUp(self):
        self.user = CustomUser.objects.create_user(phone_number="+919999999999")
        self.destination = Destination.objects.create(
            name="Test", slug="test", country="India"
        )
        self.trip = Trip.objects.create(
            name="Test Trip", slug="test-trip", type="trek",
            destination=self.destination, duration_days=1,
        )
        self.schedule = TripSchedule.objects.create(
            trip=self.trip, capacity=5, start_date="2026-10-01", end_date="2026-10-01",
        )
        self.package = Package.objects.create(
            trip=self.trip, name="Standard", slug="standard"
        )
        self.schedule_package = SchedulePackage.objects.create(
            trip_schedule=self.schedule, package=self.package
        )
        self.pricing = Pricing.objects.create(
            schedule_package=self.schedule_package, amount=Decimal("1000.00"),
            currency="INR", effective_from=timezone.now(),
        )

    def booking(self, capacity):
        return create_booking(
            schedule_id=self.schedule.id, booked_by=self.user, pricing=self.pricing,
            capacity_quantity=capacity,
        )


class CapacityInvariantTests(CapacityTestMixin, TestCase):
    def test_confirmed_booking_consumes_capacity(self):
        self.booking(3)
        availability = get_schedule_availability(self.schedule.id)
        self.assertEqual(availability.confirmed_quantity, 3)
        self.assertEqual(availability.available_quantity, 2)

    def test_hold_consumes_capacity_and_release_restores_it(self):
        hold = create_hold(
            schedule_id=self.schedule.id, quantity=2, created_by=self.user,
        )
        self.assertEqual(get_schedule_availability(self.schedule.id).available_quantity, 3)
        from apps.bookings.services.release_hold import release_hold
        release_hold(hold_id=hold.id)
        self.assertEqual(get_schedule_availability(self.schedule.id).available_quantity, 5)

    def test_pending_offer_consumes_capacity(self):
        traveler = Traveler.objects.create(first_name="FIFO", last_name="Traveler")
        WaitlistEntry.objects.create(
            trip_schedule=self.schedule, traveler=traveler, requested_quantity=2,
        )
        offer = create_waitlist_offer(schedule_id=self.schedule.id)
        self.assertEqual(offer.offered_quantity, 2)
        self.assertEqual(get_schedule_availability(self.schedule.id).available_quantity, 3)

    def test_waiting_entry_consumes_zero_capacity(self):
        traveler = Traveler.objects.create(first_name="Waiting", last_name="Traveler")
        WaitlistEntry.objects.create(
            trip_schedule=self.schedule, traveler=traveler, requested_quantity=10,
        )
        availability = get_schedule_availability(self.schedule.id)
        self.assertEqual(availability.pending_offer_quantity, 0)
        self.assertEqual(availability.available_quantity, 5)

    def test_over_allocation_is_rejected(self):
        self.booking(4)
        with self.assertRaises(CapacityError):
            self.booking(2)
        self.assertEqual(
            get_schedule_availability(self.schedule.id).available_quantity, 1
        )


    def test_pending_offer_is_partial_for_first_fifo_entry(self):
        first = Traveler.objects.create(first_name="First", last_name="Traveler")
        second = Traveler.objects.create(first_name="Second", last_name="Traveler")
        WaitlistEntry.objects.create(
            trip_schedule=self.schedule, traveler=first, requested_quantity=8,
        )
        WaitlistEntry.objects.create(
            trip_schedule=self.schedule, traveler=second, requested_quantity=1,
        )
        self.booking(4)

        offer = create_waitlist_offer(schedule_id=self.schedule.id)
        self.assertIsNotNone(offer)
        self.assertEqual(offer.offered_quantity, 1)
        self.assertEqual(offer.waitlist_entry.traveler_id, first.id)
        self.assertEqual(get_schedule_availability(self.schedule.id).available_quantity, 0)

    def test_hold_conversion_replaces_reserved_capacity_with_booking_capacity(self):
        hold = create_hold(
            schedule_id=self.schedule.id, quantity=3, created_by=self.user,
        )
        from apps.bookings.services.convert_hold import convert_hold_to_booking

        booking = convert_hold_to_booking(
            hold_id=hold.id, booked_by=self.user, pricing=self.pricing,
        )
        hold.refresh_from_db()
        self.assertEqual(hold.status, BookingHoldStatus.CONVERTED)
        self.assertEqual(booking.status, BookingStatus.CONFIRMED)
        self.assertEqual(booking.capacity_quantity, 3)
        self.assertEqual(get_schedule_availability(self.schedule.id).available_quantity, 2)

    def test_waitlist_offer_acceptance_replaces_reserved_capacity_with_booking_capacity(self):
        traveler = Traveler.objects.create(first_name="Offer", last_name="Traveler")
        entry = WaitlistEntry.objects.create(
            trip_schedule=self.schedule, traveler=traveler, requested_quantity=3,
        )
        offer = create_waitlist_offer(schedule_id=self.schedule.id)
        from apps.bookings.services.accept_waitlist_offer import accept_waitlist_offer

        booking = accept_waitlist_offer(
            offer_id=offer.id, booked_by=self.user, pricing=self.pricing,
        )
        offer.refresh_from_db()
        self.assertEqual(offer.status, WaitlistOfferStatus.ACCEPTED)
        self.assertEqual(booking.capacity_quantity, 3)
        self.assertEqual(get_schedule_availability(self.schedule.id).available_quantity, 2)

    def test_capacity_override_cannot_reduce_below_committed(self):
        self.booking(4)
        with self.assertRaises(ValueError):
            override_capacity(
                schedule_id=self.schedule.id, new_capacity=3,
                reason="invalid reduction", created_by=self.user,
            )

    def test_cancelling_waitlist_entry_declines_pending_offer_and_releases_capacity(self):
        traveler = Traveler.objects.create(
            first_name="Cancel",
            last_name="Traveler",
        )
        entry = WaitlistEntry.objects.create(
            trip_schedule=self.schedule,
            traveler=traveler,
            requested_quantity=2,
        )

        offer = create_waitlist_offer(schedule_id=self.schedule.id)

        self.assertEqual(offer.status, WaitlistOfferStatus.PENDING)
        self.assertEqual(
            get_schedule_availability(self.schedule.id).available_quantity,
            3,
        )

        from apps.bookings.services.cancel_waitlist_entry import cancel_waitlist_entry

        cancel_waitlist_entry(entry_id=entry.id)

        offer.refresh_from_db()
        entry.refresh_from_db()

        self.assertEqual(offer.status, WaitlistOfferStatus.DECLINED)
        self.assertEqual(entry.status, WaitlistEntryStatus.CANCELLED)
        self.assertEqual(
            get_schedule_availability(self.schedule.id).available_quantity,
            5,
        )

    def test_cancelled_waitlist_entry_cannot_accept_offer(self):
        traveler = Traveler.objects.create(
            first_name="Cancelled",
            last_name="Traveler",
        )
        entry = WaitlistEntry.objects.create(
            trip_schedule=self.schedule,
            traveler=traveler,
            requested_quantity=2,
        )

        offer = create_waitlist_offer(schedule_id=self.schedule.id)

        from apps.bookings.services.cancel_waitlist_entry import cancel_waitlist_entry
        from apps.bookings.services.accept_waitlist_offer import accept_waitlist_offer

        cancel_waitlist_entry(entry_id=entry.id)

        offer.refresh_from_db()
        self.assertEqual(offer.status, WaitlistOfferStatus.DECLINED)

        with self.assertRaises(ValueError):
            accept_waitlist_offer(
                offer_id=offer.id,
                booked_by=self.user,
                pricing=self.pricing,
            )


class CapacityConcurrencyTests(CapacityTestMixin, TransactionTestCase):
    reset_sequences = True

    def test_concurrent_allocation_attempts_cannot_exceed_capacity(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrency locking test requires PostgreSQL.")

        import threading
        from django.db import close_old_connections

        barrier = threading.Barrier(2)
        results = []
        errors = []

        def allocate():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                self.booking(3)
                results.append("success")
            except CapacityError:
                errors.append("capacity")
            finally:
                close_old_connections()

        threads = [threading.Thread(target=allocate) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(results.count("success"), 1)
        self.assertEqual(errors.count("capacity"), 1)

        availability = get_schedule_availability(self.schedule.id)
        self.assertEqual(availability.confirmed_quantity, 3)
        self.assertLessEqual(
            availability.confirmed_quantity
            + availability.held_quantity
            + availability.pending_offer_quantity,
            availability.capacity,
        )


def test_cancelling_waitlist_entry_declines_pending_offer_and_releases_capacity(self):
    traveler = Traveler.objects.create(
        first_name="Cancel",
        last_name="Traveler",
    )
    entry = WaitlistEntry.objects.create(
        trip_schedule=self.schedule,
        traveler=traveler,
        requested_quantity=2,
    )

    offer = create_waitlist_offer(schedule_id=self.schedule.id)

    self.assertEqual(offer.status, WaitlistOfferStatus.PENDING)
    self.assertEqual(
        get_schedule_availability(self.schedule.id).available_quantity,
        3,
    )

    from apps.bookings.services.cancel_waitlist_entry import cancel_waitlist_entry

    cancel_waitlist_entry(entry_id=entry.id)

    offer.refresh_from_db()
    entry.refresh_from_db()

    self.assertEqual(offer.status, WaitlistOfferStatus.DECLINED)
    self.assertEqual(entry.status, WaitlistEntryStatus.CANCELLED)
    self.assertEqual(
        get_schedule_availability(self.schedule.id).available_quantity,
        5,
    )


def test_cancelled_waitlist_entry_cannot_accept_offer(self):
    traveler = Traveler.objects.create(
        first_name="Cancelled",
        last_name="Traveler",
    )
    entry = WaitlistEntry.objects.create(
        trip_schedule=self.schedule,
        traveler=traveler,
        requested_quantity=2,
    )

    offer = create_waitlist_offer(schedule_id=self.schedule.id)

    from apps.bookings.services.cancel_waitlist_entry import cancel_waitlist_entry
    from apps.bookings.services.accept_waitlist_offer import accept_waitlist_offer

    cancel_waitlist_entry(entry_id=entry.id)

    offer.refresh_from_db()
    self.assertEqual(offer.status, WaitlistOfferStatus.DECLINED)

    with self.assertRaises(ValueError):
        accept_waitlist_offer(
            offer_id=offer.id,
            booked_by=self.user,
            pricing=self.pricing,
        )