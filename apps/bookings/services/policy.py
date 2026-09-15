from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.bookings.models import (
    CancellationPolicy,
    CancellationPolicyRule,
    TripSchedule,
)


def calculate_days_before_departure(
    trip_schedule: TripSchedule,
    cancellation_at=None,
) -> int:
    """
    Calculate calendar days before departure.

    MVP semantics:
    - TripSchedule.start_date is the departure date.
    - Only calendar dates are considered.
    - Cancellation on or after departure gives 0 days.
    """
    if cancellation_at is None:
        cancellation_at = timezone.now()

    cancellation_date = timezone.localtime(cancellation_at).date()

    days = (trip_schedule.start_date - cancellation_date).days

    return max(days, 0)


def validate_policy_usable(policy: CancellationPolicy) -> None:
    """
    An active cancellation policy must contain a 0-day rule.
    """
    if not policy.is_active:
        raise ValidationError("Cancellation policy is not active.")

    if not policy.rules.filter(
        minimum_days_before_departure=0
    ).exists():
        raise ValidationError(
            "Active cancellation policy must contain a 0-day rule."
        )


def get_active_policy_for_schedule(
    trip_schedule: TripSchedule,
) -> CancellationPolicy:
    """
    Return the active cancellation policy for a schedule.
    """
    try:
        policy = CancellationPolicy.objects.get(
            trip_schedule=trip_schedule,
            is_active=True,
        )
    except CancellationPolicy.DoesNotExist:
        raise ValidationError(
            "No active cancellation policy exists for this trip schedule."
        )

    validate_policy_usable(policy)

    return policy


def select_cancellation_policy_rule(
    trip_schedule: TripSchedule,
    cancellation_at=None,
):
    """
    Select the highest applicable cancellation threshold.

    Example:

        30 -> 90%
        15 -> 75%
         7 -> 50%
         0 ->  0%

    At 20 days before departure, the 15-day rule applies.
    At exactly 15 days, the 15-day rule applies.
    """
    policy = get_active_policy_for_schedule(trip_schedule)

    days_before_departure = calculate_days_before_departure(
        trip_schedule=trip_schedule,
        cancellation_at=cancellation_at,
    )

    rule = (
        policy.rules
        .filter(
            minimum_days_before_departure__lte=days_before_departure,
        )
        .order_by(
            "-minimum_days_before_departure",
            "-id",
        )
        .first()
    )

    if rule is None:
        raise ValidationError(
            "No applicable cancellation policy rule exists."
        )

    return policy, rule, days_before_departure