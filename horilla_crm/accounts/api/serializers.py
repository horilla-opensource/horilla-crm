"""
Serializers for horilla_crm.accounts models
"""

from rest_framework import serializers

from horilla_core.api.serializers import HorillaUserSerializer
from horilla_crm.accounts.models import Account, PartnerAccountRelationship


class AccountSerializer(serializers.ModelSerializer):
    """Serializer for Account model"""

    account_owner_details = HorillaUserSerializer(
        source="account_owner", read_only=True
    )
    parent_account_details = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = "__all__"

    def get_parent_account_details(self, obj):
        """Get parent account details if available"""
        if obj.parent_account:
            return {
                "id": obj.parent_account.id,
                "name": obj.parent_account.name,
                "account_number": obj.parent_account.account_number,
            }
        return None


class PartnerAccountRelationshipSerializer(serializers.ModelSerializer):
    """Serializer for PartnerAccountRelationship model"""

    account_details = AccountSerializer(source="account", read_only=True)
    partner_details = AccountSerializer(source="partner", read_only=True)

    class Meta:
        model = PartnerAccountRelationship
        fields = "__all__"
