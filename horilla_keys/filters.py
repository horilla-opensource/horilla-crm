"""
Filters for the horilla_keys app
"""

import django_filters

from horilla_generics.filters import HorillaFilterSet
from horilla_keys.models import ShortcutKey

# Define your horilla_keys filters here


class ShortKeyFilter(HorillaFilterSet):
    class Meta:
        model = ShortcutKey
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["page"]
