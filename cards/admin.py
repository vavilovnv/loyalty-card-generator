"""Admin configuration for the cards app."""

from django.contrib import admin

from cards.models import Card, Purchase


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    """Admin interface for loyalty cards."""

    list_display = (
        "series",
        "number",
        "issued_at",
        "expires_at",
        "used_at",
        "balance",
        "status",
    )
    list_filter = ("status", "series")
    search_fields = ("series", "number")
    ordering = ("-issued_at",)

    @admin.display(description="Balance")
    def balance(self, obj: Card) -> object:
        """Return the loyalty card balance for admin display."""
        return obj.amount


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    """Admin interface for purchases."""

    list_display = ("card", "purchased_at", "amount", "description")
    list_filter = ("purchased_at",)
    search_fields = ("card__series", "card__number", "description")
