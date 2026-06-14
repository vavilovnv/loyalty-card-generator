"""Signal handlers for loyalty cards."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cards.models import Purchase
from cards.services import refresh_card_usage


@receiver(post_save, sender=Purchase)
def update_card_after_purchase_save(
    sender: type[Purchase], instance: Purchase, **kwargs: object
) -> None:
    """Refresh loyalty card usage fields after a purchase is saved."""
    refresh_card_usage(instance.card)


@receiver(post_delete, sender=Purchase)
def update_card_after_purchase_delete(
    sender: type[Purchase], instance: Purchase, **kwargs: object
) -> None:
    """Refresh loyalty card usage fields after a purchase is deleted."""
    refresh_card_usage(instance.card)
