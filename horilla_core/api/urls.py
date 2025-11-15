"""
URL patterns for horilla_core API
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from horilla_core.api.views import (
    BusinessHourViewSet,
    CompanyViewSet,
    CustomerRoleViewSet,
    DepartmentViewSet,
    HolidayViewSet,
    HorillaAttachmentViewSet,
    HorillaUserViewSet,
    ImportHistoryViewSet,
    PartnerRoleViewSet,
    RoleViewSet,
    ScoringCriterionViewSet,
    ScoringRuleViewSet,
    TeamRoleViewSet,
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r"companies", CompanyViewSet)
router.register(r"departments", DepartmentViewSet)
router.register(r"roles", RoleViewSet)
router.register(r"users", HorillaUserViewSet)

router.register(r"business-hours", BusinessHourViewSet)
router.register(r"team-roles", TeamRoleViewSet)
router.register(r"customer-roles", CustomerRoleViewSet)
router.register(r"partner-roles", PartnerRoleViewSet)
router.register(r"scoring-rules", ScoringRuleViewSet)
router.register(r"scoring-criteria", ScoringCriterionViewSet)
router.register(r"import-histories", ImportHistoryViewSet)
router.register(r"attachments", HorillaAttachmentViewSet)
router.register(r"holidays", HolidayViewSet)


# The API URLs are now determined automatically by the router
urlpatterns = [
    # JWT Authentication endpoints
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # Include the router URLs
    path("", include(router.urls)),
]
