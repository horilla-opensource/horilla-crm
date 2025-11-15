"""
API views for horilla_crm.reports models

This module mirrors horilla_core/accounts API patterns including search, filtering,
bulk update, bulk delete, permissions, and documentation.
"""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, viewsets

from horilla_core.api.docs import BULK_DELETE_DOCS, BULK_UPDATE_DOCS, SEARCH_FILTER_DOCS
from horilla_core.api.mixins import BulkOperationsMixin, SearchFilterMixin
from horilla_core.api.permissions import IsCompanyMember
from horilla_crm.reports.api.docs import (
    REPORT_CREATE_DOCS,
    REPORT_DETAIL_DOCS,
    REPORT_FOLDER_CREATE_DOCS,
    REPORT_FOLDER_DETAIL_DOCS,
    REPORT_FOLDER_LIST_DOCS,
    REPORT_LIST_DOCS,
)
from horilla_crm.reports.api.serializers import ReportFolderSerializer, ReportSerializer
from horilla_crm.reports.models import Report, ReportFolder

# Common Swagger parameter for search
search_param = openapi.Parameter(
    "search",
    openapi.IN_QUERY,
    description="Search term for full-text search across relevant fields",
    type=openapi.TYPE_STRING,
)


class ReportFolderViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for ReportFolder model"""

    queryset = ReportFolder.objects.all()
    serializer_class = ReportFolderSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    # Search across common folder fields
    search_fields = [
        "name",
    ]

    # Filtering on key fields and common core fields
    filterset_fields = [
        "is_favourite",
        "report_folder_owner",
        "parent",
        "company",
        "created_by",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=REPORT_FOLDER_LIST_DOCS + "\n\n" + SEARCH_FILTER_DOCS,
    )
    def list(self, request, *args, **kwargs):
        """List report folders with search and filter capabilities"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=REPORT_FOLDER_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific report folder"""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=REPORT_FOLDER_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        """Create a new report folder"""
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=BULK_UPDATE_DOCS)
    def bulk_update(self, request, *args, **kwargs):
        """Bulk update report folders"""
        return super().bulk_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=BULK_DELETE_DOCS)
    def bulk_delete(self, request, *args, **kwargs):
        """Bulk delete report folders"""
        return super().bulk_delete(request, *args, **kwargs)


class ReportViewSet(SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet):
    """ViewSet for Report model"""

    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    # Search across common report fields
    search_fields = [
        "name",
        "chart_type",
    ]

    # Filtering on key fields and common core fields
    filterset_fields = [
        "report_owner",
        "folder",
        "is_favourite",
        "company",
        "created_by",
        "module",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=REPORT_LIST_DOCS + "\n\n" + SEARCH_FILTER_DOCS,
    )
    def list(self, request, *args, **kwargs):
        """List reports with search and filter capabilities"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=REPORT_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific report"""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=REPORT_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        """Create a new report"""
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=BULK_UPDATE_DOCS)
    def bulk_update(self, request, *args, **kwargs):
        """Bulk update reports"""
        return super().bulk_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=BULK_DELETE_DOCS)
    def bulk_delete(self, request, *args, **kwargs):
        """Bulk delete reports"""
        return super().bulk_delete(request, *args, **kwargs)
