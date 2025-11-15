"""
API views for horilla_crm.timeline models

This module mirrors horilla_core/accounts API patterns including search, filtering,
bulk update, bulk delete, permissions, and documentation.
"""

from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from horilla_core.api.docs import BULK_DELETE_DOCS, BULK_UPDATE_DOCS, SEARCH_FILTER_DOCS
from horilla_core.api.mixins import BulkOperationsMixin, SearchFilterMixin
from horilla_core.api.permissions import IsCompanyMember
from horilla_crm.timeline.api.docs import (
    USER_AVAILABILITY_CREATE_DOCS,
    USER_AVAILABILITY_CURRENT_DOCS,
    USER_AVAILABILITY_DETAIL_DOCS,
    USER_AVAILABILITY_LIST_DOCS,
    USER_CALENDAR_PREFERENCE_CREATE_DOCS,
    USER_CALENDAR_PREFERENCE_DETAIL_DOCS,
    USER_CALENDAR_PREFERENCE_LIST_DOCS,
)
from horilla_crm.timeline.api.serializers import (
    UserAvailabilitySerializer,
    UserCalendarPreferenceSerializer,
)
from horilla_crm.timeline.models import UserAvailability, UserCalendarPreference

# Common Swagger parameter for search
search_param = openapi.Parameter(
    "search",
    openapi.IN_QUERY,
    description="Search term for full-text search across relevant fields",
    type=openapi.TYPE_STRING,
)

bulk_update_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "ids": openapi.Schema(
            type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)
        ),
        "filters": openapi.Schema(type=openapi.TYPE_OBJECT, additional_properties=True),
        "data": openapi.Schema(type=openapi.TYPE_OBJECT, additional_properties=True),
    },
    required=["data"],
)

bulk_delete_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "ids": openapi.Schema(
            type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)
        ),
        "filters": openapi.Schema(type=openapi.TYPE_OBJECT, additional_properties=True),
    },
)


class UserCalendarPreferenceViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for UserCalendarPreference model"""

    queryset = UserCalendarPreference.objects.all()
    serializer_class = UserCalendarPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    # Enable search across common fields
    search_fields = [
        "user__username",
        "calendar_type",
        "color",
    ]

    # Filterable fields including core fields
    filterset_fields = [
        "user",
        "calendar_type",
        "is_selected",
        "color",
        "company",
        "created_by",
        "is_active",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=USER_CALENDAR_PREFERENCE_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        """List preferences with search and filter capabilities"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=USER_CALENDAR_PREFERENCE_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific preference"""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=USER_CALENDAR_PREFERENCE_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        """Create a new preference"""
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=bulk_update_body, operation_description=BULK_UPDATE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Update multiple preferences in a single request"""
        return super().bulk_update(request)

    @swagger_auto_schema(
        request_body=bulk_delete_body, operation_description=BULK_DELETE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """Delete multiple preferences in a single request"""
        return super().bulk_delete(request)


class UserAvailabilityViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for UserAvailability model"""

    queryset = UserAvailability.objects.all()
    serializer_class = UserAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    # Enable search across common fields
    search_fields = [
        "user__username",
        "reason",
    ]

    # Filterable fields including core fields
    filterset_fields = [
        "user",
        "from_datetime",
        "to_datetime",
        "reason",
        "company",
        "created_by",
        "is_active",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=USER_AVAILABILITY_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        """List availability records with search and filter capabilities"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=USER_AVAILABILITY_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific availability record"""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=USER_AVAILABILITY_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        """Create a new availability record"""
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=bulk_update_body, operation_description=BULK_UPDATE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Update multiple availability records in a single request"""
        return super().bulk_update(request)

    @swagger_auto_schema(
        request_body=bulk_delete_body, operation_description=BULK_DELETE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """Delete multiple availability records in a single request"""
        return super().bulk_delete(request)

    @swagger_auto_schema(operation_description=USER_AVAILABILITY_CURRENT_DOCS)
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        """Get current unavailability periods, optionally filtered by user_id"""
        user_id = request.query_params.get("user_id")
        now = timezone.now()
        queryset = self.get_queryset().filter(
            from_datetime__lte=now, to_datetime__gte=now
        )
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
