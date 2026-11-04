import phonenumbers

from django.core.exceptions import ValidationError


def normalize_phone_number(phone_number: str) -> str:
    """
    Normalize phone numbers to E.164 format.

    Indian 10-digit numbers default to country code +91.
    International numbers must include their country code.
    """

    if not phone_number:
        raise ValidationError("Phone number is required.")

    phone_number = phone_number.strip()
    try:
        if phone_number.isdigit() and len(phone_number) == 10:
            parsed_number = phonenumbers.parse(phone_number, "IN")
        else:
            parsed_number = phonenumbers.parse(phone_number, None)

        if not phonenumbers.is_valid_number(parsed_number):
            raise ValidationError("Enter a valid phone number.")

        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        raise ValidationError("Enter a valid international phone number.")
