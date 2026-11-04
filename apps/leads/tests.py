from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.leads.models import Contact
from apps.leads.utils import normalize_phone_number


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
