"""Test factories for the cards application."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from cards.models import Card, CardStatus, Purchase


def create_card(
    *,
    series: str = "A",
    number: str = "000000000001",
    expires_delta: timedelta = timedelta(days=30),
    status: CardStatus = CardStatus.NOT_ACTIVATED,
    amount: Decimal = Decimal("0.00"),
) -> Card:
    """Create a loyalty card for tests."""
    issued_at = timezone.now()

    return Card.objects.create(
        series=series,
        number=number,
        issued_at=issued_at,
        expires_at=issued_at + expires_delta,
        amount=amount,
        status=status,
    )


def create_purchase(
    *,
    card: Card,
    amount: Decimal = Decimal("10.00"),
    purchased_delta: timedelta = timedelta(days=0),
    description: str = "",
) -> Purchase:
    """Create a purchase for tests."""
    return Purchase.objects.create(
        card=card,
        amount=amount,
        purchased_at=timezone.now() + purchased_delta,
        description=description,
    )
