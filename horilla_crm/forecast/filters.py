"""
Filters for the forecast app.

This module defines filter classes used to search and filter forecast records.
"""

from horilla_crm.forecast.models import ForecastTarget, ForecastType
from horilla_generics.filters import HorillaFilterSet


class ForecastTargetFilter(HorillaFilterSet):
    """
    Filter class for ForecastTarget model
    """

    class Meta:
        """Filter options for the ForecastTarget model."""

        model = ForecastTarget
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["target_amount"]


class ForecastTypeFilter(HorillaFilterSet):
    """
    Filter class for ForecastType model
    """

    class Meta:
        """Filter options for the ForecastType model."""

        model = ForecastType
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["name"]
