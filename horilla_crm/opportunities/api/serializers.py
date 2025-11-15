"""
Serializers for horilla_crm.opportunities models
"""

from rest_framework import serializers

from horilla_core.api.serializers import HorillaUserSerializer
from horilla_crm.opportunities.models import (
    BigDealAlert,
    DefaultOpportunityMember,
    Opportunity,
    OpportunityStage,
    OpportunityTeam,
    OpportunityTeamMember,
)


class OpportunityStageSerializer(serializers.ModelSerializer):
    """Serializer for OpportunityStage model"""

    class Meta:
        model = OpportunityStage
        fields = "__all__"


class OpportunitySerializer(serializers.ModelSerializer):
    """Serializer for Opportunity model"""

    owner_details = HorillaUserSerializer(source="owner", read_only=True)
    stage_details = OpportunityStageSerializer(source="stage", read_only=True)

    class Meta:
        model = Opportunity
        fields = "__all__"


class OpportunityTeamSerializer(serializers.ModelSerializer):
    """Serializer for OpportunityTeam model"""

    owner_details = HorillaUserSerializer(source="owner", read_only=True)

    class Meta:
        model = OpportunityTeam
        fields = "__all__"


class OpportunityTeamMemberSerializer(serializers.ModelSerializer):
    """Serializer for OpportunityTeamMember model"""

    user_details = HorillaUserSerializer(source="user", read_only=True)
    opportunity_details = OpportunitySerializer(source="opportunity", read_only=True)

    class Meta:
        model = OpportunityTeamMember
        fields = "__all__"


class DefaultOpportunityMemberSerializer(serializers.ModelSerializer):
    """Serializer for DefaultOpportunityMember model"""

    user_details = HorillaUserSerializer(source="user", read_only=True)
    team_details = OpportunityTeamSerializer(source="team", read_only=True)

    class Meta:
        model = DefaultOpportunityMember
        fields = "__all__"


class BigDealAlertSerializer(serializers.ModelSerializer):
    """Serializer for BigDealAlert model"""

    class Meta:
        model = BigDealAlert
        fields = "__all__"
