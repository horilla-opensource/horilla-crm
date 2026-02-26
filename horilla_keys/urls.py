"""
URLs for the horilla_keys app
"""

from django.urls import path

from . import views

app_name = "horilla_keys"

urlpatterns = [
    path("short-key-view/", views.ShortKeyView.as_view(), name="short_key_view"),
    path("short-key-nav/", views.ShortKeyNavbar.as_view(), name="short_key_nav"),
    path("short-key-list/", views.ShortKeyListView.as_view(), name="short_key_list"),
    path(
        "short-key-create/", views.ShortKeyFormView.as_view(), name="short_key_create"
    ),
    path(
        "short-key-update/<int:pk>/",
        views.ShortKeyFormView.as_view(),
        name="short_key_update",
    ),
    path(
        "short-key-delete/<int:pk>/",
        views.ShortcutKeyDeleteView.as_view(),
        name="short_key_delete",
    ),
    path("short-key-data/", views.ShortKeyDataView.as_view(), name="short_key_data"),
]
