"""
URL patterns for horilla_crm.timeline API
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from horilla_crm.timeline.api.views import (
    UserAvailabilityViewSet,
    UserCalendarPreferenceViewSet,
)

router = DefaultRouter()
router.register(r"user-calendar-preferences", UserCalendarPreferenceViewSet)
router.register(r"user-availabilities", UserAvailabilityViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
