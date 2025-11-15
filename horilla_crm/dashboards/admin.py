"""Admin configuration for dashboards app."""

from django.contrib import admin

from .models import ComponentCriteria, Dashboard, DashboardComponent, DashboardFolder

# Register your dashboards models here.
admin.site.register(Dashboard)
admin.site.register(DashboardComponent)
admin.site.register(ComponentCriteria)
admin.site.register(DashboardFolder)
