"""Views for loyalty card management."""

from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, CharField, Func, Q, QuerySet, Value, When
from django.db.models.functions import Cast, Coalesce
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from cards.forms import CardGenerationForm
from cards.models import Card, CardStatus
from cards.services import (
    CardGenerationError,
    expire_cards,
    generate_cards,
    refresh_card_usage,
)


@login_required
def card_list(request: HttpRequest) -> HttpResponse:
    """Render a searchable list of loyalty cards."""
    expire_cards()

    query: str = request.GET.get("q", "").strip()
    cards: QuerySet[Card] = _search_cards(query)

    context: dict[str, Any] = {
        "cards": cards,
        "query": query,
        "status_labels": dict(CardStatus.choices),
    }

    return render(request, "cards/card_list.html", context)


@login_required
def card_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Render a loyalty card profile with purchase history."""
    expire_cards()

    card: Card = get_object_or_404(Card, pk=pk)
    refresh_card_usage(card)

    context: dict[str, Any] = {"card": card, "purchases": card.purchases.all()}

    return render(request, "cards/card_detail.html", context)


@login_required
def generate_cards_view(request: HttpRequest) -> HttpResponse:
    """Render and process the loyalty card generation form."""
    if request.method == "POST":
        form: CardGenerationForm = CardGenerationForm(request.POST)
        if form.is_valid():
            series: str = form.cleaned_data["series"]
            count: int = form.cleaned_data["count"]
            duration_months: int = form.get_duration_months()
            try:
                created_cards: list[Card] = generate_cards(
                    series, count, duration_months
                )
            except CardGenerationError as error:
                form.add_error(None, str(error))
            else:
                messages.success(
                    request, f"Generated {len(created_cards)} loyalty card(s)."
                )

                return redirect("cards:list")
    else:
        form = CardGenerationForm()

    return render(request, "cards/card_generate.html", {"form": form})


@require_POST
@login_required
def activate_card(request: HttpRequest, pk: int) -> HttpResponseRedirect:
    """Activate a non-expired loyalty card."""
    expire_cards()

    card: Card = get_object_or_404(Card, pk=pk)
    if card.status == CardStatus.EXPIRED:
        messages.error(request, "Expired loyalty cards cannot be activated.")
    else:
        card.status = CardStatus.ACTIVATED
        card.save(update_fields=["status"])
        messages.success(request, "Loyalty card activated.")

    return _redirect_back(request, card)


@require_POST
@login_required
def deactivate_card(request: HttpRequest, pk: int) -> HttpResponseRedirect:
    """Deactivate a non-expired loyalty card."""
    expire_cards()

    card: Card = get_object_or_404(Card, pk=pk)
    if card.status == CardStatus.EXPIRED:
        messages.error(request, "Expired loyalty cards cannot be deactivated.")
    else:
        card.status = CardStatus.NOT_ACTIVATED
        card.save(update_fields=["status"])
        messages.success(request, "Loyalty card deactivated.")

    return _redirect_back(request, card)


@require_POST
@login_required
def delete_card(request: HttpRequest, pk: int) -> HttpResponseRedirect:
    """Delete a loyalty card."""
    card: Card = get_object_or_404(Card, pk=pk)
    card_identifier: str = str(card)

    card.delete()
    messages.success(request, f"Loyalty card {card_identifier} deleted.")

    return redirect("cards:list")


def _search_cards(query: str) -> QuerySet[Card]:
    cards: QuerySet[Card] = Card.objects.all()
    if not query:
        return cards

    status_query: Q = _build_status_query(query)
    searchable_cards: QuerySet[Card] = cards.annotate(
        issued_text=_format_datetime("issued_at"),
        expires_text=_format_datetime("expires_at"),
        used_text=Coalesce(
            _format_datetime("used_at"),
            Value("", output_field=CharField()),
            output_field=CharField(),
        ),
        amount_text=Cast("amount", output_field=CharField()),
        status_text=Case(
            When(status=CardStatus.NOT_ACTIVATED, then=Value("Not activated")),
            When(status=CardStatus.ACTIVATED, then=Value("Activated")),
            When(status=CardStatus.EXPIRED, then=Value("Expired")),
            default=Value(""),
            output_field=CharField(),
        ),
    )

    return searchable_cards.filter(
        Q(series__icontains=query)
        | Q(number__icontains=query)
        | status_query
        | Q(issued_text__icontains=query)
        | Q(expires_text__icontains=query)
        | Q(used_text__icontains=query)
        | Q(amount_text__icontains=query)
    )


def _build_status_query(query: str) -> Q:
    normalized_query: str = query.strip().replace("_", " ").replace("-", " ").lower()
    normalized_query = " ".join(normalized_query.split())
    status_by_query: dict[str, CardStatus] = {
        "not activated": CardStatus.NOT_ACTIVATED,
        "notactivated": CardStatus.NOT_ACTIVATED,
        "activated": CardStatus.ACTIVATED,
        "expired": CardStatus.EXPIRED,
    }
    status: CardStatus | None = status_by_query.get(normalized_query)
    if status is not None:
        return Q(status=status)

    return Q(status__icontains=query) | Q(status_text__icontains=query)


def _format_datetime(field_name: str) -> Func:
    return Func(
        field_name,
        Value("YYYY-MM-DD HH24:MI:SS"),
        function="TO_CHAR",
        output_field=CharField(),
    )


def _redirect_back(request: HttpRequest, card: Card) -> HttpResponseRedirect:
    next_url: str | None = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect(reverse("cards:detail", kwargs={"pk": card.pk}))
