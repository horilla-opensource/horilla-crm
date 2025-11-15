"""
API mixins for implementing advanced features like search, filtering, bulk update, and bulk delete
"""

from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response


class SearchFilterMixin:
    """
    Mixin to add search and filtering capabilities to ViewSets
    """

    search_fields = []  # Fields to search in, should be overridden in the ViewSet
    filterset_fields = []  # Fields to filter by, should be overridden in the ViewSet

    def get_queryset(self):
        """
        Override get_queryset to add search and filtering capabilities
        """
        queryset = super().get_queryset()

        # Apply search if search parameter is provided
        search_term = self.request.query_params.get("search", None)
        if search_term and self.search_fields:
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f"{field}__icontains": search_term})
            queryset = queryset.filter(q_objects)

        # Apply filtering for each filter parameter
        for param, value in self.request.query_params.items():
            if param in self.filterset_fields and value:
                queryset = queryset.filter(**{param: value})

        return queryset


class BulkOperationsMixin:
    """
    Mixin to add bulk update and bulk delete capabilities to ViewSets
    with support for filtering operations
    """

    def _apply_filters_to_queryset(self, queryset, filters):
        """
        Apply filters to queryset based on provided filter criteria

        Filter format:
        {
            "field1": "value1",
            "field2__contains": "value2",
            "field3__in": [1, 2, 3],
            ...
        }
        """
        if not filters:
            return queryset

        try:
            return queryset.filter(**filters)
        except Exception as e:
            # Log the error or handle invalid filter fields
            return queryset

    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """
        Update multiple instances in a single request with optional filtering

        Expected request format:
        {
            "ids": [1, 2, 3, ...],  # Optional if filters are provided
            "filters": {            # Optional if ids are provided
                "field1": "value1",
                "field2__contains": "value2",
                ...
            },
            "data": {
                "field1": "value1",
                "field2": "value2",
                ...
            }
        }
        """
        ids = request.data.get("ids", [])
        filters = request.data.get("filters", {})
        update_data = request.data.get("data", {})

        if not update_data:
            return Response(
                {"error": "'data' is required for bulk update"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not ids and not filters:
            return Response(
                {"error": "Either 'ids' or 'filters' must be provided for bulk update"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Start with the base queryset
        queryset = self.get_queryset()

        # Apply ID filtering if provided
        if ids:
            queryset = queryset.filter(id__in=ids)

        # Apply additional filters if provided
        if filters:
            queryset = self._apply_filters_to_queryset(queryset, filters)

        # Check if any records match the criteria
        record_count = queryset.count()
        if record_count == 0:
            return Response(
                {"error": "No records match the provided criteria"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Perform bulk update within a transaction
        with transaction.atomic():
            updated_count = queryset.update(**update_data)

        return Response(
            {
                "message": f"Successfully updated {updated_count} records",
                "updated_count": updated_count,
            }
        )

    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """
        Delete multiple instances in a single request with optional filtering

        Expected request format:
        {
            "ids": [1, 2, 3, ...],  # Optional if filters are provided
            "filters": {            # Optional if ids are provided
                "field1": "value1",
                "field2__contains": "value2",
                ...
            }
        }

        Or for simple ID-based deletion:
        [1, 2, 3, ...]
        """
        # Handle direct array format for backward compatibility
        if isinstance(request.data, list):
            ids = request.data
            filters = {}
        else:
            ids = request.data.get("ids", [])
            filters = request.data.get("filters", {})

        if not ids and not filters:
            return Response(
                {"error": "Either 'ids' or 'filters' must be provided for bulk delete"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Start with the base queryset
        queryset = self.get_queryset()

        # Apply ID filtering if provided
        if ids:
            queryset = queryset.filter(id__in=ids)

        # Apply additional filters if provided
        if filters:
            queryset = self._apply_filters_to_queryset(queryset, filters)

        # Check if any records match the criteria
        record_count = queryset.count()
        if record_count == 0:
            return Response(
                {"error": "No records match the provided criteria"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Perform bulk delete within a transaction
        with transaction.atomic():
            deleted_count, _ = queryset.delete()

        return Response(
            {
                "message": f"Successfully deleted {deleted_count} records",
                "deleted_count": deleted_count,
            }
        )
