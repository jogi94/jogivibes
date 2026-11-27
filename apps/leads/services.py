from django.core.exceptions import ValidationError
from django.db import transaction
from apps.leads.enums import LeadStatus, CampaignStatus, AcquisitionSource, LeadInterestLevel
from apps.leads.models import Lead, LeadStatusHistory, LeadInteraction, Contact, Campaign, LeadPhoneOTP
from apps.leads.permissions import is_crm_admin, get_accessible_lead
from django.core.exceptions import PermissionDenied
from django.utils.text import slugify
from apps.leads.utils import normalize_phone_number
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured
from apps.leads.twilio_verify import send_sms_verification, check_sms_verification
from django.db.models import F


@transaction.atomic
def change_lead_status(*, user, lead_id, new_status, changed_by=None, reason="",):
    """
    Change a lead's status and record its history atomically.
    """
    try:
        new_status = LeadStatus(new_status)
    except ValueError:
        raise ValidationError("Invalid lead status.")
    lead = get_accessible_lead(user, lead_id)
    lead = Lead.objects.select_for_update().get(pk=lead.pk)
    previous_status = lead.status
    if previous_status == new_status:
        raise ValidationError("Lead already has this status.")

    LeadStatusHistory.objects.create(
        lead=lead,
        previous_status=previous_status,
        new_status=new_status,
        changed_by=user,
        reason=reason,
    )
    lead.status = new_status
    lead.save(update_fields=["status", "modified"])
    return lead


@transaction.atomic
def record_lead_interaction(*, user, lead_id, interaction_date, channel,
                            interaction_type, contact_result, summary,
                            created_by=None, objection="", interest_after_interaction="",
                            next_action="", next_follow_up_date=None):
    """
    Record a customer interaction and update the lead's
    next follow-up information atomically.
    """
    lead = get_accessible_lead(user, lead_id)
    lead = Lead.objects.select_for_update().get(pk=lead.pk)
    interaction = LeadInteraction.objects.create(
        lead=lead,
        interaction_date=interaction_date,
        channel=channel,
        interaction_type=interaction_type,
        contact_result=contact_result,
        summary=summary,
        objection=objection,
        interest_after_interaction=interest_after_interaction,
        next_action=next_action,
        next_follow_up_date=next_follow_up_date,
        created_by=user,
    )
    lead.next_follow_up_action = next_action
    lead.next_follow_up_date = next_follow_up_date

    if interest_after_interaction:
        lead.interest_level = interest_after_interaction

    lead.save(
        update_fields=[
            "next_follow_up_action",
            "next_follow_up_date",
            "interest_level",
            "modified",
        ]
    )
    return interaction

@transaction.atomic
def create_lead(
    *,
    user,
    contact,
    trip,
    group_size=1,
    campaign=None,
    preferred_departure_month=None,
    preferred_schedule=None,
    preferred_departure_date=None,
    interest_level="WARM",
    assigned_to=None,
    notes="",
):
    if not user.is_authenticated:
        raise PermissionDenied("Authentication is required.")

    crm_admin = is_crm_admin(user)

    # Only CRM Admin can set departure preferences.
    if not crm_admin and any([
        preferred_departure_month,
        preferred_schedule,
        preferred_departure_date,
    ]):
        raise PermissionDenied(
            "Only CRM Admin can set departure preferences."
        )

    # Staff are automatically assigned their own leads.
    if crm_admin:
        assignee = assigned_to
    else:
        assignee = user

    lead = Lead.objects.create(
        contact=contact,
        trip=trip,
        campaign=campaign,
        group_size=group_size,
        preferred_departure_month=preferred_departure_month,
        preferred_schedule=preferred_schedule,
        preferred_departure_date=preferred_departure_date,
        interest_level=interest_level,
        assigned_to=assignee,
        notes=notes,
        created_by=user,
        modified_by=user,
    )

    return lead


@transaction.atomic
def update_lead(*, user, lead_id, assigned_to=None, preferred_departure_month=None,
                preferred_schedule=None, preferred_departure_date=None, update_assignment=False,
                update_departure_preferences=False):
    if not user.is_authenticated:
        raise PermissionDenied("Authentication is required.")

    if not is_crm_admin(user):
        raise PermissionDenied(
            "Only CRM Admin can update these lead fields."
        )

    if not update_assignment and not update_departure_preferences:
        raise ValidationError("No lead fields selected for update.")

    lead = Lead.objects.select_for_update().get(pk=lead_id)
    if update_assignment:
        if assigned_to is not None:
            if not assigned_to.is_active or not getattr(
                assigned_to, "is_staff", False
            ):
                raise ValidationError(
                    "A lead can only be assigned to an active staff member."
                )

        lead.assigned_to = assigned_to

    if update_departure_preferences:
        if (
            preferred_schedule is not None
            and preferred_schedule.trip_id != lead.trip_id
        ):
            raise ValidationError(
                "Preferred schedule must belong to the lead's trip."
            )

        lead.preferred_departure_month = preferred_departure_month
        lead.preferred_schedule = preferred_schedule
        lead.preferred_departure_date = preferred_departure_date

    lead.modified_by = user

    update_fields = ["modified_by", "modified"]

    if update_assignment:
        update_fields.append("assigned_to")

    if update_departure_preferences:
        update_fields.extend([
            "preferred_departure_month",
            "preferred_schedule",
            "preferred_departure_date",
        ])

    lead.save(update_fields=update_fields)

    return lead


@transaction.atomic
def create_campaign(*, user, name, acquisition_source, start_date, end_date, trips=None,
                    description="", status=CampaignStatus.DRAFT):
    if not user.is_authenticated or not is_crm_admin(user):
        raise PermissionDenied(
            "Only CRM Admin can create campaigns."
        )

    if end_date < start_date:
        raise ValidationError(
            "Campaign end date cannot be before start date."
        )

    base_slug = slugify(name)

    if not base_slug:
        raise ValidationError("Campaign name must produce a valid slug.")

    slug = base_slug
    counter = 1
    while Campaign.objects.filter(slug=slug).exists():
        counter += 1
        slug = f"{base_slug}-{counter}"

    campaign = Campaign.objects.create(
        name=name,
        slug=slug,
        acquisition_source=acquisition_source,
        start_date=start_date,
        end_date=end_date,
        description=description,
        status=status,
        created_by=user,
        modified_by=user,
    )

    if trips:
        campaign.trips.set(trips)

    return campaign


@transaction.atomic
def update_campaign(
    *,
    user,
    campaign_id,
    name=None,
    acquisition_source=None,
    start_date=None,
    end_date=None,
    trips=None,
    description=None,
    status=None,
):
    if not user.is_authenticated or not is_crm_admin(user):
        raise PermissionDenied(
            "Only CRM Admin can update campaigns."
        )

    campaign = Campaign.objects.select_for_update().get(
        pk=campaign_id
    )

    if name is not None:
        campaign.name = name

    if acquisition_source is not None:
        campaign.acquisition_source = acquisition_source

    if start_date is not None:
        campaign.start_date = start_date

    if end_date is not None:
        campaign.end_date = end_date

    if campaign.end_date < campaign.start_date:
        raise ValidationError(
            "Campaign end date cannot be before start date."
        )

    if description is not None:
        campaign.description = description

    if status is not None:
        campaign.status = status

    campaign.modified_by = user

    campaign.save()

    if trips is not None:
        campaign.trips.set(trips)

    return campaign


@transaction.atomic
def archive_campaign(*, user, campaign_id):
    if not user.is_authenticated or not is_crm_admin(user):
        raise PermissionDenied(
            "Only CRM Admin can archive campaigns."
        )

    campaign = Campaign.objects.select_for_update().get(pk=campaign_id)
    campaign.status = CampaignStatus.ARCHIVED
    campaign.modified_by = user
    campaign.save(update_fields=["status", "modified_by", "modified"])
    return campaign


def send_lead_phone_otp(*, user, lead, phone_number):
    if not user.is_authenticated or not user.is_staff:
        raise PermissionDenied("Only logged-in staff can send enquiry OTPs.")
    if lead.created_by_id != user.pk:
        raise PermissionDenied("Only the staff member who entered this enquiry can verify it.")

    phone_number = normalize_phone_number(phone_number)
    now = timezone.now()
    recent_count = LeadPhoneOTP.objects.filter(
        created_by=user,
        phone_number=phone_number,
        created__gte=now - timedelta(hours=1),
    ).count()
    if recent_count >= 5:
        raise ValidationError("Too many codes requested for this number. Try again later.")

    try:
        response = send_sms_verification(phone_number=phone_number)
    except ImproperlyConfigured:
        raise
    except Exception as error:
        raise ValidationError("Twilio could not send the verification code.") from error
    if response.get("status") != "pending" or not response.get("sid"):
        raise ValidationError("Twilio did not start phone verification.")

    LeadPhoneOTP.objects.filter(
        created_by=user,
        lead=lead,
        phone_number=phone_number,
        consumed_at__isnull=True,
    ).update(consumed_at=now)
    return LeadPhoneOTP.objects.create(
        phone_number=phone_number,
        verification_sid=response["sid"],
        created_by=user,
        lead=lead,
        expires_at=now + timedelta(minutes=10),
    )


def verify_lead_phone_otp(*, user, lead, phone_number, code):
    if not user.is_authenticated or not user.is_staff:
        return False
    if lead.created_by_id != user.pk:
        raise PermissionDenied("Only the staff member who entered this enquiry can verify it.")
    phone_number = normalize_phone_number(phone_number)
    now = timezone.now()
    challenge = LeadPhoneOTP.objects.filter(
        created_by=user,
        lead=lead,
        phone_number=phone_number,
        consumed_at__isnull=True,
        expires_at__gt=now,
    ).order_by("-created").first()
    if challenge is None:
        return False
    if challenge.attempt_count >= 5:
        LeadPhoneOTP.objects.filter(pk=challenge.pk, consumed_at__isnull=True).update(consumed_at=now)
        return False
    if not code:
        return False

    try:
        valid = check_sms_verification(
            verification_sid=challenge.verification_sid,
            code=code,
        )
    except Exception as error:
        raise ValidationError("Twilio could not verify the code. Please try again.") from error

    updates = {"attempt_count": F("attempt_count") + 1}
    if valid or challenge.attempt_count + 1 >= 5:
        updates["consumed_at"] = now
    changed = LeadPhoneOTP.objects.filter(
        pk=challenge.pk,
        consumed_at__isnull=True,
        expires_at__gt=now,
    ).update(**updates)
    return valid and changed == 1


def create_public_enquiry(*, user, full_name, phone_number, trip, group_size=1,
    email="", city="", preferred_departure_month=None, message=""):
    """
    Create an enquiry and record the staff member who entered it.
    """
    if not user.is_authenticated or not user.is_staff:
        raise PermissionDenied("Only logged-in staff can create enquiries.")

    normalized_phone = normalize_phone_number(phone_number)
    with transaction.atomic():
        contact, created = Contact.objects.get_or_create(
            phone_number=normalized_phone,
            defaults={
                "full_name": full_name,
                "email": email,
                "city": city,
            },
        )
        if not created:
            contact.full_name = full_name
            if email:
                contact.email = email
            if city:
                contact.city = city
            contact.save()
        return Lead.objects.create(
            created_by=user,
            modified_by=user,
            contact=contact,
            trip=trip,
            group_size=group_size,
            source=AcquisitionSource.WEBSITE,
            status=LeadStatus.NEW,
            interest_level=LeadInterestLevel.WARM,
            phone_verified=False,
            verified_phone_number="",
            preferred_departure_month=preferred_departure_month,
            notes=message,
        )
