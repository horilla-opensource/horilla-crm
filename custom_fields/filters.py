from horilla.contrib.generics.filters import HorillaFilterSet

from .models import CustomFieldDefinition


class CustomFieldDefinitionFilter(HorillaFilterSet):
    class Meta:
        model = CustomFieldDefinition
        fields = ["content_type", "field_type", "is_required"]
        search_fields = ["name"]
