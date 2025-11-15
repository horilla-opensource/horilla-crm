import logging

import django_filters
from django.db.models import Q

logger = logging.getLogger(__name__)
# Define operator choices by field type
OPERATOR_CHOICES = {
    "text": [
        ("icontains", "Contains"),
        ("exact", "Equals"),
        ("ne", "Not Equals"),
        ("istartswith", "Starts with"),
        ("iendswith", "Ends with"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "number": [
        ("exact", "Equals"),
        ("gt", "Greater than"),
        ("lt", "Less than"),
        ("gte", "Greater than or equal"),
        ("lte", "Less than or equal"),
        ("between", "Between"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "float": [
        ("exact", "Equals"),
        ("gt", "Greater than"),
        ("lt", "Less than"),
        ("gte", "Greater than or equal"),
        ("lte", "Less than or equal"),
        ("between", "Between"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "decimal": [
        ("exact", "Equals"),
        ("gt", "Greater than"),
        ("lt", "Less than"),
        ("gte", "Greater than or equal"),
        ("lte", "Less than or equal"),
        ("between", "Between"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "date": [
        ("exact", "Equals"),
        ("gt", "After"),
        ("lt", "Before"),
        ("between", "Between"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "datetime": [
        ("exact", "Equals"),
        ("gt", "After"),
        ("lt", "Before"),
        ("between", "Between"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "boolean": [("exact", "Equals")],
    "choice": [
        ("exact", "Equals"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
    "other": [
        ("exact", "Equals"),
        ("icontains", "Contains"),
        ("isnull", "Is empty"),
        ("isnotnull", "Is not empty"),
    ],
}


class HorillaFilterSet(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search", label="Search")

    @classmethod
    def get_operators_for_field(cls, field_type):
        """Return appropriate operators for a given field type"""
        return OPERATOR_CHOICES.get(field_type, OPERATOR_CHOICES["other"])

    def filter_queryset(self, queryset):
        """
        Override the default filter_queryset to handle our custom filtering approach.
        Process arrays of fields, operators, and values.
        """
        if hasattr(self, "form") and hasattr(self.form, "cleaned_data"):
            queryset = super().filter_queryset(queryset)

        request = getattr(self, "request", None)
        if not request and hasattr(self, "data") and hasattr(self.data, "_request"):
            request = self.data._request

        if not request:
            return queryset

        fields = self.data.getlist("field", []) or request.GET.getlist("field", [])
        operators = self.data.getlist("operator", []) or request.GET.getlist(
            "operator", []
        )
        values = self.data.getlist("value", []) or request.GET.getlist("value", [])
        start_values = self.data.getlist("start_value", []) or request.GET.getlist(
            "start_value", []
        )
        end_values = self.data.getlist("end_value", []) or request.GET.getlist(
            "end_value", []
        )

        for i, (field, operator) in enumerate(zip(fields, operators)):
            if not field or not operator:
                continue

            try:
                if operator == "ne":
                    value = values[i] if i < len(values) else None
                    if value is not None:
                        queryset = queryset.exclude(**{field: value})

                elif operator == "between":
                    start_value = start_values[i] if i < len(start_values) else None
                    end_value = end_values[i] if i < len(end_values) else None

                    if start_value and end_value:
                        queryset = queryset.filter(
                            **{f"{field}__gte": start_value, f"{field}__lte": end_value}
                        )
                    elif start_value:
                        queryset = queryset.filter(**{f"{field}__gte": start_value})
                    elif end_value:
                        queryset = queryset.filter(**{f"{field}__lte": end_value})

                elif operator == "isnull":
                    queryset = queryset.filter(**{f"{field}__isnull": True})

                elif operator == "isnotnull":
                    queryset = queryset.filter(**{f"{field}__isnull": False})

                else:
                    value = values[i] if i < len(values) else None
                    if value is not None:
                        queryset = queryset.filter(**{f"{field}__{operator}": value})

            except Exception as e:
                logger.error(f"Filter error for {field} {operator}: {e}")

        search_query = self.data.get("search", "") or request.GET.get("search", "")
        if search_query:
            queryset = self.filter_search(queryset, "search", search_query)

        return queryset

    def filter_search(self, queryset, name, value):
        """Handle search across specified fields"""
        search_fields = getattr(self.Meta, "search_fields", [])
        if not value or not search_fields:
            return queryset

        queries = Q()
        for field in search_fields:
            queries |= Q(**{f"{field}__icontains": value})
        return queryset.filter(queries)
