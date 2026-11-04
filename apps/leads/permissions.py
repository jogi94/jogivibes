from django.core.exceptions import PermissionDenied

from apps.leads.models import Lead


CRM_ADMIN_GROUP = "CRM Admin"


def is_crm_admin(user):
    if not user.is_authenticated:
        return False

    return (user.is_superuser or user.groups.filter(name=CRM_ADMIN_GROUP).exists())


def get_accessible_leads(user):
    """
    Return leads the user is allowed to access.
    """
    if not user.is_authenticated:
        return Lead.objects.none()

    if is_crm_admin(user):
        return Lead.objects.all()

    return Lead.objects.filter(assigned_to=user)


def get_accessible_lead(user, lead_id):
    """
    Retrieve a lead only if the user has access.
    """
    try:
        return get_accessible_leads(user).get(pk=lead_id)
    except Lead.DoesNotExist:
        raise PermissionDenied(
            "You do not have permission to access this lead."
        )