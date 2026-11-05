
from django import forms

from apps.leads.enums import (
    ContactResult,
    InteractionChannel,
    InteractionType,
    LeadInterestLevel,
)


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