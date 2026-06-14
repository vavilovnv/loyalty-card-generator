from django.apps import AppConfig


class CardsConfig(AppConfig):
    """Application configuration for the loyalty cards app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "cards"

    def ready(self) -> None:
        """Register loyalty card signal handlers."""
        import cards.signals  # noqa: F401
