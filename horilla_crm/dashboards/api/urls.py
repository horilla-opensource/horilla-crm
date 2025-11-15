"""
URL patterns for horilla_crm.dashboards API
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from horilla_crm.dashboards.api.views import (
    ComponentCriteriaViewSet,
    DashboardComponentViewSet,
    DashboardFolderViewSet,
    DashboardViewSet,
)

router = DefaultRouter()
router.register(r"dashboard-folders", DashboardFolderViewSet)
router.register(r"dashboards", DashboardViewSet)
router.register(r"dashboard-components", DashboardComponentViewSet)
router.register(r"component-criteria", ComponentCriteriaViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
