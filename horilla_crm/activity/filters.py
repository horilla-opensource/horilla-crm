"""
filters module for Activity model to enable filtering based on various fields.
"""

from horilla_crm.activity.models import Activity
from horilla_generics.filters import HorillaFilterSet


class ActivityFilter(HorillaFilterSet):
    """
    ActivityFilter class for filtering Activity model instances.
    """

    class Meta:
        """
        meta class for ActivityFilter
        """

        model = Activity
        fields = "__all__"
        exclude = ["additional_info", "id"]
        search_fields = ["subject", "activity_type"]
