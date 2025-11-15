"""Filters for dashboards app."""

from horilla_generics.filters import HorillaFilterSet

from .models import Dashboard


class DashboardFilter(HorillaFilterSet):
    """Dashboard Filter"""

    class Meta:
        """Meta class for DashboardFilter"""

        model = Dashboard
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]
