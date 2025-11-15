"""
Serializers for horilla_crm.activity models
"""

from rest_framework import serializers

from horilla_core.api.serializers import HorillaUserSerializer
from horilla_crm.activity.models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    """Serializer for Activity model"""

    owner_details = HorillaUserSerializer(source="owner", read_only=True)
    meeting_host_details = HorillaUserSerializer(source="meeting_host", read_only=True)
    assigned_to_details = HorillaUserSerializer(
        source="assigned_to", many=True, read_only=True
    )
    participants_details = HorillaUserSerializer(
        source="participants", many=True, read_only=True
    )

    class Meta:
        model = Activity
        fields = "__all__"
