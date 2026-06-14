"""Expire outdated loyalty cards."""

from django.core.management.base import BaseCommand

from cards.services import expire_cards


class Command(BaseCommand):
    """Mark outdated loyalty cards as expired."""

    help = "Mark outdated non-expired loyalty cards as expired."

    def handle(self, *args: object, **options: object) -> None:
        """Execute the command."""
        updated_count: int = expire_cards()
        self.stdout.write(
            self.style.SUCCESS(f"Expired {updated_count} loyalty card(s).")
        )
