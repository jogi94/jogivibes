
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
    preferred_departure_month = forms.DateField(required=False, label="Preferred Departure Month",
        input_formats=["%Y-%m"],
        widget=forms.DateInput(attrs={
            "type": "month",
        }))
    message = forms.CharField(required=False, label="Additional Requirements",
        widget=forms.Textarea(attrs={
            "rows": 4,
            "placeholder": "Tell us about your travel plans...",
        }))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["trip"].queryset = Trip.objects.all()



class LeadStatusForm(forms.Form):
    status = forms.ChoiceField(choices=LeadStatus.choices, label="Lead Status")
    reason = forms.CharField(
        required=False, label="Reason for Status Change",
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Why are you changing this lead's status?",
        }))
