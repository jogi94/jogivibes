from django.contrib import admin

from apps.leads.models import (
    Campaign,
    Contact,
    Lead,
    LeadInteraction,
    LeadStatusHistory,
)
from apps.leads.permissions import (
    get_accessible_leads,
    is_crm_admin,
)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone_number", "email", "city")
    search_fields = ("full_name", "phone_number", "email")
    ordering = ("full_name",)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "contact",
        "trip",
        "status",
        "interest_level",
        "assigned_to",
        "next_follow_up_date",
    )
    list_filter = ("status", "interest_level", "trip")
    search_fields = (
        "contact__full_name",
        "contact__phone_number",
    )
    readonly_fields = (
        "contact",
        "trip",
        "campaign",
        "group_size",
        "preferred_departure_month",
        "preferred_schedule",
        "preferred_departure_date",
        "status",
        "interest_level",
        "assigned_to",
        "next_follow_up_date",
        "next_follow_up_action",
        "notes",
        "created",
        "modified",
        "created_by",
        "modified_by",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(
            pk__in=get_accessible_leads(request.user).values("pk")
        )

    def has_view_permission(self, request, obj=None):
        if obj is None:
            return request.user.is_authenticated

        return get_accessible_leads(request.user).filter(
            pk=obj.pk
        ).exists()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "acquisition_source",
        "start_date",
        "end_date",
        "status",
    )
    list_filter = ("status", "acquisition_source")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    def has_module_permission(self, request):
        return is_crm_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_crm_admin(request.user)

    def has_add_permission(self, request):
        return is_crm_admin(request.user)

    def has_change_permission(self, request, obj=None):
        return is_crm_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LeadInteraction)
class LeadInteractionAdmin(admin.ModelAdmin):
    list_display = (
        "lead",
        "interaction_date",
        "channel",
        "interaction_type",
        "contact_result",
        "created_by",
    )
    list_filter = ("channel", "interaction_type", "contact_result")
    readonly_fields = (
        "lead",
        "interaction_date",
        "channel",
        "interaction_type",
        "contact_result",
        "summary",
        "objection",
        "interest_after_interaction",
        "next_action",
        "next_follow_up_date",
        "created_by",
        "created",
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.filter(
            lead__in=get_accessible_leads(request.user)
        )

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False

        if obj is None:
            return True

        return get_accessible_leads(request.user).filter(
            pk=obj.lead_id
        ).exists()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LeadStatusHistory)
class LeadStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "lead",
        "previous_status",
        "new_status",
        "changed_by",
        "changed_at"
    )
    readonly_fields = (
        "lead",
        "previous_status",
        "new_status",
        "changed_by",
        "changed_at",
        "reason"
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False