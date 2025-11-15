"""Django admin configuration for forecast  app."""

from django.contrib import admin

from horilla_crm.forecast.models import (
    Forecast,
    ForecastCondition,
    ForecastTarget,
    ForecastTargetUser,
    ForecastType,
)

admin.site.register(ForecastType)
admin.site.register(Forecast)
admin.site.register(ForecastTarget)
admin.site.register(ForecastTargetUser)
admin.site.register(ForecastCondition)
