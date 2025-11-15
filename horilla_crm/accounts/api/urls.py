"""
URL patterns for horilla_crm.accounts API
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from horilla_crm.accounts.api.views import (
    AccountViewSet,
    PartnerAccountRelationshipViewSet,
)

router = DefaultRouter()
router.register(r"accounts", AccountViewSet)
router.register(r"partner-account-relationships", PartnerAccountRelationshipViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
