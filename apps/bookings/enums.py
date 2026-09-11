from django.db import models


class TripScheduleStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class BookingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"


class BookingHoldStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CONVERTED = "converted", "Converted"
    EXPIRED = "expired", "Expired"
    RELEASED = "released", "Released"


class WaitlistEntryStatus(models.TextChoices):
    WAITING = "waiting", "Waiting"
    CANCELLED = "cancelled", "Cancelled"


class WaitlistOfferStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    EXPIRED = "expired", "Expired"
    DECLINED = "declined", "Declined"
