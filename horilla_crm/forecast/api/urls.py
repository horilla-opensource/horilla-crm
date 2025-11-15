"""
URL patterns for horilla_crm.forecast API
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from horilla_crm.forecast.api.views import (
    ForecastTargetUserViewSet,
    ForecastTargetViewSet,
    ForecastTypeViewSet,
    ForecastViewSet,
)

router = DefaultRouter()
router.register(r"forecast-types", ForecastTypeViewSet)
router.register(r"forecasts", ForecastViewSet)
router.register(r"forecast-targets", ForecastTargetViewSet)
router.register(r"forecast-target-users", ForecastTargetUserViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
