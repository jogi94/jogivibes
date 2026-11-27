
from django import forms
from apps.leads.enums import (
    ContactResult,
    InteractionChannel,
    InteractionType,
    LeadInterestLevel,
    AcquisitionSource,
    LeadStatus
)
from apps.leads.models import Contact
from apps.trips.models import Trip
from apps.trips.enums import TripStatus
from apps.leads.utils import normalize_phone_number
from django.core.exceptions import ValidationError


class LeadInteractionForm(forms.Form):
    interaction_date = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
    )
    channel = forms.ChoiceField(choices=InteractionChannel.choices)
    interaction_type = forms.ChoiceField(choices=InteractionType.choices)
    contact_result = forms.ChoiceField(choices=ContactResult.choices)
    summary = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    objection = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    interest_after_interaction = forms.ChoiceField(choices=[("", "Keep current interest level")]
                                 + list(LeadInterestLevel.choices), required=False)
    next_action = forms.CharField(required=False, max_length=255)
    next_follow_up_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))


class PublicEnquiryForm(forms.Form):
    full_name = forms.CharField(max_length=255, label="Full Name",
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your full name",
        }))
    phone_number = forms.CharField(max_length=16, label="Phone Number",
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your phone number",
            "type": "tel",
        }))
    email = forms.EmailField(required=False,
        widget=forms.EmailInput(attrs={
            "placeholder": "Enter your email address",
        }))
    city = forms.CharField(max_length=100, required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Your city",
        }))
    trip = forms.ModelChoiceField(queryset=Trip.objects.none(), label="Interested Trip")
    group_size = forms.IntegerField(min_value=1, initial=1, label="Number of Travelers")
    preferred_departure_month = forms.DateField(
        required=False,
        label="Preferred Departure Month",
        input_formats=["%Y-%m"],
        widget=forms.DateInput(
            attrs={"type": "month"},
            format="%Y-%m",
        ),
    )
    message = forms.CharField(required=False, label="Additional Requirements",
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Tell us about your travel plans...",
        }))
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
        label="",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["trip"].queryset = Trip.objects.filter(
            status=TripStatus.PUBLISHED
        )

    def clean_phone_number(self):
        try:
            return normalize_phone_number(self.cleaned_data["phone_number"])
        except ValidationError as error:
            raise forms.ValidationError(error.messages)


class LeadPhoneVerificationForm(forms.Form):
    verification_code = forms.CharField(
        required=False,
        max_length=10,
        label="Verification code",
        widget=forms.TextInput(attrs={
            "placeholder": "Enter the code sent by SMS",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
        }),
    )


class EnquiryPhoneUpdateForm(forms.Form):
    phone_number = forms.CharField(
        max_length=16,
        label="Enquirer mobile number",
        widget=forms.TextInput(attrs={"type": "tel", "placeholder": "Enter the correct mobile number"}),
    )

    def clean_phone_number(self):
        try:
            return normalize_phone_number(self.cleaned_data["phone_number"])
        except ValidationError as error:
            raise forms.ValidationError(error.messages)




class LeadStatusForm(forms.Form):
    status = forms.ChoiceField(choices=LeadStatus.choices, label="Lead Status")
    reason = forms.CharField(
        required=False, label="Reason for Status Change",
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Why are you changing this lead's status?",
        }))
