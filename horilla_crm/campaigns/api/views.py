"""
API views for horilla_crm.campaigns models

This module mirrors horilla_core and Accounts API patterns including search, filtering,
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
from horilla_crm.campaigns.api.docs import (
    CAMPAIGN_CHILD_CAMPAIGNS_DOCS,
    CAMPAIGN_CREATE_DOCS,
    CAMPAIGN_DETAIL_DOCS,
    CAMPAIGN_LIST_DOCS,
)
from horilla_crm.campaigns.api.serializers import CampaignSerializer
from horilla_crm.campaigns.models import Campaign

# Common Swagger parameter for search
search_param = openapi.Parameter(
    "search",
    openapi.IN_QUERY,
    description="Search term for full-text search across campaign fields",
    type=openapi.TYPE_STRING,
)


class CampaignViewSet(SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet):
    """ViewSet for Campaign model"""

    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    # Search across key campaign fields
    search_fields = [
        "campaign_name",
        "description",
    ]

    # Filtering on key fields and common core fields
    filterset_fields = [
        "campaign_owner",
        "status",
        "campaign_type",
        "start_date",
        "end_date",
        "parent_campaign",
        "is_active",
        "created_by",
        "company",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param], operation_description=CAMPAIGN_LIST_DOCS
    )
    def list(self, request, *args, **kwargs):
        """List campaigns with search and filter capabilities"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=CAMPAIGN_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific campaign"""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=CAMPAIGN_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        """Create a new campaign"""
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=BULK_UPDATE_DOCS)
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Update multiple campaigns in a single request"""
        return super().bulk_update(request)

    @swagger_auto_schema(operation_description=BULK_DELETE_DOCS)
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """Delete multiple campaigns in a single request"""
        return super().bulk_delete(request)

    @swagger_auto_schema(operation_description=CAMPAIGN_CHILD_CAMPAIGNS_DOCS)
    @action(detail=True, methods=["get"])
    def child_campaigns(self, request, pk=None):
        """Get child campaigns for a specific parent campaign"""
        campaign = self.get_object()
        queryset = self.filter_queryset(campaign.child_campaigns.all())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
