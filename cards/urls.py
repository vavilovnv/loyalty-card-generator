"""URL patterns for loyalty card management."""

from django.urls import path

from cards import views

app_name = "cards"

urlpatterns = [
    path("", views.card_list, name="list"),
    path("generate/", views.generate_cards_view, name="generate"),
    path("<int:pk>/", views.card_detail, name="detail"),
    path("<int:pk>/activate/", views.activate_card, name="activate"),
    path("<int:pk>/deactivate/", views.deactivate_card, name="deactivate"),
    path("<int:pk>/delete/", views.delete_card, name="delete"),
]
