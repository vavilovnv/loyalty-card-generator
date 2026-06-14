"""Forms for loyalty card management views."""

from typing import Any

from django import forms


class CardGenerationForm(forms.Form):
    """Validate loyalty card generation parameters."""

    DURATION_CHOICES: tuple[tuple[str, str], ...] = (
        ("1", "1 month"),
        ("6", "6 months"),
        ("12", "1 year"),
    )

    series = forms.CharField(
        label="Series",
        max_length=32,
        widget=forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
    )
    count = forms.IntegerField(
        label="Quantity",
        min_value=1,
        max_value=1000,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    duration_months = forms.ChoiceField(
        label="Activity period",
        choices=DURATION_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def clean_series(self) -> str:
        """Return a normalized loyalty card series."""
        value: str = self.cleaned_data["series"]

        return value.strip().upper()

    def get_duration_months(self) -> int:
        """Return the selected activity period in months."""
        value: Any = self.cleaned_data["duration_months"]

        return int(value)
