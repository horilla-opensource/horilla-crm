"""
Serializers for horilla_crm.contacts models
"""

from rest_framework import serializers

from horilla_core.api.serializers import HorillaUserSerializer
from horilla_crm.contacts.models import Contact


class ContactSerializer(serializers.ModelSerializer):
    """Serializer for Contact model"""

    contact_owner_details = HorillaUserSerializer(
        source="contact_owner", read_only=True
    )
    parent_contact_details = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = "__all__"

    def get_parent_contact_details(self, obj):
        """Return minimal details of parent contact if present"""
        if obj.parent_contact:
            return {
                "id": obj.parent_contact.id,
                "first_name": obj.parent_contact.first_name,
                "last_name": obj.parent_contact.last_name,
                "email": obj.parent_contact.email,
            }
        return None
