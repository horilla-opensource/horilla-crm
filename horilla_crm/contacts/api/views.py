"""
API views for horilla_crm.contacts models

This module mirrors horilla_core and accounts API patterns including search, filtering,
bulk update, bulk delete, permissions, and documentation.
"""

import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, viewsets

from horilla_core.api.docs import BULK_DELETE_DOCS, BULK_UPDATE_DOCS, SEARCH_FILTER_DOCS
from horilla_core.api.mixins import BulkOperationsMixin, SearchFilterMixin
from horilla_core.api.permissions import IsCompanyMember
from horilla_crm.contacts.api.docs import (
    CONTACT_CREATE_DOCS,
    CONTACT_DETAIL_DOCS,
    CONTACT_LIST_DOCS,
)
from horilla_crm.contacts.api.serializers import ContactSerializer
from horilla_crm.contacts.models import Contact

logger = logging.getLogger(__name__)

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


class ContactViewSet(SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet):
    """ViewSet for Contact model"""

    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    # Search across common contact fields
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "secondary_phone",
        "address_city",
        "address_state",
        "address_country",
        "description",
    ]

    # Filtering on key fields and common core fields
    filterset_fields = [
        "contact_owner",
        "parent_contact",
        "contact_source",
        "is_primary",
        "languages",
        "is_active",
        "created_by",
        "company",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=CONTACT_LIST_DOCS + "\n\n" + SEARCH_FILTER_DOCS,
    )
    def list(self, request, *args, **kwargs):
        """List contacts with search and filter capabilities"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=CONTACT_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific contact"""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=CONTACT_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        """Create a new contact"""
        response = super().create(request, *args, **kwargs)
        try:
            logger.info(
                "Contact created", extra={"contact_id": response.data.get("id")}
            )
        except Exception:
            # Ensure logging does not break response
            pass
        return response

    @swagger_auto_schema(
        request_body=bulk_update_body, operation_description=BULK_UPDATE_DOCS
    )
    def bulk_update(self, request):
        """Update multiple contacts in a single request"""
        return super().bulk_update(request)

    @swagger_auto_schema(
        request_body=bulk_delete_body, operation_description=BULK_DELETE_DOCS
    )
    def bulk_delete(self, request):
        """Delete multiple contacts in a single request"""
        return super().bulk_delete(request)
