from types import SimpleNamespace
from django.contrib import admin
from django.test import SimpleTestCase
from apps.bookings.models import TripSchedule
from apps.trips.admin import (
    ItineraryInline,
    SeasonListFilter,
    TripImageInline,
    PackageItemInline,
)
from apps.trips.models import (
    Destination,
    Itinerary,
    Package,
    PackageItem,
    Pricing,
    SchedulePackage,
    Trip,
    TripImage,
)


class TripAdminConfigurationTests(SimpleTestCase):
    def test_trip_domain_models_are_registered(self):
        for model in (
            Destination,
            Trip,
            TripImage,
            Itinerary,
            Package,
            PackageItem,
            SchedulePackage,
            Pricing,
            TripSchedule,
        ):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin.site._registry)

    def test_trip_admin_has_content_management_controls(self):
        model_admin = admin.site._registry[Trip]

        self.assertIn("name", model_admin.list_display)
        self.assertIn("status", model_admin.list_filter)
        self.assertIn("difficulty", model_admin.list_filter)
        self.assertIn(SeasonListFilter, model_admin.list_filter)
        self.assertIn("name", model_admin.search_fields)
        self.assertEqual(
            model_admin.prepopulated_fields,
            {"slug": ("name",)},
        )

    def test_trip_admin_includes_images_and_one_itinerary(self):
        model_admin = admin.site._registry[Trip]

        self.assertIn(TripImageInline, model_admin.inlines)
        self.assertIn(ItineraryInline, model_admin.inlines)
        self.assertEqual(ItineraryInline.max_num, 1)
        self.assertEqual(TripImageInline.model, TripImage)
        self.assertEqual(ItineraryInline.model, Itinerary)

    def test_existing_model_relationships_are_preserved(self):
        self.assertIs(
            TripImage._meta.get_field("trip").remote_field.model,
            Trip,
        )
        self.assertIs(
            Itinerary._meta.get_field("trip").remote_field.model,
            Trip,
        )
        self.assertIs(
            PackageItem._meta.get_field("package").remote_field.model,
            Package,
        )
        self.assertIs(
            SchedulePackage._meta.get_field(
                "trip_schedule"
            ).remote_field.model,
            TripSchedule,
        )
        self.assertIs(
            SchedulePackage._meta.get_field("package").remote_field.model,
            Package,
        )
        self.assertIn(
            "unique_trip_cover_image",
            {constraint.name for constraint in TripImage._meta.constraints},
        )

    def test_related_admins_have_search_and_list_configuration(self):
        for model in (
            Destination,
            Package,
            SchedulePackage,
            Pricing,
            TripSchedule,
        ):
            model_admin = admin.site._registry[model]

            with self.subTest(model=model.__name__):
                self.assertTrue(model_admin.list_display)
                self.assertTrue(model_admin.search_fields)
                self.assertTrue(model_admin.list_filter)

    def test_package_admin_includes_package_items(self):
        self.assertIn(
            PackageItemInline,
            admin.site._registry[Package].inlines,
        )

    def test_schedule_identity_and_capacity_are_read_only_after_creation(self):
        model_admin = admin.site._registry[TripSchedule]

        readonly = model_admin.get_readonly_fields(
            request=None,
            obj=object(),
        )
        self.assertTrue(
            {"trip", "start_date", "end_date", "capacity"}.issubset(
                set(readonly)
            )
        )

        add_readonly = model_admin.get_readonly_fields(
            request=None,
            obj=None,
        )
        self.assertNotIn("capacity", add_readonly)

    def test_existing_pricing_terms_are_read_only(self):
        model_admin = admin.site._registry[Pricing]

        readonly = set(
            model_admin.get_readonly_fields(
                request=None,
                obj=SimpleNamespace(retired_at=None),
            )
        )

        self.assertTrue(
            {
                "schedule_package",
                "pricing_type",
                "customer",
                "amount",
                "currency",
                "effective_from",
                "effective_until",
            }.issubset(readonly)
        )
