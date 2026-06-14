"""Signal handlers for loyalty cards."""

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from cards.models import Card, Purchase
from cards.services import refresh_card_usage

PREVIOUS_CARD_ID_ATTR: str = "_previous_card_id"


@receiver(pre_save, sender=Purchase)
def remember_previous_purchase_card(
    sender: type[Purchase], instance: Purchase, **kwargs: object
) -> None:
    """Store the previous card before a purchase is saved."""
    previous_card_id: int | None = None
    if instance.pk is not None:
        previous_card_id = (
            Purchase.objects.filter(pk=instance.pk)
            .values_list("card_id", flat=True)
            .first()
        )

    setattr(instance, PREVIOUS_CARD_ID_ATTR, previous_card_id)


@receiver(post_save, sender=Purchase)
def update_card_after_purchase_save(
    sender: type[Purchase], instance: Purchase, **kwargs: object
) -> None:
    """Refresh loyalty card usage fields after a purchase is saved."""
    previous_card_id: int | None = getattr(instance, PREVIOUS_CARD_ID_ATTR, None)

    refresh_card_usage(instance.card)
    if previous_card_id is not None and previous_card_id != instance.card_id:
        previous_card: Card | None = Card.objects.filter(pk=previous_card_id).first()
        if previous_card is not None:
            refresh_card_usage(previous_card)


@receiver(post_delete, sender=Purchase)
def update_card_after_purchase_delete(
    sender: type[Purchase], instance: Purchase, **kwargs: object
) -> None:
    """Refresh loyalty card usage fields after a purchase is deleted."""
    refresh_card_usage(instance.card)
