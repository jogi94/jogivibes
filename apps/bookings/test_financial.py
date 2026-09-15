from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.db import models
from django.db.models import Sum
from django.db import connection, close_old_connections
from django.test import TransactionTestCase

from apps.bookings.enums import (
    BookingStatus,
    CancellationStatus,
    PaymentMethod,
    PaymentProvider,
    PaymentStatus,
    RefundStatus,
)
from apps.bookings.models import (
    Booking,
    Cancellation,
    CancellationPolicy,
    CancellationPolicyRule,
    Payment,
    Refund,
)
from apps.bookings.services.cancellation import (
    approve_cancellation,
    cancel_cancellation_request,
    complete_cancellation,
    reject_cancellation,
    request_cancellation,
)
from apps.bookings.services.payment import (
    cancel_payment,
    create_payment,
    get_booking_payment_position,
    mark_payment_failed,
    mark_payment_paid,
)
from apps.bookings.services.policy import (
    calculate_days_before_departure,
    select_cancellation_policy_rule,
    validate_policy_usable,
)
from apps.bookings.services.refund import (
    complete_refund,
    create_refund,
    fail_refund,
    start_refund,
)
from apps.trips.models.destination import Destination
from apps.trips.models.package import Package
from apps.trips.models.pricing import Pricing
from apps.trips.models.schedule_package import SchedulePackage
from apps.trips.models.trip import Trip
from apps.users.models import CustomUser


class FinancialTestMixin:
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone_number="+919999999999"
        )
        self.second_user = CustomUser.objects.create_user(
            phone_number="+918888888888"
        )

        self.destination = Destination.objects.create(
            name="Financial Test",
            slug="financial-test",
            country="India",
        )

        self.trip = Trip.objects.create(
            name="Financial Test Trip",
            slug="financial-test-trip",
            type="trek",
            destination=self.destination,
            duration_days=1,
        )

        self.schedule = self._create_schedule()

        self.package = Package.objects.create(
            trip=self.trip,
            name="Standard",
            slug="standard",
        )

        self.schedule_package = SchedulePackage.objects.create(
            trip_schedule=self.schedule,
            package=self.package,
        )

        self.pricing = Pricing.objects.create(
            schedule_package=self.schedule_package,
            amount=Decimal("1000.00"),
            currency="INR",
            effective_from=timezone.now(),
        )

        self.booking = self._create_booking()

    def _create_schedule(self, capacity=10, start_date=date(2026, 10, 1)):
        return self._create_schedule_with_dates(capacity=capacity, start_date=start_date, end_date=start_date)

    def _create_schedule_with_dates(self, capacity=10, start_date=date(2026, 10, 1), end_date=date(2026, 10, 1)):
        from apps.bookings.models import TripSchedule

        return TripSchedule.objects.create(trip=self.trip, capacity=capacity, start_date=start_date, end_date=end_date)

    def _create_booking(self, final_amount=Decimal("1000.00")):
        return Booking.objects.create(
            booked_by=self.user,
            trip_schedule=self.schedule,
            pricing=self.pricing,
            status=BookingStatus.CONFIRMED,
            capacity_quantity=1,
            package_id_snapshot=self.package.id,
            package_name_snapshot=self.package.name,
            package_slug_snapshot=self.package.slug,
            unit_price=Decimal("1000.00"),
            price_currency="INR",
            quantity=1,
            subtotal=Decimal("1000.00"),
            discount_amount=Decimal("0.00"),
            adjustment_amount=Decimal("0.00"),
            final_amount=final_amount,
        )

    def create_policy(self, rules=None, active=True):
        policy = CancellationPolicy.objects.create(
            trip_schedule=self.schedule,
            name="Standard Cancellation Policy",
            description="Financial test policy",
            is_active=active,
        )

        for minimum_days, refund_percentage in rules or [
            (30, Decimal("90.00")),
            (15, Decimal("75.00")),
            (7, Decimal("50.00")),
            (0, Decimal("0.00")),
        ]:
            CancellationPolicyRule.objects.create(
                policy=policy,
                minimum_days_before_departure=minimum_days,
                refund_percentage=refund_percentage,
            )

        return policy

    def create_paid_payment(self, amount=Decimal("1000.00"), booking=None):
        booking = booking or self.booking

        payment = create_payment(
            booking_id=booking.id,
            amount=amount,
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.MANUAL,
            created_by=self.user,
        )

        mark_payment_paid(payment_id=payment.id)
        return Payment.objects.get(pk=payment.id)


class PaymentTests(FinancialTestMixin, TestCase):
    def test_payment_starts_pending(self):
        payment = create_payment(
            booking_id=self.booking.id,
            amount=Decimal("1000.00"),
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.MANUAL,
            created_by=self.user,
        )

        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertIsNone(payment.paid_at)

    def test_payment_can_be_marked_paid(self):
        payment = create_payment(
            booking_id=self.booking.id,
            amount=Decimal("1000.00"),
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.MANUAL,
            created_by=self.user,
        )

        mark_payment_paid(payment_id=payment.id)

        payment.refresh_from_db()

        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertIsNotNone(payment.paid_at)

    def test_paid_payment_cannot_be_paid_again(self):
        payment = self.create_paid_payment()

        with self.assertRaises(ValidationError):
            mark_payment_paid(payment_id=payment.id)

    def test_pending_payment_can_fail(self):
        payment = create_payment(
            booking_id=self.booking.id,
            amount=Decimal("1000.00"),
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.MANUAL,
            created_by=self.user,
        )

        mark_payment_failed(
            payment_id=payment.id,
            failure_reason="Test failure",
        )

        payment.refresh_from_db()

        self.assertEqual(payment.status, PaymentStatus.FAILED)
        self.assertEqual(payment.failure_reason, "Test failure")
        self.assertIsNone(payment.paid_at)

    def test_pending_payment_can_be_cancelled(self):
        payment = create_payment(
            booking_id=self.booking.id,
            amount=Decimal("1000.00"),
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.MANUAL,
            created_by=self.user,
        )

        cancel_payment(payment_id=payment.id)

        payment.refresh_from_db()

        self.assertEqual(payment.status, PaymentStatus.CANCELLED)
        self.assertIsNone(payment.paid_at)

    def test_provider_transaction_id_must_be_unique(self):
        create_payment(
            booking_id=self.booking.id,
            amount=Decimal("500.00"),
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.MANUAL,
            provider_transaction_id="TXN-001",
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            create_payment(
                booking_id=self.booking.id,
                amount=Decimal("500.00"),
                currency="INR",
                method=PaymentMethod.UPI,
                provider=PaymentProvider.MANUAL,
                provider_transaction_id="TXN-001",
                created_by=self.user,
            )

    def test_same_transaction_id_can_exist_for_different_providers(self):
        create_payment(
            booking_id=self.booking.id,
            amount=Decimal("500.00"),
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.MANUAL,
            provider_transaction_id="TXN-001",
            created_by=self.user,
        )

        payment = create_payment(
            booking_id=self.booking.id,
            amount=Decimal("500.00"),
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.RAZORPAY,
            provider_transaction_id="TXN-001",
            created_by=self.user,
        )

        self.assertIsNotNone(payment.pk)

    def test_payment_cannot_exceed_booking_final_amount(self):
        payment = create_payment(
            booking_id=self.booking.id,
            amount=Decimal("1001.00"),
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.MANUAL,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            mark_payment_paid(payment_id=payment.id)

    def test_multiple_payments_can_settle_booking_without_overpayment(self):
        first = create_payment(
            booking_id=self.booking.id,
            amount=Decimal("600.00"),
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.MANUAL,
            created_by=self.user,
        )
        mark_payment_paid(payment_id=first.id)

        second = create_payment(
            booking_id=self.booking.id,
            amount=Decimal("400.00"),
            currency="INR",
            method=PaymentMethod.CARD,
            provider=PaymentProvider.MANUAL,
            created_by=self.user,
        )
        mark_payment_paid(payment_id=second.id)

        total = Payment.objects.filter(
            booking=self.booking,
            status=PaymentStatus.PAID,
        ).aggregate(total=Sum("amount"))["total"]

        self.assertEqual(total, Decimal("1000.00"))

    def test_booking_payment_position_is_paid(self):
        self.create_paid_payment()

        position = get_booking_payment_position(self.booking.id)

        self.assertEqual(position, "PAID")


class CancellationPolicyTests(FinancialTestMixin, TestCase):
    def test_days_before_departure_are_calculated_from_local_date(self):
        cancellation_at = timezone.make_aware(
            timezone.datetime(2026, 9, 20, 12, 0)
        )

        days = calculate_days_before_departure(
            self.schedule,
            cancellation_at=cancellation_at,
        )

        self.assertEqual(days, 11)

    def test_days_before_departure_never_go_below_zero(self):
        cancellation_at = timezone.make_aware(
            timezone.datetime(2026, 10, 5, 12, 0)
        )

        days = calculate_days_before_departure(
            self.schedule,
            cancellation_at=cancellation_at,
        )

        self.assertEqual(days, 0)

    def test_highest_applicable_threshold_wins(self):
        policy = self.create_policy()

        policy, rule, days = select_cancellation_policy_rule(
            self.schedule,
            cancellation_at=timezone.make_aware(
                timezone.datetime(2026, 9, 10, 12, 0)
            ),
        )

        self.assertEqual(days, 21)
        self.assertEqual(rule.minimum_days_before_departure, 15)
        self.assertEqual(rule.refund_percentage, Decimal("75.00"))

    def test_policy_without_zero_day_rule_is_not_usable(self):
        policy = self.create_policy(
            rules=[
                (30, Decimal("90.00")),
                (15, Decimal("75.00")),
            ]
        )

        with self.assertRaises(ValidationError):
            validate_policy_usable(policy)


class CancellationTests(FinancialTestMixin, TestCase):
    def test_cancellation_request_starts_requested(self):
        cancellation = request_cancellation(
            booking_id=self.booking.id,
            requested_by=self.user,
            reason="Personal reason",
        )

        self.assertEqual(
            cancellation.status,
            CancellationStatus.REQUESTED,
        )
        self.assertEqual(
            cancellation.booking_id,
            self.booking.id,
        )

    def test_cancellation_can_be_approved(self):
        self.create_policy()

        cancellation = request_cancellation(
            booking_id=self.booking.id,
            requested_by=self.user,
            reason="Personal reason",
        )

        approve_cancellation(
            cancellation_id=cancellation.id,
            processed_by=self.second_user,
        )

        cancellation.refresh_from_db()

        self.assertEqual(
            cancellation.status,
            CancellationStatus.APPROVED,
        )
        self.assertIsNotNone(cancellation.approved_at)
        self.assertIsNotNone(cancellation.cancellation_policy_id)
        self.assertIsNotNone(cancellation.cancellation_policy_rule_id)
        self.assertEqual(
            cancellation.policy_name_snapshot,
            "Standard Cancellation Policy",
        )

    def test_cancellation_can_be_rejected(self):
        cancellation = request_cancellation(
            booking_id=self.booking.id,
            requested_by=self.user,
            reason="Personal reason",
        )

        reject_cancellation(
            cancellation_id=cancellation.id,
            processed_by=self.second_user,
            rejection_reason="Not eligible",
        )

        cancellation.refresh_from_db()

        self.assertEqual(
            cancellation.status,
            CancellationStatus.REJECTED,
        )
        self.assertEqual(
            cancellation.rejection_reason,
            "Not eligible",
        )

    def test_requested_cancellation_can_be_cancelled(self):
        cancellation = request_cancellation(
            booking_id=self.booking.id,
            requested_by=self.user,
            reason="Changed my mind",
        )

        cancel_cancellation_request(cancellation_id=cancellation.id, processed_by=self.user)

        cancellation.refresh_from_db()

        self.assertEqual(
            cancellation.status,
            CancellationStatus.CANCELLED,
        )

    def test_booking_is_cancelled_only_when_cancellation_completes(self):
        self.create_policy()

        cancellation = request_cancellation(
            booking_id=self.booking.id,
            requested_by=self.user,
            reason="Personal reason",
        )

        approve_cancellation(
            cancellation_id=cancellation.id,
            processed_by=self.second_user,
        )

        self.booking.refresh_from_db()

        self.assertEqual(
            self.booking.status,
            BookingStatus.CONFIRMED,
        )

        complete_cancellation(
            cancellation_id=cancellation.id,
            processed_by=self.second_user,
        )

        self.booking.refresh_from_db()
        cancellation.refresh_from_db()

        self.assertEqual(
            cancellation.status,
            CancellationStatus.COMPLETED,
        )
        self.assertEqual(
            self.booking.status,
            BookingStatus.CANCELLED,
        )

    def test_only_one_active_cancellation_is_allowed(self):
        request_cancellation(
            booking_id=self.booking.id,
            requested_by=self.user,
            reason="First request",
        )

        with self.assertRaises(ValidationError):
            request_cancellation(
                booking_id=self.booking.id,
                requested_by=self.user,
                reason="Second request",
            )

    def test_policy_snapshot_is_preserved(self):
        policy = self.create_policy()

        cancellation = request_cancellation(
            booking_id=self.booking.id,
            requested_by=self.user,
            reason="Personal reason",
        )

        approve_cancellation(
            cancellation_id=cancellation.id,
            processed_by=self.second_user,
        )

        cancellation.refresh_from_db()

        original_policy_name = cancellation.policy_name_snapshot
        original_rule = cancellation.rule_min_days_snapshot
        original_percentage = cancellation.refund_percentage_snapshot

        policy.name = "Changed Policy Name"
        policy.save(update_fields=["name", "modified"])

        self.assertEqual(
            cancellation.policy_name_snapshot,
            original_policy_name,
        )
        self.assertEqual(
            cancellation.rule_min_days_snapshot,
            original_rule,
        )
        self.assertEqual(
            cancellation.refund_percentage_snapshot,
            original_percentage,
        )


class RefundTests(FinancialTestMixin, TestCase):
    def test_refund_starts_pending(self):
        payment = self.create_paid_payment()

        refund = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("500.00"),
            currency="INR",
            calculated_amount=Decimal("500.00"),
            approved_amount=Decimal("500.00"),
            reason="Test refund",
            created_by=self.user,
        )

        self.assertEqual(
            refund.status,
            RefundStatus.PENDING,
        )

    def test_refund_can_move_to_processing(self):
        payment = self.create_paid_payment()

        refund = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("500.00"),
            currency="INR",
            calculated_amount=Decimal("500.00"),
            approved_amount=Decimal("500.00"),
            reason="Test refund",
            created_by=self.user,
        )

        start_refund(refund_id=refund.id)

        refund.refresh_from_db()

        self.assertEqual(
            refund.status,
            RefundStatus.PROCESSING,
        )

    def test_refund_can_complete(self):
        payment = self.create_paid_payment()

        refund = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("500.00"),
            currency="INR",
            calculated_amount=Decimal("500.00"),
            approved_amount=Decimal("500.00"),
            reason="Test refund",
            created_by=self.user,
        )

        start_refund(refund_id=refund.id)
        complete_refund(refund_id=refund.id)

        refund.refresh_from_db()

        self.assertEqual(
            refund.status,
            RefundStatus.COMPLETED,
        )
        self.assertIsNotNone(refund.processed_at)

    def test_refund_can_fail(self):
        payment = self.create_paid_payment()

        refund = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("500.00"),
            currency="INR",
            calculated_amount=Decimal("500.00"),
            approved_amount=Decimal("500.00"),
            reason="Test refund",
            created_by=self.user,
        )

        start_refund(refund_id=refund.id)
        fail_refund(
            refund_id=refund.id,
            failure_reason="Provider failure",
        )

        refund.refresh_from_db()

        self.assertEqual(
            refund.status,
            RefundStatus.FAILED,
        )
        self.assertEqual(
            refund.failure_reason,
            "Provider failure",
        )

    def test_full_refund_changes_payment_to_refunded(self):
        payment = self.create_paid_payment()

        refund = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("1000.00"),
            currency="INR",
            calculated_amount=Decimal("1000.00"),
            approved_amount=Decimal("1000.00"),
            reason="Full refund",
            created_by=self.user,
        )

        start_refund(refund_id=refund.id)
        complete_refund(refund_id=refund.id)

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            PaymentStatus.REFUNDED,
        )

    def test_partial_refund_keeps_payment_paid(self):
        payment = self.create_paid_payment()

        refund = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("400.00"),
            currency="INR",
            calculated_amount=Decimal("400.00"),
            approved_amount=Decimal("400.00"),
            reason="Partial refund",
            created_by=self.user,
        )

        start_refund(refund_id=refund.id)
        complete_refund(refund_id=refund.id)

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            PaymentStatus.PAID,
        )

    def test_refund_override_requires_reason_and_user(self):
        payment = self.create_paid_payment()

        with self.assertRaises(ValidationError):
            create_refund(
                booking_id=self.booking.id,
                payment_id=payment.id,
                amount=Decimal("400.00"),
                currency="INR",
                calculated_amount=Decimal("500.00"),
                approved_amount=Decimal("400.00"),
                reason="Override test",
                created_by=self.user,
            )

    def test_refund_override_can_be_created_with_reason_and_user(self):
        payment = self.create_paid_payment()

        refund = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("400.00"),
            currency="INR",
            calculated_amount=Decimal("500.00"),
            approved_amount=Decimal("400.00"),
            override_reason="Management approval",
            override_by=self.second_user,
            reason="Override test",
            created_by=self.user,
        )

        self.assertEqual(
            refund.amount,
            Decimal("400.00"),
        )
        self.assertEqual(
            refund.calculated_amount,
            Decimal("500.00"),
        )
        self.assertEqual(
            refund.approved_amount,
            Decimal("400.00"),
        )

    def test_refund_cannot_exceed_payment_amount(self):
        payment = self.create_paid_payment()

        with self.assertRaises(ValidationError):
            create_refund(
                booking_id=self.booking.id,
                payment_id=payment.id,
                amount=Decimal("1001.00"),
                currency="INR",
                calculated_amount=Decimal("1001.00"),
                approved_amount=Decimal("1001.00"),
                reason="Too large",
                created_by=self.user,
            )

    def test_multiple_refunds_cannot_exceed_payment_amount(self):
        payment = self.create_paid_payment()

        first = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("600.00"),
            currency="INR",
            calculated_amount=Decimal("600.00"),
            approved_amount=Decimal("600.00"),
            reason="First refund",
            created_by=self.user,
        )

        start_refund(refund_id=first.id)
        complete_refund(refund_id=first.id)

        second = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("400.00"),
            currency="INR",
            calculated_amount=Decimal("400.00"),
            approved_amount=Decimal("400.00"),
            reason="Second refund",
            created_by=self.user,
        )

        start_refund(refund_id=second.id)
        complete_refund(refund_id=second.id)

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            PaymentStatus.REFUNDED,
        )

    def test_refund_currency_must_match_booking_currency(self):
        payment = self.create_paid_payment()

        with self.assertRaises(ValidationError):
            create_refund(
                booking_id=self.booking.id,
                payment_id=payment.id,
                amount=Decimal("500.00"),
                currency="USD",
                calculated_amount=Decimal("500.00"),
                approved_amount=Decimal("500.00"),
                reason="Currency mismatch",
                created_by=self.user,
            )

    def test_refund_payment_must_belong_to_booking(self):
        other_booking = self._create_booking()

        payment = create_payment(
            booking_id=other_booking.id,
            amount=Decimal("1000.00"),
            currency="INR",
            method=PaymentMethod.UPI,
            provider=PaymentProvider.MANUAL,
            created_by=self.user,
        )

        mark_payment_paid(payment_id=payment.id)

        with self.assertRaises(ValidationError):
            create_refund(
                booking_id=self.booking.id,
                payment_id=payment.id,
                amount=Decimal("500.00"),
                currency="INR",
                calculated_amount=Decimal("500.00"),
                approved_amount=Decimal("500.00"),
                reason="Relationship mismatch",
                created_by=self.user,
            )

    def test_refunded_payment_cannot_receive_another_refund(self):
        payment = self.create_paid_payment()

        refund = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("1000.00"),
            currency="INR",
            calculated_amount=Decimal("1000.00"),
            approved_amount=Decimal("1000.00"),
            reason="Full refund",
            created_by=self.user,
        )

        start_refund(refund_id=refund.id)
        complete_refund(refund_id=refund.id)

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            PaymentStatus.REFUNDED,
        )

        with self.assertRaises(ValidationError):
            create_refund(
                booking_id=self.booking.id,
                payment_id=payment.id,
                amount=Decimal("1.00"),
                currency="INR",
                calculated_amount=Decimal("1.00"),
                approved_amount=Decimal("1.00"),
                reason="Invalid second refund",
                created_by=self.user,
            )


class FinancialConcurrencyTests(FinancialTestMixin, TransactionTestCase):
    reset_sequences = True

    def test_concurrent_payment_operations_cannot_overpay_booking(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrency test requires PostgreSQL.")

        import threading

        barrier = threading.Barrier(2)
        successes = []
        errors = []

        def pay():
            close_old_connections()
            try:
                payment = create_payment(
                    booking_id=self.booking.id,
                    amount=Decimal("600.00"),
                    currency="INR",
                    method=PaymentMethod.UPI,
                    provider=PaymentProvider.MANUAL,
                    created_by=self.user,
                )

                barrier.wait(timeout=5)

                mark_payment_paid(payment_id=payment.id)
                successes.append(payment.id)

            except ValidationError:
                errors.append("validation")
            finally:
                close_old_connections()

        threads = [
            threading.Thread(target=pay),
            threading.Thread(target=pay),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        self.assertFalse(
            any(thread.is_alive() for thread in threads)
        )

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(errors), 1)

        total_paid = Payment.objects.filter(
            booking=self.booking,
            status=PaymentStatus.PAID,
        ).aggregate(total=Sum("amount"))["total"]

        self.assertEqual(
            total_paid,
            Decimal("600.00"),
        )

    def test_concurrent_refunds_cannot_exceed_payment_amount(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrency test requires PostgreSQL.")

        import threading

        payment = self.create_paid_payment()

        first = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("600.00"),
            currency="INR",
            calculated_amount=Decimal("600.00"),
            approved_amount=Decimal("600.00"),
            reason="Concurrent refund 1",
            created_by=self.user,
        )

        second = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("600.00"),
            currency="INR",
            calculated_amount=Decimal("600.00"),
            approved_amount=Decimal("600.00"),
            reason="Concurrent refund 2",
            created_by=self.user,
        )

        start_refund(refund_id=first.id)
        start_refund(refund_id=second.id)

        barrier = threading.Barrier(2)
        successes = []
        errors = []

        def complete(refund_id):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                complete_refund(refund_id=refund_id)
                successes.append(refund_id)
            except ValidationError:
                errors.append("validation")
            finally:
                close_old_connections()

        threads = [
            threading.Thread(
                target=complete,
                args=(first.id,),
            ),
            threading.Thread(
                target=complete,
                args=(second.id,),
            ),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        self.assertFalse(
            any(thread.is_alive() for thread in threads)
        )

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(errors), 1)

        total_refunded = Refund.objects.filter(
            payment=payment,
            status=RefundStatus.COMPLETED,
        ).aggregate(total=Sum("amount"))["total"]

        self.assertEqual(
            total_refunded,
            Decimal("600.00"),
        )

    def test_concurrent_refund_and_payment_operations_preserve_booking_invariant(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrency test requires PostgreSQL.")

        import threading

        payment = self.create_paid_payment()

        refund = create_refund(
            booking_id=self.booking.id,
            payment_id=payment.id,
            amount=Decimal("600.00"),
            currency="INR",
            calculated_amount=Decimal("600.00"),
            approved_amount=Decimal("600.00"),
            reason="Concurrent refund",
            created_by=self.user,
        )

        start_refund(refund_id=refund.id)

        barrier = threading.Barrier(2)
        errors = []

        def complete_refund_operation():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                complete_refund(refund_id=refund.id)
            except ValidationError:
                errors.append("validation")
            finally:
                close_old_connections()

        def create_payment_operation():
            close_old_connections()
            try:
                barrier.wait(timeout=5)

                new_payment = create_payment(
                    booking_id=self.booking.id,
                    amount=Decimal("600.00"),
                    currency="INR",
                    method=PaymentMethod.CARD,
                    provider=PaymentProvider.MANUAL,
                    created_by=self.user,
                )

                mark_payment_paid(
                    payment_id=new_payment.id,
                )

            except ValidationError:
                errors.append("validation")
            finally:
                close_old_connections()

        threads = [
            threading.Thread(
                target=complete_refund_operation,
            ),
            threading.Thread(
                target=create_payment_operation,
            ),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        self.assertFalse(
            any(thread.is_alive() for thread in threads)
        )

        settled_total = Payment.objects.filter(
            booking=self.booking,
            status__in=[
                PaymentStatus.PAID,
                PaymentStatus.REFUNDED,
            ],
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        completed_refunds = Refund.objects.filter(
            booking=self.booking,
            status=RefundStatus.COMPLETED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        self.assertLessEqual(
            settled_total,
            self.booking.final_amount,
        )

        self.assertLessEqual(completed_refunds, settled_total)