from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from apps.leads.enums import AcquisitionSource, LeadStatus
from apps.leads.models import Contact, Lead
from apps.leads.utils import normalize_phone_number
from apps.trips.enums import TripStatus
from apps.trips.models import Destination, Trip


class PhoneNumberNormalizationTests(TestCase):

    def test_normalizes_indian_number(self):
        result = normalize_phone_number("9876543210")
        self.assertEqual(result, "+919876543210")

    def test_accepts_international_number(self):
        result = normalize_phone_number("+14155552671")
        self.assertEqual(result, "+14155552671")

    def test_rejects_invalid_number(self):
        with self.assertRaises(ValidationError):
            normalize_phone_number("12345")


class ContactModelTests(TestCase):

    def test_create_contact(self):
        contact = Contact.objects.create(
            full_name="Rahul Sharma",
            phone_number="9876543210",
            email="rahul@example.com",
            city="Delhi",
        )

        self.assertEqual(contact.phone_number, "+919876543210")
        self.assertEqual(contact.full_name, "Rahul Sharma")

    def test_duplicate_phone_number_is_rejected(self):
        Contact.objects.create(
            full_name="Rahul Sharma",
            phone_number="9876543210",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Contact.objects.create(
                    full_name="Amit Sharma",
                    phone_number="+919876543210",
                )

    def test_optional_fields_can_be_blank(self):
        contact = Contact.objects.create(
            full_name="Rahul Sharma",
            phone_number="9876543210",
        )

        self.assertEqual(contact.email, "")
        self.assertEqual(contact.city, "")


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
})
class PublicEnquiryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.destination = Destination.objects.create(
            name="Himachal", slug="himachal", country="India"
        )
        self.published_trip = self.make_trip("Published Trek", TripStatus.PUBLISHED)
        self.draft_trip = self.make_trip("Draft Trek", TripStatus.DRAFT)
        self.archived_trip = self.make_trip("Archived Trek", TripStatus.ARCHIVED)

    def make_trip(self, name, status):
        slug = name.lower().replace(" ", "-")
        return Trip.objects.create(
            name=name,
            slug=slug,
            status=status,
            destination=self.destination,
            duration_days=3,
        )

    def post_data(self, **overrides):
        data = {
            "full_name": "Asha Rao",
            "phone_number": "9876543210",
            "email": "asha@example.com",
            "city": "Pune",
            "trip": str(self.published_trip.pk),
            "group_size": "3",
            "preferred_departure_month": "2027-04",
            "message": "Vegetarian meals, please.",
        }
        data.update(overrides)
        return data

    def test_get_shows_public_enquiry_form_and_only_published_trips(self):
        response = self.client.get(reverse("leads:enquiry"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Trek")
        self.assertNotContains(response, "Draft Trek")
        self.assertNotContains(response, "Archived Trek")

    def test_valid_post_creates_contact_and_website_lead_then_redirects(self):
        response = self.client.post(reverse("leads:enquiry"), self.post_data())

        self.assertRedirects(response, reverse("leads:enquiry-success"))
        contact = Contact.objects.get(phone_number="+919876543210")
        lead = Lead.objects.get(contact=contact)
        self.assertEqual(lead.trip, self.published_trip)
        self.assertEqual(lead.source, AcquisitionSource.WEBSITE)
        self.assertEqual(lead.status, LeadStatus.NEW)
        self.assertEqual(lead.group_size, 3)
        self.assertEqual(lead.preferred_departure_month.isoformat(), "2027-04-01")
        self.assertEqual(lead.notes, "Vegetarian meals, please.")

    def test_unpublished_trip_ids_are_rejected_without_records(self):
        for trip in (self.draft_trip, self.archived_trip):
            with self.subTest(status=trip.status):
                response = self.client.post(
                    reverse("leads:enquiry"), self.post_data(trip=str(trip.pk))
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("trip", response.context["form"].errors)
                self.assertEqual(Contact.objects.count(), 0)
                self.assertEqual(Lead.objects.count(), 0)

    def test_invalid_phone_and_group_size_do_not_create_partial_records(self):
        for overrides, field in (
            ({"phone_number": "12345"}, "phone_number"),
            ({"group_size": "0"}, "group_size"),
        ):
            with self.subTest(field=field):
                response = self.client.post(
                    reverse("leads:enquiry"), self.post_data(**overrides)
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.assertEqual(Contact.objects.count(), 0)
                self.assertEqual(Lead.objects.count(), 0)

    def test_required_fields_are_validated_without_records(self):
        response = self.client.post(
            reverse("leads:enquiry"),
            {"full_name": "", "phone_number": "", "trip": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            {"full_name", "phone_number", "trip"}.issubset(
                response.context["form"].errors
            )
        )
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(Lead.objects.count(), 0)

    def test_contact_is_reused_for_returning_phone_number(self):
        self.client.post(reverse("leads:enquiry"), self.post_data())
        self.client.post(
            reverse("leads:enquiry"),
            self.post_data(full_name="Asha R.", trip=str(self.published_trip.pk)),
        )

        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(Lead.objects.count(), 2)

    def test_filled_honeypot_returns_success_without_crm_records(self):
        response = self.client.post(
            reverse("leads:enquiry"), self.post_data(website="spam.example")
        )

        self.assertRedirects(response, reverse("leads:enquiry-success"))
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(Lead.objects.count(), 0)
