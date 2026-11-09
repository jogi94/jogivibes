from django.conf import settings
from django.core.exceptions import ValidationError
from apps.core.models import TimeStampedModel
from .utils import normalize_phone_number
from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from apps.core.models import TrackedModel
from apps.leads.enums import (
    LeadInterestLevel, LeadStatus, ContactResult, InteractionChannel,
    InteractionType, AcquisitionSource, CampaignStatus)


# Create your models here.


class Contact(TimeStampedModel):
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=16, unique=True)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"

    def save(self, *args, **kwargs):
        self.phone_number = normalize_phone_number(self.phone_number)
        super().save(*args, **kwargs)


class Lead(TrackedModel):
    contact = models.ForeignKey("leads.Contact", on_delete=models.PROTECT, related_name="leads")
    trip = models.ForeignKey("trips.Trip", on_delete=models.PROTECT, related_name="leads")
    campaign = models.ForeignKey("leads.Campaign", on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="leads")
    source = models.CharField(max_length=20, choices=AcquisitionSource.choices, default=AcquisitionSource.OTHER,
                              db_index=True)
    group_size = models.PositiveIntegerField(default=1)
    preferred_departure_month = models.DateField(null=True, blank=True,
                                                 help_text="Store the first day of the preferred month.")
    preferred_schedule = models.ForeignKey("bookings.TripSchedule", on_delete=models.SET_NULL, null=True,
                                           blank=True, related_name="preferred_leads")
    preferred_departure_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=LeadStatus.choices, default=LeadStatus.NEW, db_index=True)
    interest_level = models.CharField(
        max_length=10,
        choices=LeadInterestLevel.choices,
        default=LeadInterestLevel.WARM,
        db_index=True,
    )
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="assigned_leads")
    next_follow_up_date = models.DateField(null=True, blank=True, db_index=True)
    next_follow_up_action = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created"]
        indexes = [
            models.Index(fields=["assigned_to", "status"], name="lead_assignee_status_idx"),
            models.Index(fields=["trip", "status"], name="lead_trip_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(group_size__gte=1), name="lead_group_size_gte_1")
        ]

    def __str__(self):
        return f"{self.contact.full_name} - {self.trip.name}"


class Campaign(TrackedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    acquisition_source = models.CharField(max_length=20, choices=AcquisitionSource.choices)
    description = models.TextField(blank=True)
    trips = models.ManyToManyField("trips.Trip", related_name="campaigns", blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT,
                              db_index=True)

    class Meta:
        ordering = ["-start_date", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="campaign_end_after_start",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class LeadInteraction(models.Model):
    lead = models.ForeignKey("leads.Lead", on_delete=models.PROTECT, related_name="interactions")
    interaction_date = models.DateTimeField()
    channel = models.CharField(max_length=20, choices=InteractionChannel.choices)
    interaction_type = models.CharField(max_length=30, choices=InteractionType.choices)
    contact_result = models.CharField(max_length=25, choices=ContactResult.choices)
    summary = models.TextField()
    objection = models.TextField(blank=True)
    interest_after_interaction = models.CharField(max_length=10, choices=LeadInterestLevel.choices, blank=True)
    next_action = models.CharField(max_length=255, blank=True)
    next_follow_up_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lead_interactions_created")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-interaction_date"]
        indexes = [
            models.Index(
                fields=["lead", "-interaction_date"],
                name="lead_interaction_date_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError(
                "Lead interactions are historical records and cannot be edited."
            )

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Lead interactions are historical records and cannot be deleted."
        )

    def __str__(self):
        return f"{self.lead} - {self.interaction_type}"


class LeadStatusHistory(models.Model):
    lead = models.ForeignKey("leads.Lead", on_delete=models.PROTECT, related_name="status_history")
    previous_status = models.CharField(max_length=20, choices=LeadStatus.choices)
    new_status = models.CharField(max_length=20, choices=LeadStatus.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="lead_status_changes")
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["lead", "-changed_at"], name="lead_status_history_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Lead status history records cannot be edited.")

        if self.previous_status == self.new_status:
            raise ValidationError("Previous and new status cannot be the same.")

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Lead status history records cannot be deleted.")

    def __str__(self):
        return f"{self.lead}: {self.previous_status} → {self.new_status}"