"""View tests for the cards application."""

from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from cards.models import Card, CardStatus
from cards.tests.factories import create_card


class CardListViewTests(TestCase):
    """Tests for the loyalty card list view."""

    def test_card_list_expires_outdated_cards_before_rendering(self) -> None:
        # -- Arrange --
        card = create_card(
            expires_delta=timedelta(days=-1),
            status=CardStatus.ACTIVATED,
        )

        # -- Act --
        response = self.client.get(reverse("cards:list"))

        # -- Assert --
        card.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(card.status, CardStatus.EXPIRED)

    def test_card_list_filters_by_status_text(self) -> None:
        # -- Arrange --
        activated_card = create_card(
            number="000000000020",
            status=CardStatus.ACTIVATED,
        )
        create_card(number="000000000021", status=CardStatus.NOT_ACTIVATED)

        # -- Act --
        response = self.client.get(reverse("cards:list"), {"q": "activated"})

        # -- Assert --
        self.assertEqual(response.status_code, 200)
        self.assertIn(activated_card, response.context["cards"])


class CardDetailViewTests(TestCase):
    """Tests for the loyalty card detail view."""

    def test_card_detail_refreshes_usage_before_rendering(self) -> None:
        # -- Arrange --
        card = create_card()

        # -- Act --
        response = self.client.get(reverse("cards:detail", kwargs={"pk": card.pk}))

        # -- Assert --
        card.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(card.amount, 0)
        self.assertIsNone(card.used_at)


class GenerateCardsViewTests(TestCase):
    """Tests for the loyalty card generation view."""

    def test_get_generate_view_renders_form(self) -> None:
        # -- Arrange --
        url = reverse("cards:generate")

        # -- Act --
        response = self.client.get(url)

        # -- Assert --
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_post_generate_view_creates_cards_and_redirects(self) -> None:
        # -- Arrange --
        url = reverse("cards:generate")

        # -- Act --
        response = self.client.post(
            url,
            data={"series": " vip ", "count": "2", "duration_months": "1"},
        )

        # -- Assert --
        self.assertRedirects(response, reverse("cards:list"))
        self.assertEqual(Card.objects.filter(series="VIP").count(), 2)
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("Generated 2 loyalty card(s).", messages)

    def test_post_generate_view_renders_form_errors(self) -> None:
        # -- Arrange --
        url = reverse("cards:generate")

        # -- Act --
        response = self.client.post(
            url,
            data={"series": "VIP", "count": "0", "duration_months": "1"},
        )

        # -- Assert --
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Card.objects.count(), 0)
        self.assertIn("count", response.context["form"].errors)


class CardStatusActionViewTests(TestCase):
    """Tests for card activation and deactivation views."""

    def test_activate_card_sets_status_and_redirects_to_detail(self) -> None:
        # -- Arrange --
        card = create_card()

        # -- Act --
        response = self.client.post(reverse("cards:activate", kwargs={"pk": card.pk}))

        # -- Assert --
        card.refresh_from_db()
        self.assertRedirects(response, reverse("cards:detail", kwargs={"pk": card.pk}))
        self.assertEqual(card.status, CardStatus.ACTIVATED)

    def test_activate_card_uses_next_redirect_when_provided(self) -> None:
        # -- Arrange --
        card = create_card()

        # -- Act --
        response = self.client.post(
            reverse("cards:activate", kwargs={"pk": card.pk}),
            data={"next": reverse("cards:list")},
        )

        # -- Assert --
        self.assertRedirects(
            response, reverse("cards:list"), fetch_redirect_response=False
        )

    def test_activate_card_keeps_expired_card_expired(self) -> None:
        # -- Arrange --
        card = create_card(
            expires_delta=timedelta(days=-1),
            status=CardStatus.ACTIVATED,
        )

        # -- Act --
        response = self.client.post(reverse("cards:activate", kwargs={"pk": card.pk}))

        # -- Assert --
        card.refresh_from_db()
        self.assertRedirects(response, reverse("cards:detail", kwargs={"pk": card.pk}))
        self.assertEqual(card.status, CardStatus.EXPIRED)

    def test_deactivate_card_sets_status(self) -> None:
        # -- Arrange --
        card = create_card(status=CardStatus.ACTIVATED)

        # -- Act --
        response = self.client.post(reverse("cards:deactivate", kwargs={"pk": card.pk}))

        # -- Assert --
        card.refresh_from_db()
        self.assertRedirects(response, reverse("cards:detail", kwargs={"pk": card.pk}))
        self.assertEqual(card.status, CardStatus.NOT_ACTIVATED)


class DeleteCardViewTests(TestCase):
    """Tests for loyalty card deletion."""

    def test_delete_card_removes_card_and_redirects_to_list(self) -> None:
        # -- Arrange --
        card = create_card()

        # -- Act --
        response = self.client.post(reverse("cards:delete", kwargs={"pk": card.pk}))

        # -- Assert --
        self.assertRedirects(response, reverse("cards:list"))
        self.assertFalse(Card.objects.filter(pk=card.pk).exists())
