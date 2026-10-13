from django.contrib import admin

from apps.core.admin import TrackedModelAdminMixin
from apps.bookings.models import TripSchedule


@admin.register(TripSchedule)
class TripScheduleAdmin(TrackedModelAdminMixin, admin.ModelAdmin):
    list_display = (
        "trip",
        "start_date",
        "end_date",
        "capacity",
        "status",
        "modified",
    )
    list_filter = ("status", "start_date")
    search_fields = ("trip__name", "trip__slug", "trip__destination__name")
    autocomplete_fields = ("trip",)
    list_select_related = ("trip", "trip__destination")
    ordering = ("start_date",)
    readonly_fields = ("created", "modified", "created_by", "modified_by")

    fieldsets = (
        (
            "Schedule",
            {
                "fields": (
                    "trip",
                    "start_date",
                    "end_date",
                    "status",
                )
            },
        ),
        (
            "Capacity",
            {
                "fields": ("capacity",),
                "description": (
                    "Capacity can be set when creating a schedule. After creation, "
                    "change it only through the approved capacity override service "
                    "so confirmed bookings, active holds, and pending waitlist "
                    "offers remain within the schedule limit."
                ),
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created",
                    "modified",
                    "created_by",
                    "modified_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))

        if obj:
            fields.extend(
                field
                for field in ("trip", "start_date", "end_date", "capacity")
                if field not in fields
            )

        return tuple(fields)
