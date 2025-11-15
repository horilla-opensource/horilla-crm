"""
Serializers for horilla_crm.leads models
"""

from rest_framework import serializers

from horilla_core.api.serializers import HorillaUserSerializer
from horilla_crm.leads.models import Lead, LeadStatus


class LeadStatusSerializer(serializers.ModelSerializer):
    """Serializer for LeadStatus model"""

    class Meta:
        model = LeadStatus
        fields = "__all__"
