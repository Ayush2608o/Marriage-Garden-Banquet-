import re

from django import forms

from .models import Enquiry


class EnquiryForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = ("name", "email", "phone", "venue", "event_type", "event_date", "guest_count", "notes")
        widgets = {
            "venue": forms.HiddenInput(),
            "event_date": forms.DateInput(attrs={"type": "date"}),
            "guest_count": forms.NumberInput(attrs={"min": 1, "max": 10000}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["venue"].queryset = self.fields["venue"].queryset.filter(is_active=True)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Enter your name.")
        return name

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        digits = re.sub(r"\D", "", phone)
        if not re.fullmatch(r"\+?[0-9][0-9\s().-]{6,23}", phone) or not 7 <= len(digits) <= 15:
            raise forms.ValidationError("Enter a valid phone number with 7 to 15 digits.")
        return phone

    def clean_notes(self):
        return self.cleaned_data["notes"].strip()
