"""
API views for horilla_crm.opportunities models

This module mirrors horilla_core API patterns including search, filtering,
bulk update, bulk delete, permissions, and documentation.
"""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from horilla_core.api.mixins import BulkOperationsMixin, SearchFilterMixin
from horilla_core.api.permissions import IsCompanyMember, IsOwnerOrAdmin
from horilla_crm.opportunities.api.serializers import (
    BigDealAlertSerializer,
    DefaultOpportunityMemberSerializer,
    OpportunitySerializer,
    OpportunityStageSerializer,
    OpportunityTeamMemberSerializer,
    OpportunityTeamSerializer,
)
from horilla_crm.opportunities.models import (
    BigDealAlert,
    DefaultOpportunityMember,
    Opportunity,
    OpportunityStage,
    OpportunityTeam,
    OpportunityTeamMember,
)

# Define common Swagger parameters for documentation
search_param = openapi.Parameter(
    "search",
    openapi.IN_QUERY,
    description="Search term for filtering results",
    type=openapi.TYPE_STRING,
)


class OpportunityStageViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for OpportunityStage model"""

    queryset = OpportunityStage.objects.all()
    serializer_class = OpportunityStageSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]
    search_fields = ["name"]
    filterset_fields = ["stage_type", "is_final", "company"]


class OpportunityViewSet(SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet):
    """ViewSet for Opportunity model"""

    queryset = Opportunity.objects.all()
    serializer_class = OpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]
    search_fields = ["name", "tracking_number", "order_number"]
    filterset_fields = [
        "stage",
        "owner",
        "opportunity_type",
        "lead_source",
        "forecast_category",
        "company",
    ]

    @action(detail=True, methods=["get"])
    def team_members(self, request, pk=None):
        """Get team members for an opportunity"""
        opportunity = self.get_object()
        team_members = OpportunityTeamMember.objects.filter(opportunity=opportunity)
        serializer = OpportunityTeamMemberSerializer(team_members, many=True)
        return Response(serializer.data)


class OpportunityTeamViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for OpportunityTeam model"""

    queryset = OpportunityTeam.objects.all()
    serializer_class = OpportunityTeamSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]
    search_fields = ["team_name"]
    filterset_fields = ["owner", "company"]

    @action(detail=True, methods=["get"])
    def team_members(self, request, pk=None):
        """Get default team members for a team"""
        team = self.get_object()
        members = DefaultOpportunityMember.objects.filter(team=team)
        serializer = DefaultOpportunityMemberSerializer(members, many=True)
        return Response(serializer.data)


class OpportunityTeamMemberViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for OpportunityTeamMember model"""

    queryset = OpportunityTeamMember.objects.all()
    serializer_class = OpportunityTeamMemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]
    search_fields = ["user__first_name", "user__last_name", "team_role"]
    filterset_fields = [
        "opportunity",
        "user",
        "team_role",
        "opportunity_access",
        "company",
    ]


class DefaultOpportunityMemberViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for DefaultOpportunityMember model"""

    queryset = DefaultOpportunityMember.objects.all()
    serializer_class = DefaultOpportunityMemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]
    search_fields = ["user__first_name", "user__last_name", "team_role"]
    filterset_fields = [
        "team",
        "user",
        "team_role",
        "opportunity_access_level",
        "company",
    ]


class BigDealAlertViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for BigDealAlert model"""

    queryset = BigDealAlert.objects.all()
    serializer_class = BigDealAlertSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]
    search_fields = ["alert_name", "sender_name", "sender_email"]
    filterset_fields = ["active", "notify_opportunity_owner", "company"]
