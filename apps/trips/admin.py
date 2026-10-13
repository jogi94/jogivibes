from django import forms
from django.contrib import admin
from django.utils import timezone

from apps.core.admin import TrackedModelAdminMixin
from apps.bookings.models import TripSchedule
from apps.trips.enums import Season
from apps.trips.models.destination import Destination
from apps.trips.models.itinerary import Itinerary
from apps.trips.models.package import Package
from apps.trips.models.package_item import PackageItem
from apps.trips.models.pricing import Pricing
from apps.trips.models.schedule_package import SchedulePackage
from apps.trips.models.trip import Trip
from apps.trips.models.trip_image import TripImage


class SeasonListFilter(admin.SimpleListFilter):
    title = "season"
    parameter_name = "season"

    def lookups(self, request, model_admin):
        return Season.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(seasons__contains=[self.value()])
        return queryset


class TripImageInlineForm(forms.ModelForm):
    class Meta:
        model = TripImage
        fields = "__all__"
        help_texts = {
            "is_cover": "Select this for at most one image per trip.",
        }


class TripImageInline(admin.TabularInline):
    model = TripImage
    form = TripImageInlineForm
    extra = 1
    fields = ("image", "caption", "sort_order", "is_cover")
    ordering = ("sort_order", "id")
    verbose_name = "trip image"
    verbose_name_plural = "trip images"


class ItineraryInline(admin.StackedInline):
    model = Itinerary
    extra = 1
    max_num = 1
    fields = ("description",)
    verbose_name = "itinerary"
    verbose_name_plural = "itinerary"


@admin.register(Trip)
class TripAdmin(TrackedModelAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "destination",
        "type",
        "status",
        "difficulty",
        "duration_days",
        "max_altitude_m",
        "modified",
    )
    list_filter = ("type", "status", "difficulty", SeasonListFilter)
    search_fields = ("name", "slug", "destination__name")
    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("destination",)
    ordering = ("name",)
    readonly_fields = ("created", "modified", "created_by", "modified_by")

    fieldsets = (
        (
            "Trip content",
            {
                "fields": (
                    "name",
                    "slug",
                    "description",
                    "destination",
                )
            },
        ),
        (
            "Classification and publication",
            {
                "fields": (
                    "type",
                    "status",
                    "difficulty",
                    "seasons",
                )
            },
        ),
        (
            "Trip details",
            {
                "fields": ("duration_days", "max_altitude_m")
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

    inlines = (TripImageInline, ItineraryInline)


@admin.register(Destination)
class DestinationAdmin(TrackedModelAdminMixin, admin.ModelAdmin):
    list_display = ("name", "region", "country", "state", "city", "modified")
    search_fields = ("name", "slug", "region", "country", "state", "city")
    list_filter = ("country", "state")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)
    readonly_fields = ("created", "modified", "created_by", "modified_by")

    fieldsets = (
        ("Destination", {"fields": ("name", "slug", "description")}),
        ("Location", {"fields": ("region", "country", "state", "city")}),
        (
            "Audit",
            {
                "fields": ("created", "modified", "created_by", "modified_by"),
                "classes": ("collapse",),
            },
        ),
    )


class PackageItemInline(admin.TabularInline):
    model = PackageItem
    extra = 1
    fields = ("name", "description", "sort_order", "is_included")
    ordering = ("sort_order", "id")


@admin.register(Package)
class PackageAdmin(TrackedModelAdminMixin, admin.ModelAdmin):
    list_display = ("name", "trip", "slug", "is_active", "retired_at", "modified")
    list_filter = ("is_active", "trip")
    search_fields = ("name", "slug", "trip__name", "trip__slug")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("trip",)
    ordering = ("trip__name", "name")
    readonly_fields = ("created", "modified", "created_by", "modified_by", "retired_at")

    fieldsets = (
        ("Package", {"fields": ("trip", "name", "slug", "description")}),
        ("Availability", {"fields": ("is_active", "retired_at")}),
        (
            "Audit",
            {
                "fields": ("created", "modified", "created_by", "modified_by"),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = (PackageItemInline,)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))

        if obj and "trip" not in fields:
            fields.append("trip")

        if obj and obj.retired_at and "is_active" not in fields:
            fields.append("is_active")

        return tuple(fields)

    def save_model(self, request, obj, form, change):
        if change:
            previous = Package.objects.filter(pk=obj.pk).only(
                "is_active", "retired_at"
            ).first()

            if (
                previous
                and previous.is_active
                and not obj.is_active
                and not previous.retired_at
            ):
                obj.retired_at = timezone.now()

        super().save_model(request, obj, form, change)


@admin.register(SchedulePackage)
class SchedulePackageAdmin(TrackedModelAdminMixin, admin.ModelAdmin):
    list_display = (
        "trip_schedule",
        "package",
        "is_available",
        "retired_at",
        "modified",
    )
    list_filter = ("is_available", "trip_schedule__status")
    search_fields = (
        "trip_schedule__trip__name",
        "trip_schedule__trip__slug",
        "package__name",
        "package__slug",
    )
    autocomplete_fields = ("trip_schedule", "package")
    list_select_related = ("trip_schedule", "trip_schedule__trip", "package")
    readonly_fields = ("created", "modified", "created_by", "modified_by")

    fieldsets = (
        ("Schedule and package", {"fields": ("trip_schedule", "package")}),
        ("Availability", {"fields": ("is_available", "retired_at")}),
        (
            "Audit",
            {
                "fields": ("created", "modified", "created_by", "modified_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))

        if obj:
            fields.extend(
                field
                for field in ("trip_schedule", "package")
                if field not in fields
            )

        return tuple(fields)


@admin.register(Pricing)
class PricingAdmin(TrackedModelAdminMixin, admin.ModelAdmin):
    list_display = (
        "schedule_package",
        "pricing_type",
        "customer",
        "amount",
        "currency",
        "effective_from",
        "effective_until",
        "is_active",
        "retired_at",
    )
    list_filter = ("pricing_type", "is_active", "currency")
    search_fields = (
        "schedule_package__trip_schedule__trip__name",
        "schedule_package__package__name",
        "customer__phone_number",
        "customer__username",
    )
    autocomplete_fields = ("schedule_package",)
    list_select_related = (
        "schedule_package",
        "schedule_package__trip_schedule",
        "schedule_package__trip_schedule__trip",
        "schedule_package__package",
        "customer",
    )
    ordering = ("effective_from",)

    readonly_fields = (
        "effective_period",
        "created",
        "modified",
        "created_by",
        "modified_by",
        "retired_at",
    )

    fieldsets = (
        (
            "Pricing target",
            {"fields": ("schedule_package", "pricing_type", "customer")},
        ),
        ("Price", {"fields": ("amount", "currency")}),
        (
            "Validity",
            {
                "fields": (
                    "effective_from",
                    "effective_until",
                    "effective_period",
                    "is_active",
                    "retired_at",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": ("created", "modified", "created_by", "modified_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))

        if obj:
            fields.extend(
                field
                for field in (
                    "schedule_package",
                    "pricing_type",
                    "customer",
                    "amount",
                    "currency",
                    "effective_from",
                    "effective_until",
                )
                if field not in fields
            )

            if obj.retired_at and "is_active" not in fields:
                fields.append("is_active")

        return tuple(fields)

    def save_model(self, request, obj, form, change):
        if change:
            previous = Pricing.objects.filter(pk=obj.pk).only(
                "is_active", "retired_at"
            ).first()

            if (
                previous
                and previous.is_active
                and not obj.is_active
                and not previous.retired_at
            ):
                obj.retired_at = timezone.now()

        super().save_model(request, obj, form, change)



@admin.register(TripImage)
class TripImageAdmin(TrackedModelAdminMixin, admin.ModelAdmin):
    list_display = ("trip", "caption", "sort_order", "is_cover", "modified")
    list_filter = ("is_cover",)
    search_fields = ("trip__name", "trip__slug", "caption")
    autocomplete_fields = ("trip",)
    list_select_related = ("trip",)
    ordering = ("trip__name", "sort_order", "id")
    readonly_fields = ("created", "modified", "created_by", "modified_by")


@admin.register(Itinerary)
class ItineraryAdmin(TrackedModelAdminMixin, admin.ModelAdmin):
    list_display = ("trip", "modified")
    search_fields = ("trip__name", "trip__slug")
    autocomplete_fields = ("trip",)
    list_select_related = ("trip",)
    readonly_fields = ("created", "modified", "created_by", "modified_by")


@admin.register(PackageItem)
class PackageItemAdmin(TrackedModelAdminMixin, admin.ModelAdmin):
    list_display = ("name", "package", "sort_order", "is_included", "modified")
    list_filter = ("is_included",)
    search_fields = ("name", "package__name", "package__trip__name")
    autocomplete_fields = ("package",)
    list_select_related = ("package", "package__trip")
    ordering = ("package__name", "sort_order", "id")
    readonly_fields = ("created", "modified", "created_by", "modified_by")
