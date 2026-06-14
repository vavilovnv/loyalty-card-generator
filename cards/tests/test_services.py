"""Service tests for the cards application."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from cards.models import Card, CardStatus
from cards.services import (
    CARD_NUMBER_LENGTH,
    MAX_GENERATION_ATTEMPTS,
    CardGenerationError,
    add_months,
    expire_cards,
    generate_cards,
    refresh_card_usage,
)
from cards.tests.factories import create_card, create_purchase


class AddMonthsTests(TestCase):
    """Tests for calendar month arithmetic."""

    def test_add_months_clamps_to_last_day_of_target_month(self) -> None:
        # -- Arrange --
        value = datetime(2024, 1, 31, 12, 0, tzinfo=UTC)

        # -- Act --
        result = add_months(value, 1)

        # -- Assert --
        self.assertEqual(result, datetime(2024, 2, 29, 12, 0, tzinfo=UTC))

    def test_add_months_crosses_year_boundary(self) -> None:
        # -- Arrange --
        value = datetime(2024, 11, 30, 12, 0, tzinfo=UTC)

        # -- Act --
        result = add_months(value, 6)

        # -- Assert --
        self.assertEqual(result, datetime(2025, 5, 30, 12, 0, tzinfo=UTC))


class GenerateCardsTests(TestCase):
    """Tests for loyalty card generation."""

    def test_generate_cards_creates_requested_cards(self) -> None:
        # -- Arrange --
        with patch("cards.services.randbelow", side_effect=[1, 2, 3]):
            # -- Act --
            cards = generate_cards(series="VIP", count=3, duration_months=6)

        # -- Assert --
        self.assertEqual(len(cards), 3)
        self.assertEqual(Card.objects.count(), 3)
        self.assertEqual(
            [card.number for card in cards],
            [
                "000000000001",
                "000000000002",
                "000000000003",
            ],
        )
        self.assertTrue(all(card.status == CardStatus.NOT_ACTIVATED for card in cards))
        self.assertTrue(all(len(card.number) == CARD_NUMBER_LENGTH for card in cards))

    def test_generate_cards_retries_when_batch_contains_duplicates(self) -> None:
        # -- Arrange --
        with patch("cards.services.randbelow", side_effect=[1, 1, 2, 3]):
            # -- Act --
            cards = generate_cards(series="VIP", count=2, duration_months=1)

        # -- Assert --
        self.assertEqual(
            [card.number for card in cards], ["000000000002", "000000000003"]
        )

    def test_generate_cards_retries_after_integrity_error(self) -> None:
        # -- Arrange --
        create_card(series="VIP", number="000000000001")

        with patch("cards.services.randbelow", side_effect=[1, 2]):
            # -- Act --
            cards = generate_cards(series="VIP", count=1, duration_months=12)

        # -- Assert --
        self.assertEqual(cards[0].number, "000000000002")
        self.assertEqual(Card.objects.filter(series="VIP").count(), 2)

    def test_generate_cards_rejects_invalid_count(self) -> None:
        # -- Arrange --
        error: CardGenerationError | None = None

        # -- Act --
        try:
            generate_cards(series="VIP", count=0, duration_months=1)
        except CardGenerationError as exc:
            error = exc

        # -- Assert --
        self.assertIsNotNone(error)

    def test_generate_cards_rejects_invalid_duration(self) -> None:
        # -- Arrange --
        error: CardGenerationError | None = None

        # -- Act --
        try:
            generate_cards(series="VIP", count=1, duration_months=2)
        except CardGenerationError as exc:
            error = exc

        # -- Assert --
        self.assertIsNotNone(error)

    def test_generate_cards_fails_after_too_many_collisions(self) -> None:
        # -- Arrange --
        values = [1] * (MAX_GENERATION_ATTEMPTS * 2)
        error: CardGenerationError | None = None

        # -- Act --
        try:
            with patch("cards.services.randbelow", side_effect=values):
                generate_cards(series="VIP", count=2, duration_months=1)
        except CardGenerationError as exc:
            error = exc

        # -- Assert --
        self.assertIsNotNone(error)


class ExpireCardsTests(TestCase):
    """Tests for loyalty card expiration."""

    def test_expire_cards_marks_only_outdated_non_expired_cards(self) -> None:
        # -- Arrange --
        now = timezone.now()
        expired_candidate = create_card(
            number="000000000010",
            expires_delta=timedelta(days=-1),
            status=CardStatus.ACTIVATED,
        )
        active_card = create_card(
            number="000000000011",
            expires_delta=timedelta(days=1),
            status=CardStatus.ACTIVATED,
        )
        already_expired_card = create_card(
            number="000000000012",
            expires_delta=timedelta(days=-2),
            status=CardStatus.EXPIRED,
        )

        # -- Act --
        updated_count = expire_cards(now=now)

        # -- Assert --
        expired_candidate.refresh_from_db()
        active_card.refresh_from_db()
        already_expired_card.refresh_from_db()
        self.assertEqual(updated_count, 1)
        self.assertEqual(expired_candidate.status, CardStatus.EXPIRED)
        self.assertEqual(active_card.status, CardStatus.ACTIVATED)
        self.assertEqual(already_expired_card.status, CardStatus.EXPIRED)


class RefreshCardUsageTests(TestCase):
    """Tests for loyalty card balance refresh."""

    def test_refresh_card_usage_sets_balance_and_last_purchase_time(self) -> None:
        # -- Arrange --
        card = create_card(amount=Decimal("99.00"))
        older_purchase = create_purchase(
            card=card,
            amount=Decimal("10.00"),
            purchased_delta=timedelta(days=-2),
        )
        newer_purchase = create_purchase(
            card=card,
            amount=Decimal("15.50"),
            purchased_delta=timedelta(days=-1),
        )

        # -- Act --
        refreshed_card = refresh_card_usage(card)

        # -- Assert --
        self.assertEqual(refreshed_card.amount, Decimal("25.50"))
        self.assertEqual(refreshed_card.used_at, newer_purchase.purchased_at)
        self.assertNotEqual(refreshed_card.used_at, older_purchase.purchased_at)

    def test_refresh_card_usage_resets_card_without_purchases(self) -> None:
        # -- Arrange --
        card = create_card(amount=Decimal("99.00"))

        # -- Act --
        refreshed_card = refresh_card_usage(card)

        # -- Assert --
        self.assertEqual(refreshed_card.amount, Decimal("0.00"))
        self.assertIsNone(refreshed_card.used_at)


class GenerateCardsCollisionTests(TestCase):
    """Tests for database collision handling during generation."""

    def test_generate_cards_retries_bulk_create_integrity_error(self) -> None:
        # -- Arrange --
        real_bulk_create = Card.objects.bulk_create

        def flaky_bulk_create(cards: list[Card]) -> list[Card]:
            if not hasattr(flaky_bulk_create, "called"):
                flaky_bulk_create.called = True  # type: ignore[attr-defined]
                raise IntegrityError

            return real_bulk_create(cards)

        with (
            patch.object(Card.objects, "bulk_create", side_effect=flaky_bulk_create),
            patch("cards.services.randbelow", side_effect=[1, 2]),
        ):
            # -- Act --
            cards = generate_cards(series="VIP", count=1, duration_months=1)

        # -- Assert --
        self.assertEqual(cards[0].number, "000000000002")
