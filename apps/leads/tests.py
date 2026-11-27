from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, Client, override_settings
from unittest.mock import patch
from django.urls import reverse

from apps.leads.enums import AcquisitionSource, LeadStatus
from apps.leads.models import Contact, Lead, LeadPhoneOTP
from apps.leads.utils import normalize_phone_number
from apps.trips.enums import TripStatus
from apps.trips.models import Destination, Trip
from apps.users.models import CustomUser


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
        self.staff = CustomUser.objects.create_user(
            "9876500000", is_staff=True, username="staff"
        )
        self.client.force_login(self.staff)
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
        response = self.client.get(reverse("leads:leads_enquiry"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Trek")
        self.assertNotContains(response, "Draft Trek")
        self.assertNotContains(response, "Archived Trek")

    @patch("apps.leads.services.send_sms_verification", return_value={"status": "pending", "sid": "VE" + "a" * 32})
    def test_valid_post_creates_unverified_lead_then_sends_otp(self, send_otp):
        response = self.client.post(reverse("leads:leads_enquiry"), self.post_data())

        contact = Contact.objects.get(phone_number="+919876543210")
        lead = Lead.objects.get(contact=contact)
        self.assertRedirects(response, reverse("leads:enquiry_verify", kwargs={"pk": lead.pk}))
        self.assertEqual(lead.trip, self.published_trip)
        self.assertEqual(lead.source, AcquisitionSource.WEBSITE)
        self.assertEqual(lead.status, LeadStatus.NEW)
        self.assertEqual(lead.group_size, 3)
        self.assertEqual(lead.preferred_departure_month.isoformat(), "2027-04-01")
        self.assertEqual(lead.notes, "Vegetarian meals, please.")
        self.assertEqual(lead.created_by, self.staff)
        self.assertFalse(lead.phone_verified)
        send_otp.assert_called_once_with(phone_number=contact.phone_number)

    def test_unpublished_trip_ids_are_rejected_without_records(self):
        for trip in (self.draft_trip, self.archived_trip):
            with self.subTest(status=trip.status):
                response = self.client.post(
                    reverse("leads:leads_enquiry"), self.post_data(trip=str(trip.pk))
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
                    reverse("leads:leads_enquiry"), self.post_data(**overrides)
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
                self.assertEqual(Contact.objects.count(), 0)
                self.assertEqual(Lead.objects.count(), 0)

    def test_required_fields_are_validated_without_records(self):
        response = self.client.post(
            reverse("leads:leads_enquiry"),
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

    @patch("apps.leads.services.send_sms_verification", return_value={"status": "pending", "sid": "VE" + "a" * 32})
    def test_contact_is_reused_for_returning_phone_number(self, send_otp):
        self.client.post(reverse("leads:leads_enquiry"), self.post_data())
        self.client.post(
            reverse("leads:leads_enquiry"),
            self.post_data(full_name="Asha R.", trip=str(self.published_trip.pk)),
        )

        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(Lead.objects.count(), 2)

    def test_filled_honeypot_returns_success_without_crm_records(self):
        response = self.client.post(
            reverse("leads:leads_enquiry"), self.post_data(website="spam.example")
        )

        self.assertRedirects(response, reverse("leads:enquiry_success"))
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(Lead.objects.count(), 0)

    @patch("apps.leads.services.send_sms_verification", return_value={"status": "pending", "sid": "VE" + "a" * 32})
    def test_submit_records_otp_challenge_for_phone_and_staff(self, send_otp):
        response = self.client.post(
            reverse("leads:leads_enquiry"),
            self.post_data(),
        )

        lead = Lead.objects.get()
        self.assertRedirects(response, reverse("leads:enquiry_verify", kwargs={"pk": lead.pk}))
        challenge = LeadPhoneOTP.objects.get()
        self.assertEqual(challenge.phone_number, "+919876543210")
        self.assertEqual(challenge.created_by, self.staff)
        self.assertEqual(challenge.lead, lead)
        send_otp.assert_called_once_with(phone_number="+919876543210")

    @patch("apps.leads.services.check_sms_verification", return_value=True)
    @patch("apps.leads.services.send_sms_verification", return_value={"status": "pending", "sid": "VE" + "b" * 32})
    def test_approved_otp_marks_only_matching_phone_verified(self, send_otp, check_otp):
        response = self.client.post(reverse("leads:leads_enquiry"), self.post_data())
        lead = Lead.objects.get()
        response = self.client.post(
            reverse("leads:enquiry_verify", kwargs={"pk": lead.pk}),
            {"verification_code": "123456", "action": "verify"},
        )

        self.assertRedirects(response, reverse("leads:enquiry_success"))
        lead = Lead.objects.get()
        self.assertTrue(lead.phone_verified)
        self.assertEqual(lead.verified_phone_number, lead.contact.phone_number)
        self.assertEqual(lead.created_by, self.staff)
        check_otp.assert_called_once_with(
            verification_sid="VE" + "b" * 32,
            code="123456",
        )

    @patch("apps.leads.services.check_sms_verification", side_effect=[False, True])
    @patch("apps.leads.services.send_sms_verification", return_value={"status": "pending", "sid": "VE" + "c" * 32})
    def test_wrong_otp_stays_unverified_and_correct_retry_succeeds(self, send_otp, check_otp):
        self.client.post(reverse("leads:leads_enquiry"), self.post_data())
        lead = Lead.objects.get()
        verify_url = reverse("leads:enquiry_verify", kwargs={"pk": lead.pk})
        response = self.client.post(verify_url, {"verification_code": "000000", "action": "verify"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(lead.phone_verified)
        self.assertEqual(lead.verified_phone_number, "")
        response = self.client.post(verify_url, {"verification_code": "123456", "action": "verify"})
        self.assertRedirects(response, reverse("leads:enquiry_success"))

    def test_changing_contact_phone_clears_lead_verification(self):
        contact = Contact.objects.create(full_name="Verified", phone_number="9876543210")
        lead = Lead.objects.create(
            contact=contact,
            trip=self.published_trip,
            phone_verified=True,
            verified_phone_number=contact.phone_number,
        )

        contact.phone_number = "9876543211"
        contact.save()
        lead.refresh_from_db()

        self.assertFalse(lead.phone_verified)
        self.assertEqual(lead.verified_phone_number, "")
