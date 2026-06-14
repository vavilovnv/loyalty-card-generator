"""Model tests for the cards application."""

from decimal import Decimal

from django.test import TestCase

from cards.models import CardStatus
from cards.tests.factories import create_card, create_purchase


class CardModelTests(TestCase):
    """Tests for the loyalty card model."""

    def test_string_representation_uses_series_and_number(self) -> None:
        # -- Arrange --
        card = create_card(series="VIP", number="000000000123")

        # -- Act --
        result = str(card)

        # -- Assert --
        self.assertEqual(result, "VIP-000000000123")

    def test_is_expired_reflects_status(self) -> None:
        # -- Arrange --
        expired_card = create_card(
            number="000000000002",
            status=CardStatus.EXPIRED,
        )
        active_card = create_card(
            number="000000000003",
            status=CardStatus.ACTIVATED,
        )

        # -- Act --
        expired_result = expired_card.is_expired
        active_result = active_card.is_expired

        # -- Assert --
        self.assertTrue(expired_result)
        self.assertFalse(active_result)


class PurchaseModelTests(TestCase):
    """Tests for the purchase model."""

    def test_string_representation_includes_card_and_amount(self) -> None:
        # -- Arrange --
        card = create_card(series="B", number="000000000004")
        purchase = create_purchase(card=card, amount=Decimal("15.50"))

        # -- Act --
        result = str(purchase)

        # -- Assert --
        self.assertEqual(result, "B-000000000004 purchase for 15.50")
