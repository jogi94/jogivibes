from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.bookings.enums import PaymentStatus
from apps.bookings.models import Booking, Payment


SETTLED_PAYMENT_STATUSES = (
    PaymentStatus.PAID,
    PaymentStatus.REFUNDED,
)


def _normalise_currency(currency):
    currency = (currency or "").strip().upper()

    if len(currency) != 3 or not currency.isalpha():
        raise ValidationError(
            "Currency must be a 3-letter ISO-4217 code."
        )

    return currency


def _lock_booking(booking_id):
    return (
        Booking.objects
        .select_for_update()
        .get(pk=booking_id)
    )


def _get_payment(payment_id):
    """
    Fetch Payment without locking it.

    The service must lock Booking first and Payment second.
    """
    return Payment.objects.get(pk=payment_id)


def _get_settled_payment_total(booking_id):
    """
    Historically settled payments.

    REFUNDED payments remain part of historical settlement.
    """
    total = (
        Payment.objects
        .filter(
            booking_id=booking_id,
            status__in=SETTLED_PAYMENT_STATUSES,
        )
        .aggregate(total=Sum("amount"))
        ["total"]
    )

    return total or Decimal("0.00")


def get_booking_payment_position(booking_id):
    """
    Derived Booking-level payment position.

    Returns:
        UNPAID
        PARTIAL
        PAID
        FULLY_REFUNDED
    """
    booking = Booking.objects.get(pk=booking_id)

    settled_total = _get_settled_payment_total(booking.id)

    refunded_total = (
        booking.refunds
        .filter(status="COMPLETED")
        .aggregate(total=Sum("amount"))
        ["total"]
        or Decimal("0.00")
    )

    if settled_total == Decimal("0.00"):
        return "UNPAID"

    if refunded_total >= booking.final_amount:
        return "FULLY_REFUNDED"

    if settled_total < booking.final_amount:
        return "PARTIAL"

    return "PAID"


def create_payment(
    *,
    booking_id,
    amount,
    currency,
    method,
    provider,
    created_by,
    provider_order_id=None,
    provider_transaction_id=None,
    provider_reference=None,
    notes=None,
):
    """
    Create a PENDING payment.

    PENDING payments do not count toward settlement.
    """
    amount = Decimal(amount)
    currency = _normalise_currency(currency)

    if amount <= Decimal("0.00"):
        raise ValidationError(
            "Payment amount must be greater than zero."
        )

    with transaction.atomic():
        booking = _lock_booking(booking_id)

        if currency != booking.price_currency.upper():
            raise ValidationError(
                "Payment currency must match the Booking currency."
            )

        validate_provider_transaction_identity(
            provider=provider,
            provider_transaction_id=provider_transaction_id,
        )

        return Payment.objects.create(
            booking=booking,
            amount=amount,
            currency=currency,
            method=method,
            provider=provider,
            provider_order_id=provider_order_id,
            provider_transaction_id=provider_transaction_id,
            provider_reference=provider_reference,
            notes=notes,
            created_by=created_by,
            status=PaymentStatus.PENDING,
        )


def validate_provider_transaction_identity(
    *,
    provider,
    provider_transaction_id,
    payment_id=None,
):
    """
    Validate provider + transaction identity.

    Database uniqueness remains the final protection.
    """
    if not provider_transaction_id:
        return

    queryset = Payment.objects.filter(
        provider=provider,
        provider_transaction_id=provider_transaction_id,
    )

    if payment_id is not None:
        queryset = queryset.exclude(pk=payment_id)

    if queryset.exists():
        raise ValidationError(
            "This provider transaction is already attached "
            "to another payment."
        )


def mark_payment_paid(
    *,
    payment_id,
    processed_by=None,
    paid_at=None,
):
    """
    PENDING -> PAID

    Lock order:
        Booking -> Payment
    """
    with transaction.atomic():

        # 1. Fetch Payment without a lock.
        payment = _get_payment(payment_id)

        # 2. Lock Booking FIRST.
        booking = _lock_booking(payment.booking_id)

        # 3. Lock Payment SECOND.
        payment = (
            Payment.objects
            .select_for_update()
            .get(pk=payment_id)
        )

        if payment.status != PaymentStatus.PENDING:
            raise ValidationError(
                "Only PENDING payments can be marked as PAID."
            )

        currency = _normalise_currency(payment.currency)

        if currency != booking.price_currency.upper():
            raise ValidationError(
                "Payment currency must match the Booking currency."
            )

        validate_provider_transaction_identity(
            provider=payment.provider,
            provider_transaction_id=payment.provider_transaction_id,
            payment_id=payment.id,
        )

        settled_total = _get_settled_payment_total(booking.id)

        if settled_total + payment.amount > booking.final_amount:
            raise ValidationError(
                "Payment would exceed the Booking final amount."
            )

        payment.status = PaymentStatus.PAID
        payment.paid_at = paid_at or timezone.now()

        payment.save(
            update_fields=[
                "status",
                "paid_at",
                "modified",
            ]
        )

        return payment


def mark_payment_failed(
    *,
    payment_id,
    failure_reason,
):
    """
    PENDING -> FAILED

    Lock order:
        Booking -> Payment
    """
    with transaction.atomic():

        payment = _get_payment(payment_id)

        booking = _lock_booking(payment.booking_id)

        payment = (
            Payment.objects
            .select_for_update()
            .get(pk=payment_id)
        )

        if payment.status != PaymentStatus.PENDING:
            raise ValidationError(
                "Only PENDING payments can be marked as FAILED."
            )

        payment.status = PaymentStatus.FAILED
        payment.failure_reason = failure_reason

        payment.save(
            update_fields=[
                "status",
                "failure_reason",
                "modified",
            ]
        )

        return payment


def cancel_payment(
    *,
    payment_id,
    reason=None,
):
    """
    PENDING -> CANCELLED

    Lock order:
        Booking -> Payment
    """
    with transaction.atomic():

        payment = _get_payment(payment_id)

        booking = _lock_booking(payment.booking_id)

        payment = (
            Payment.objects
            .select_for_update()
            .get(pk=payment_id)
        )

        if payment.status != PaymentStatus.PENDING:
            raise ValidationError(
                "Only PENDING payments can be cancelled."
            )

        payment.status = PaymentStatus.CANCELLED

        if reason:
            payment.failure_reason = reason

        payment.save(
            update_fields=[
                "status",
                "failure_reason",
                "modified",
            ]
        )

        return payment