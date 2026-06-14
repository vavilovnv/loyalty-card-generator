"""Business services for loyalty card generation and expiration."""

from calendar import monthrange
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from secrets import randbelow
from typing import cast

from django.db import IntegrityError, transaction
from django.db.models import Max, Sum
from django.utils import timezone

from cards.models import Card, CardStatus, Purchase

CARD_NUMBER_LENGTH: int = 12
MAX_GENERATION_ATTEMPTS: int = 20


class CardGenerationError(ValueError):
    """Raised when loyalty cards cannot be generated with the requested parameters."""


def add_months(value: datetime, months: int) -> datetime:
    """Return a datetime shifted by a number of calendar months."""
    month_index: int = value.month - 1 + months
    year: int = value.year + month_index // 12
    month: int = month_index % 12 + 1
    day: int = min(value.day, monthrange(year, month)[1])

    return value.replace(year=year, month=month, day=day)


def generate_cards(series: str, count: int, duration_months: int) -> list[Card]:
    """Generate loyalty cards for a series and activity duration."""
    if count < 1:
        raise CardGenerationError("Loyalty card count must be greater than zero.")

    if duration_months not in {1, 6, 12}:
        raise CardGenerationError("Unsupported activity duration.")

    issued_at: datetime = timezone.now()
    expires_at: datetime = add_months(issued_at, duration_months)

    for _attempt in range(MAX_GENERATION_ATTEMPTS):
        cards: list[Card] = [
            Card(
                series=series,
                number=_generate_number(),
                issued_at=issued_at,
                expires_at=expires_at,
                status=CardStatus.NOT_ACTIVATED,
            )
            for _index in range(count)
        ]
        if _has_duplicates(card.number for card in cards):
            continue

        try:
            with transaction.atomic():
                return list(Card.objects.bulk_create(cards))
        except IntegrityError:
            continue

    raise CardGenerationError("Could not generate unique loyalty card numbers.")


def expire_cards(now: datetime | None = None) -> int:
    """Mark outdated non-expired loyalty cards as expired."""
    current_time: datetime = now or timezone.now()
    updated_count: int = (
        Card.objects.filter(
            expires_at__lt=current_time,
        )
        .exclude(status=CardStatus.EXPIRED)
        .update(status=CardStatus.EXPIRED)
    )

    return updated_count


def refresh_card_usage(card: Card) -> Card:
    """Refresh loyalty card balance and last usage time from purchases."""
    totals: dict[str, object] = Purchase.objects.filter(card=card).aggregate(
        balance=Sum("amount"),
        used_at=Max("purchased_at"),
    )

    card.amount = cast(Decimal | None, totals["balance"]) or Decimal("0.00")
    card.used_at = cast(datetime | None, totals["used_at"])
    card.save(update_fields=["amount", "used_at"])

    return card


def _generate_number() -> str:
    number: int = randbelow(10**CARD_NUMBER_LENGTH)

    return f"{number:0{CARD_NUMBER_LENGTH}d}"


def _has_duplicates(values: Iterable[str]) -> bool:
    seen_values: set[str] = set()
    for value in values:
        if value in seen_values:
            return True
        seen_values.add(value)

    return False
