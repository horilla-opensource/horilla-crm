"""
URL patterns for horilla_keys API
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from horilla_keys.api.views import ShortcutKeyViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r"shortcut-keys", ShortcutKeyViewSet)


# The API URLs are now determined automatically by the router
urlpatterns = [
    # Include the router URLs
    path("", include(router.urls)),
]
