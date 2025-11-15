"""
URL patterns for horilla_crm.activity API
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from horilla_crm.activity.api.views import ActivityViewSet

router = DefaultRouter()
router.register(r"activities", ActivityViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
