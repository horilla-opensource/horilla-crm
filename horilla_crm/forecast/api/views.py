"""
API views for horilla_crm.forecast models

This module mirrors horilla_core and accounts API patterns including search, filtering,
bulk update, bulk delete, permissions, and documentation.
"""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from horilla_core.api.docs import BULK_DELETE_DOCS, BULK_UPDATE_DOCS, SEARCH_FILTER_DOCS
from horilla_core.api.mixins import BulkOperationsMixin, SearchFilterMixin
from horilla_core.api.permissions import IsCompanyMember
from horilla_crm.forecast.api.docs import (
    FORECAST_CREATE_DOCS,
    FORECAST_DETAIL_DOCS,
    FORECAST_LIST_DOCS,
    FORECAST_TARGET_CREATE_DOCS,
    FORECAST_TARGET_DETAIL_DOCS,
    FORECAST_TARGET_LIST_DOCS,
    FORECAST_TARGET_USER_CREATE_DOCS,
    FORECAST_TARGET_USER_DETAIL_DOCS,
    FORECAST_TARGET_USER_LIST_DOCS,
    FORECAST_TYPE_CREATE_DOCS,
    FORECAST_TYPE_DETAIL_DOCS,
    FORECAST_TYPE_LIST_DOCS,
)
from horilla_crm.forecast.api.serializers import (
    ForecastSerializer,
    ForecastTargetSerializer,
    ForecastTargetUserSerializer,
    ForecastTypeSerializer,
)
from horilla_crm.forecast.models import (
    Forecast,
    ForecastTarget,
    ForecastTargetUser,
    ForecastType,
)

# Define common Swagger parameters and bodies consistent with horilla_core
search_param = openapi.Parameter(
    "search",
    openapi.IN_QUERY,
    description="Search term for full-text search across relevant fields",
    type=openapi.TYPE_STRING,
)

filter_param = openapi.Parameter(
    "filter",
    openapi.IN_QUERY,
    description="Filter parameters in format field=value",
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


class ForecastTypeViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for ForecastType model"""

    queryset = ForecastType.objects.all()
    serializer_class = ForecastTypeSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    search_fields = [
        "name",
        "description",
    ]

    filterset_fields = [
        "forecast_type",
        "include_pipeline",
        "include_best_case",
        "include_commit",
        "include_closed",
        "created_by",
        "company",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=FORECAST_TYPE_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=FORECAST_TYPE_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=FORECAST_TYPE_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=bulk_update_body, operation_description=BULK_UPDATE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        return super().bulk_update(request)

    @swagger_auto_schema(
        request_body=bulk_delete_body, operation_description=BULK_DELETE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        return super().bulk_delete(request)


class ForecastViewSet(SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet):
    """ViewSet for Forecast model"""

    queryset = Forecast.objects.all()
    serializer_class = ForecastSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    search_fields = [
        "name",
        "owner__first_name",
        "owner__last_name",
        "owner__email",
    ]

    filterset_fields = [
        "forecast_type",
        "period",
        "quarter",
        "fiscal_year",
        "owner",
        "status",
        "created_by",
        "company",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=FORECAST_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=FORECAST_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=FORECAST_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=bulk_update_body, operation_description=BULK_UPDATE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        return super().bulk_update(request)

    @swagger_auto_schema(
        request_body=bulk_delete_body, operation_description=BULK_DELETE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        return super().bulk_delete(request)


class ForecastTargetViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for ForecastTarget model"""

    queryset = ForecastTarget.objects.all()
    serializer_class = ForecastTargetSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    search_fields = [
        "assigned_to__first_name",
        "assigned_to__last_name",
        "assigned_to__email",
        "forcasts_type__name",
    ]

    filterset_fields = [
        "assigned_to",
        "role",
        "forcasts_type",
        "period",
        "created_by",
        "company",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=FORECAST_TARGET_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=FORECAST_TARGET_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=FORECAST_TARGET_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=bulk_update_body, operation_description=BULK_UPDATE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        return super().bulk_update(request)

    @swagger_auto_schema(
        request_body=bulk_delete_body, operation_description=BULK_DELETE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        return super().bulk_delete(request)


class ForecastTargetUserViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for ForecastTargetUser model"""

    queryset = ForecastTargetUser.objects.all()
    serializer_class = ForecastTargetUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    search_fields = [
        "user__first_name",
        "user__last_name",
        "user__email",
        "forecast_target__assigned_to__email",
    ]

    filterset_fields = [
        "forecast_target",
        "user",
        "is_active",
        "created_by",
        "company",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=FORECAST_TARGET_USER_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=FORECAST_TARGET_USER_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=FORECAST_TARGET_USER_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=bulk_update_body, operation_description=BULK_UPDATE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        return super().bulk_update(request)

    @swagger_auto_schema(
        request_body=bulk_delete_body, operation_description=BULK_DELETE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        return super().bulk_delete(request)
