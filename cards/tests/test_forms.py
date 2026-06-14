"""Form tests for the cards application."""

from django.test import SimpleTestCase

from cards.forms import CardGenerationForm


class CardGenerationFormTests(SimpleTestCase):
    """Tests for loyalty card generation form validation."""

    def test_valid_form_normalizes_series_and_duration(self) -> None:
        # -- Arrange --
        form = CardGenerationForm(
            data={
                "series": " vip ",
                "count": "3",
                "duration_months": "6",
            }
        )

        # -- Act --
        is_valid = form.is_valid()
        duration_months = form.get_duration_months()

        # -- Assert --
        self.assertTrue(is_valid)
        self.assertEqual(form.cleaned_data["series"], "VIP")
        self.assertEqual(form.cleaned_data["count"], 3)
        self.assertEqual(duration_months, 6)

    def test_form_rejects_zero_count(self) -> None:
        # -- Arrange --
        form = CardGenerationForm(
            data={
                "series": "A",
                "count": "0",
                "duration_months": "1",
            }
        )

        # -- Act --
        is_valid = form.is_valid()

        # -- Assert --
        self.assertFalse(is_valid)
        self.assertIn("count", form.errors)

    def test_form_rejects_unsupported_duration(self) -> None:
        # -- Arrange --
        form = CardGenerationForm(
            data={
                "series": "A",
                "count": "1",
                "duration_months": "2",
            }
        )

        # -- Act --
        is_valid = form.is_valid()

        # -- Assert --
        self.assertFalse(is_valid)
        self.assertIn("duration_months", form.errors)
