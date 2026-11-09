from django.core.exceptions import ValidationError
from django.db import transaction
from apps.leads.enums import LeadStatus, CampaignStatus, AcquisitionSource, LeadInterestLevel
from apps.leads.models import Lead, LeadStatusHistory, LeadInteraction, Contact, Campaign
from apps.leads.permissions import is_crm_admin, get_accessible_lead
from django.core.exceptions import PermissionDenied
from django.utils.text import slugify
from apps.leads.utils import normalize_phone_number


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


@transaction.atomic
def create_public_enquiry(*, full_name, phone_number, trip, group_size=1,
    email="", city="", preferred_departure_month=None, message=""):
    """
    Create a public website enquiry and its associated lead.
    No customer authentication is required.
    """
    normalized_phone = normalize_phone_number(phone_number)
    contact, created = Contact.objects.get_or_create(
        phone_number=normalized_phone,
        defaults={
            "full_name": full_name,
            "email": email,
            "city": city,
        },
    )
    # Refresh existing contact details when new information is supplied.
    if not created:
        contact.full_name = full_name
        if email:
            contact.email = email
        if city:
            contact.city = city
        contact.save()
    lead = Lead.objects.create(
        contact=contact,
        trip=trip,
        group_size=group_size,
        source=AcquisitionSource.WEBSITE,
        status=LeadStatus.NEW,
        interest_level=LeadInterestLevel.WARM,
        preferred_departure_month=preferred_departure_month,
        notes=message,
    )
    return lead
