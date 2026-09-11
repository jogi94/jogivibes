from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField
from django.contrib.postgres.operations import BtreeGistExtension
from django.contrib.postgres.fields.ranges import RangeOperators
from django.db import models
from django.db.models import F, Func, Q

from apps.core.models import TrackedModel
from apps.trips.enums import PricingType
from apps.trips.models.schedule_package import SchedulePackage
from django.core.exceptions import ValidationError


class Pricing(TrackedModel):
    schedule_package = models.ForeignKey(SchedulePackage, on_delete=models.PROTECT, related_name="pricings")
    pricing_type = models.CharField(max_length=20, choices=PricingType.choices, default=PricingType.STANDARD,
                                    db_index=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="custom_pricings")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)
    # effective_period = DateTimeRangeField(editable=False)
    effective_period = models.GeneratedField(
        expression=Func(
            F("effective_from"),
            F("effective_until"),
            function="TSTZRANGE",
        ),
        output_field=DateTimeRangeField(),
        db_persist=True,
        editable=False,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    retired_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["effective_from"]
        constraints = [
            models.CheckConstraint(
                condition=Q(effective_until__isnull=True)
                | Q(effective_until__gt=F("effective_from")),
                name="pricing_effective_until_after_from",
            ),
            models.CheckConstraint(
                condition=(Q(pricing_type=PricingType.STANDARD) & Q(customer__isnull=True))
                | (Q(pricing_type=PricingType.CUSTOM) & Q(customer__isnull=False)),
                name="pricing_customer_matches_type",
            ),
            ExclusionConstraint(
                name="pricing_standard_no_overlap",
                expressions=[
                    ("schedule_package", RangeOperators.EQUAL),
                    ("effective_period", RangeOperators.OVERLAPS),
                ],
                condition=Q(pricing_type=PricingType.STANDARD, is_active=True),
            ),
            ExclusionConstraint(
                name="pricing_custom_no_overlap",
                expressions=[
                    ("schedule_package", RangeOperators.EQUAL),
                    ("customer", RangeOperators.EQUAL),
                    ("effective_period", RangeOperators.OVERLAPS),
                ],
                condition=Q(pricing_type=PricingType.CUSTOM, is_active=True),
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "schedule_package",
                    "pricing_type",
                    "is_active",
                ],
                name="pricing_sched_type_active_idx",
            ),
            models.Index(
                fields=[
                    "schedule_package",
                    "customer",
                    "effective_from",
                ],
                name="pricing_schedule_customer_idx",
            ),
        ]

    def __str__(self):
        return f"{self.schedule_package} - " f"{self.amount} {self.currency}"

    def clean(self):
        super().clean()

        if self.effective_until and self.effective_until <= self.effective_from:
            raise ValidationError("effective_until must be after effective_from.")

        if self.pricing_type == PricingType.STANDARD and self.customer_id:
            raise ValidationError("Standard pricing cannot have a customer.")

        if self.pricing_type == PricingType.CUSTOM and not self.customer_id:
            raise ValidationError("Custom pricing requires a customer.")