from django.db import models


class LeadStatus(models.TextChoices):
    NEW = "NEW", "New"
    CONTACTED = "CONTACTED", "Contacted"
    QUALIFIED = "QUALIFIED", "Qualified"
    FOLLOW_UP = "FOLLOW_UP", "Follow Up"
    CONVERTED = "CONVERTED", "Converted"
    LOST = "LOST", "Lost"
    ON_HOLD = "ON_HOLD", "On Hold"


class LeadInterestLevel(models.TextChoices):
    HOT = "HOT", "Hot"
    WARM = "WARM", "Warm"
    COLD = "COLD", "Cold"


class InteractionChannel(models.TextChoices):
    PHONE = "PHONE", "Phone"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    INSTAGRAM = "INSTAGRAM", "Instagram"
    EMAIL = "EMAIL", "Email"
    WEBSITE = "WEBSITE", "Website"
    IN_PERSON = "IN_PERSON", "In Person"
    OTHER = "OTHER", "Other"


class InteractionType(models.TextChoices):
    FIRST_CONTACT = "FIRST_CONTACT", "First Contact"
    FOLLOW_UP = "FOLLOW_UP", "Follow Up"
    INQUIRY = "INQUIRY", "Inquiry"
    SCHEDULE_CHANGE_REQUEST = "SCHEDULE_CHANGE_REQUEST", "Schedule Change Request"
    BOOKING_DISCUSSION = "BOOKING_DISCUSSION", "Booking Discussion"
    OTHER = "OTHER", "Other"


class ContactResult(models.TextChoices):
    CONNECTED = "CONNECTED", "Connected"
    NO_ANSWER = "NO_ANSWER", "No Answer"
    BUSY = "BUSY", "Busy"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED", "Callback Requested"
    MESSAGE_SENT = "MESSAGE_SENT", "Message Sent"
    NOT_INTERESTED = "NOT_INTERESTED", "Not Interested"
    OTHER = "OTHER", "Other"


class CampaignStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    ARCHIVED = "ARCHIVED", "Archived"


class AcquisitionSource(models.TextChoices):
    INSTAGRAM = "INSTAGRAM", "Instagram"
    FACEBOOK = "FACEBOOK", "Facebook"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    WEBSITE = "WEBSITE", "Website"
    GOOGLE = "GOOGLE", "Google"
    REFERRAL = "REFERRAL", "Referral"
    DIRECT = "DIRECT", "Direct"
    OTHER = "OTHER", "Other"