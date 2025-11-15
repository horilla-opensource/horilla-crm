"""
Serializers for horilla_crm.campaigns models
"""

from rest_framework import serializers

from horilla_core.api.serializers import HorillaUserSerializer
from horilla_crm.campaigns.models import Campaign


class CampaignSerializer(serializers.ModelSerializer):
    """Serializer for Campaign model"""

    campaign_owner_details = HorillaUserSerializer(
        source="campaign_owner", read_only=True
    )
    parent_campaign_details = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = "__all__"

    def get_parent_campaign_details(self, obj):
        """Return minimal details about the parent campaign if present"""
        if obj.parent_campaign:
            return {
                "id": obj.parent_campaign.id,
                "campaign_name": obj.parent_campaign.campaign_name,
                "status": obj.parent_campaign.status,
            }
        return None
