"""
API views for horilla_crm.dashboards models

Mirrors horilla_core and accounts API patterns including search, filtering,
bulk update, bulk delete, permissions, and documentation.
"""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from horilla_core.api.docs import BULK_DELETE_DOCS, BULK_UPDATE_DOCS, SEARCH_FILTER_DOCS
from horilla_core.api.mixins import BulkOperationsMixin, SearchFilterMixin
from horilla_core.api.permissions import IsCompanyMember
from horilla_crm.dashboards.api.docs import (
    COMPONENT_CRITERIA_CREATE_DOCS,
    COMPONENT_CRITERIA_DETAIL_DOCS,
    COMPONENT_CRITERIA_LIST_DOCS,
    DASHBOARD_COMPONENT_CREATE_DOCS,
    DASHBOARD_COMPONENT_DETAIL_DOCS,
    DASHBOARD_COMPONENT_LIST_DOCS,
    DASHBOARD_CREATE_DOCS,
    DASHBOARD_DETAIL_DOCS,
    DASHBOARD_FOLDER_CREATE_DOCS,
    DASHBOARD_FOLDER_DETAIL_DOCS,
    DASHBOARD_FOLDER_LIST_DOCS,
    DASHBOARD_LIST_DOCS,
)
from horilla_crm.dashboards.api.serializers import (
    ComponentCriteriaSerializer,
    DashboardComponentSerializer,
    DashboardFolderSerializer,
    DashboardSerializer,
)
from horilla_crm.dashboards.models import (
    ComponentCriteria,
    Dashboard,
    DashboardComponent,
    DashboardFolder,
)

# Define common Swagger parameters and bodies consistent with horilla_core
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


class DashboardFolderViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for DashboardFolder model"""

    queryset = DashboardFolder.objects.all()
    serializer_class = DashboardFolderSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    search_fields = [
        "name",
        "description",
    ]

    filterset_fields = [
        "folder_owner",
        "parent_folder",
        "is_active",
        "created_by",
        "company",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=DASHBOARD_FOLDER_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=DASHBOARD_FOLDER_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=DASHBOARD_FOLDER_CREATE_DOCS)
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


class DashboardViewSet(SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet):
    """ViewSet for Dashboard model"""

    queryset = Dashboard.objects.all()
    serializer_class = DashboardSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    search_fields = [
        "name",
        "description",
        "folder__name",
    ]

    filterset_fields = [
        "dashboard_owner",
        "folder",
        "is_default",
        "is_active",
        "created_by",
        "company",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=DASHBOARD_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=DASHBOARD_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=DASHBOARD_CREATE_DOCS)
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


class DashboardComponentViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for DashboardComponent model"""

    queryset = DashboardComponent.objects.all()
    serializer_class = DashboardComponentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    search_fields = [
        "name",
        "module",
        "metric_type",
        "chart_type",
    ]

    filterset_fields = [
        "dashboard",
        "component_type",
        "chart_type",
        "module",
        "metric_type",
        "is_active",
        "component_owner",
        "created_by",
        "company",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=DASHBOARD_COMPONENT_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=DASHBOARD_COMPONENT_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=DASHBOARD_COMPONENT_CREATE_DOCS)
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


class ComponentCriteriaViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for ComponentCriteria model"""

    queryset = ComponentCriteria.objects.all()
    serializer_class = ComponentCriteriaSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    search_fields = [
        "field",
        "value",
    ]

    filterset_fields = [
        "component",
        "operator",
        "sequence",
        "is_active",
        "created_by",
        "company",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=COMPONENT_CRITERIA_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=COMPONENT_CRITERIA_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=COMPONENT_CRITERIA_CREATE_DOCS)
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
