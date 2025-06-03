from django.urls import path

from .views import recipe_short_link_redirect

urlpatterns = [
    path(
        "s/<int:recipe_id>/",
        recipe_short_link_redirect,
        name="recipe-short-link-redirect",
    ),
]
