"""
URL patterns for horilla_crm.contacts API
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from horilla_crm.contacts.api.views import ContactViewSet

router = DefaultRouter()
router.register(r"contacts", ContactViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
