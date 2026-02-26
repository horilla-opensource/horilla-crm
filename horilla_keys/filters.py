"""
Filters for the horilla_keys app.
"""

from horilla_generics.filters import HorillaFilterSet
from horilla_keys.models import ShortcutKey


class ShortKeyFilter(HorillaFilterSet):
    """
    Filter set for ShortcutKey model.

    Used to filter, search, and manage shortcut key records
    across the application.
    """

    class Meta:
        """
        Meta configuration for ShortKeyFilter.
        """

        model = ShortcutKey
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["page"]
