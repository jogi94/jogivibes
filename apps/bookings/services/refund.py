from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.bookings.enums import PaymentStatus, RefundStatus
from apps.bookings.models import Booking, Payment, Refund


SETTLED_PAYMENT_STATUSES = (
    PaymentStatus.PAID,
    PaymentStatus.REFUNDED,
)


def _lock_booking(booking_id):
    return (
        Booking.objects
        .select_for_update()
        .get(pk=booking_id)
    )


def _get_refund(refund_id):
    return Refund.objects.get(pk=refund_id)


def _lock_payment(payment_id):
    return (
        Payment.objects
        .select_for_update()
        .get(pk=payment_id)
    )


def _lock_refund(refund_id):
    return (
        Refund.objects
        .select_for_update()
        .get(pk=refund_id)
    )


def _completed_refund_total_for_booking(booking_id):
    total = (
        Refund.objects
        .filter(
            booking_id=booking_id,
            status=RefundStatus.COMPLETED,
        )
        .aggregate(total=Sum("amount"))
        ["total"]
    )

    return total or Decimal("0.00")


def _completed_refund_total_for_payment(payment_id):
    total = (
        Refund.objects
        .filter(
            payment_id=payment_id,
            status=RefundStatus.COMPLETED,
        )
        .aggregate(total=Sum("amount"))
        ["total"]
    )

    return total or Decimal("0.00")


def _historically_settled_payment_total(booking_id):
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


def create_refund(
    *,
    booking_id,
    payment_id,
    amount,
    calculated_amount,
    approved_amount,
    currency,
    reason,
    created_by,
    cancellation_id=None,
    override_reason=None,
    override_by=None,
    provider="MANUAL",
    provider_reference=None,
):
    """
    Create a PENDING refund.

    Lock order:
        Booking -> Payment

    PENDING refunds do not consume the completed-refund aggregate.
    The authoritative aggregate check happens again when the refund
    transitions to COMPLETED.
    """
    amount = Decimal(amount)
    calculated_amount = Decimal(calculated_amount)
    approved_amount = Decimal(approved_amount)
    currency = (currency or "").strip().upper()

    if amount <= Decimal("0.00"):
        raise ValidationError(
            "Refund amount must be greater than zero."
        )

    if len(currency) != 3 or not currency.isalpha():
        raise ValidationError(
            "Currency must be a 3-letter ISO-4217 code."
        )

    if approved_amount < Decimal("0.00"):
        raise ValidationError(
            "Approved refund amount cannot be negative."
        )

    if calculated_amount < Decimal("0.00"):
        raise ValidationError(
            "Calculated refund amount cannot be negative."
        )

    if approved_amount > calculated_amount:
        raise ValidationError(
            "Approved refund cannot exceed calculated refund."
        )

    if amount != approved_amount:
        raise ValidationError(
            "Refund amount must equal approved amount."
        )

    if approved_amount != calculated_amount:
        if not override_reason or not override_by:
            raise ValidationError(
                "Refund override requires both reason and user."
            )

    with transaction.atomic():

        # 1. Lock Booking FIRST.
        booking = _lock_booking(booking_id)

        # 2. Lock Payment SECOND.
        payment = _lock_payment(payment_id)

        if payment.booking_id != booking.id:
            raise ValidationError(
                "Refund payment does not belong to the booking."
            )

        if payment.status not in SETTLED_PAYMENT_STATUSES:
            raise ValidationError(
                "Refund can only be created against a settled payment."
            )

        if currency != booking.price_currency.upper():
            raise ValidationError(
                "Refund currency must match the Booking currency."
            )

        if payment.currency.upper() != booking.price_currency.upper():
            raise ValidationError(
                "Payment currency must match the Booking currency."
            )

        completed_for_payment = (
            _completed_refund_total_for_payment(payment.id)
        )

        if completed_for_payment + amount > payment.amount:
            raise ValidationError(
                "Refund would exceed the payment amount."
            )

        completed_for_booking = (
            _completed_refund_total_for_booking(booking.id)
        )

        historically_settled = (
            _historically_settled_payment_total(booking.id)
        )

        if completed_for_booking + amount > historically_settled:
            raise ValidationError(
                "Refund would exceed historically settled payments."
            )

        if cancellation_id is not None:
            from apps.bookings.models import Cancellation

            cancellation = (
                Cancellation.objects
                .select_for_update()
                .get(pk=cancellation_id)
            )

            if cancellation.booking_id != booking.id:
                raise ValidationError(
                    "Refund cancellation does not belong to the booking."
                )

        return Refund.objects.create(
            booking=booking,
            payment=payment,
            cancellation_id=cancellation_id,
            amount=amount,
            currency=currency,
            status=RefundStatus.PENDING,
            calculated_amount=calculated_amount,
            approved_amount=approved_amount,
            override_reason=override_reason,
            override_by=override_by,
            provider=provider,
            provider_reference=provider_reference,
            reason=reason,
            created_by=created_by,
        )


def start_refund(
    *,
    refund_id,
):
    """
    PENDING -> PROCESSING

    Lock order:
        Booking -> Payment -> Refund
    """
    with transaction.atomic():

        # Fetch without lock so Booking can be locked first.
        refund = _get_refund(refund_id)

        # 1. Booking FIRST.
        booking = _lock_booking(refund.booking_id)

        # 2. Payment SECOND.
        payment = _lock_payment(refund.payment_id)

        # 3. Refund THIRD.
        refund = _lock_refund(refund.id)

        if payment.booking_id != booking.id:
            raise ValidationError(
                "Refund payment does not belong to the booking."
            )

        if refund.status != RefundStatus.PENDING:
            raise ValidationError(
                "Only PENDING refunds can begin processing."
            )

        refund.status = RefundStatus.PROCESSING

        refund.save(
            update_fields=[
                "status",
                "modified",
            ]
        )

        return refund


def complete_refund(
    *,
    refund_id,
):
    """
    PROCESSING -> COMPLETED

    If the entire Payment amount has now been refunded:

        Payment PAID -> REFUNDED

    Otherwise:

        Payment remains PAID
    """
    with transaction.atomic():

        # Fetch without lock.
        refund = _get_refund(refund_id)

        # 1. Booking FIRST.
        booking = _lock_booking(refund.booking_id)

        # 2. Payment SECOND.
        payment = _lock_payment(refund.payment_id)

        # 3. Refund THIRD.
        refund = _lock_refund(refund.id)

        if payment.booking_id != booking.id:
            raise ValidationError(
                "Refund payment does not belong to the booking."
            )

        if refund.status != RefundStatus.PROCESSING:
            raise ValidationError(
                "Only PROCESSING refunds can be completed."
            )

        if payment.status != PaymentStatus.PAID:
            raise ValidationError(
                "Only PAID payments can be refunded."
            )

        if refund.currency.upper() != booking.price_currency.upper():
            raise ValidationError(
                "Refund currency must match the Booking currency."
            )

        if payment.currency.upper() != booking.price_currency.upper():
            raise ValidationError(
                "Payment currency must match the Booking currency."
            )

        completed_before = (
            _completed_refund_total_for_payment(payment.id)
        )

        if completed_before + refund.amount > payment.amount:
            raise ValidationError(
                "Completed refunds would exceed the payment amount."
            )

        completed_for_booking = (
            _completed_refund_total_for_booking(booking.id)
        )

        historically_settled = (
            _historically_settled_payment_total(booking.id)
        )

        if completed_for_booking + refund.amount > historically_settled:
            raise ValidationError(
                "Completed refunds would exceed historically "
                "settled payments."
            )

        refund.status = RefundStatus.COMPLETED
        refund.processed_at = timezone.now()

        refund.save(
            update_fields=[
                "status",
                "processed_at",
                "modified",
            ]
        )

        completed_total = (
            completed_before + refund.amount
        )

        if completed_total == payment.amount:
            payment.status = PaymentStatus.REFUNDED

            payment.save(
                update_fields=[
                    "status",
                    "modified",
                ]
            )

        return refund


def fail_refund(
    *,
    refund_id,
    failure_reason,
):
    """
    PROCESSING -> FAILED

    Lock order:
        Booking -> Payment -> Refund
    """
    with transaction.atomic():

        refund = _get_refund(refund_id)

        # 1. Booking FIRST.
        booking = _lock_booking(refund.booking_id)

        # 2. Payment SECOND.
        payment = _lock_payment(refund.payment_id)

        # 3. Refund THIRD.
        refund = _lock_refund(refund.id)

        if payment.booking_id != booking.id:
            raise ValidationError(
                "Refund payment does not belong to the booking."
            )

        if refund.status != RefundStatus.PROCESSING:
            raise ValidationError(
                "Only PROCESSING refunds can fail."
            )

        refund.status = RefundStatus.FAILED
        refund.failure_reason = failure_reason

        refund.save(
            update_fields=[
                "status",
                "failure_reason",
                "modified",
            ]
        )

        return refund