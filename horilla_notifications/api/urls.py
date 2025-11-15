"""
URL configuration for horilla_notifications API
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from horilla_notifications.api.views import NotificationViewSet

router = DefaultRouter()
router.register(r"notifications", NotificationViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
