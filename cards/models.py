"""Database models for loyalty cards and purchases."""

from decimal import Decimal

from django.db import models


class CardStatus(models.TextChoices):
    """Available card lifecycle statuses."""

    NOT_ACTIVATED = "not_activated", "Not activated"
    ACTIVATED = "activated", "Activated"
    EXPIRED = "expired", "Expired"


class Card(models.Model):
    """A loyalty card."""

    series = models.CharField(max_length=32, db_index=True)
    number = models.CharField(max_length=32)
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    status = models.CharField(
        max_length=20,
        choices=CardStatus.choices,
        default=CardStatus.NOT_ACTIVATED,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["series", "number"],
                name="unique_card_number_per_series",
            ),
        ]
        ordering = ["-issued_at", "series", "number"]

    def __str__(self) -> str:
        """Return a readable card identifier."""
        return f"{self.series}-{self.number}"

    @property
    def is_expired(self) -> bool:
        """Return whether the card is expired by status."""
        return self.status == CardStatus.EXPIRED


class Purchase(models.Model):
    """A purchase made with a loyalty card."""

    card = models.ForeignKey(Card, related_name="purchases", on_delete=models.CASCADE)
    purchased_at = models.DateTimeField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-purchased_at"]

    def __str__(self) -> str:
        """Return a readable purchase representation."""
        return f"{self.card} purchase for {self.amount}"
