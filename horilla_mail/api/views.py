"""
API views for horilla_mail models

Follows horilla_core architecture: ModelViewSets with SearchFilterMixin and BulkOperationsMixin,
permissions, and swagger documentation.
"""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, viewsets

from horilla_core.api.mixins import BulkOperationsMixin, SearchFilterMixin
from horilla_core.api.permissions import IsCompanyMember, IsOwnerOrAdmin
from horilla_mail.api.docs import (
    MAIL_BULK_DELETE_DOCS,
    MAIL_BULK_UPDATE_DOCS,
    MAIL_SEARCH_FILTER_DOCS,
)
from horilla_mail.api.serializers import (
    HorillaMailAttachmentSerializer,
    HorillaMailConfigurationSerializer,
    HorillaMailSerializer,
    HorillaMailTemplateSerializer,
)
from horilla_mail.models import (
    HorillaMail,
    HorillaMailAttachment,
    HorillaMailConfiguration,
    HorillaMailTemplate,
)

# Common search parameter
search_param = openapi.Parameter(
    "search",
    openapi.IN_QUERY,
    description="Search term for full-text search across relevant fields",
    type=openapi.TYPE_STRING,
)


class HorillaMailConfigurationViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    queryset = HorillaMailConfiguration.objects.all().select_related(
        "company", "created_by"
    )
    serializer_class = HorillaMailConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    search_fields = [
        "type",
        "username",
        "from_email",
        "display_name",
        "host",
    ]
    filterset_fields = [
        "type",
        "is_primary",
        "company",
        "use_tls",
        "use_ssl",
        "mail_channel",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param], operation_description=MAIL_SEARCH_FILTER_DOCS
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_UPDATE_DOCS)
    def bulk_update(self, request, *args, **kwargs):
        return super().bulk_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_DELETE_DOCS)
    def bulk_delete(self, request, *args, **kwargs):
        return super().bulk_delete(request, *args, **kwargs)


class HorillaMailViewSet(SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet):
    queryset = HorillaMail.objects.all().select_related(
        "sender", "content_type", "created_by", "company"
    )
    serializer_class = HorillaMailSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    search_fields = ["subject", "to", "cc", "bcc", "mail_status"]
    filterset_fields = [
        "sender",
        "mail_status",
        "content_type",
        "object_id",
        "company",
        "created_by",
        "scheduled_at",
        "sent_at",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param], operation_description=MAIL_SEARCH_FILTER_DOCS
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_UPDATE_DOCS)
    def bulk_update(self, request, *args, **kwargs):
        return super().bulk_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_DELETE_DOCS)
    def bulk_delete(self, request, *args, **kwargs):
        return super().bulk_delete(request, *args, **kwargs)


class HorillaMailAttachmentViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    queryset = HorillaMailAttachment.objects.all().select_related(
        "mail", "created_by", "company"
    )
    serializer_class = HorillaMailAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    search_fields = ["mime_type"]
    filterset_fields = ["mail", "is_inline", "content_id", "company", "created_by"]

    @swagger_auto_schema(
        manual_parameters=[search_param], operation_description=MAIL_SEARCH_FILTER_DOCS
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_UPDATE_DOCS)
    def bulk_update(self, request, *args, **kwargs):
        return super().bulk_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_DELETE_DOCS)
    def bulk_delete(self, request, *args, **kwargs):
        return super().bulk_delete(request, *args, **kwargs)


class HorillaMailTemplateViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    queryset = HorillaMailTemplate.objects.all().select_related("company", "created_by")
    serializer_class = HorillaMailTemplateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]
    search_fields = ["title", "body"]
    filterset_fields = ["company", "content_type", "created_by"]

    @swagger_auto_schema(
        manual_parameters=[search_param], operation_description=MAIL_SEARCH_FILTER_DOCS
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_UPDATE_DOCS)
    def bulk_update(self, request, *args, **kwargs):
        return super().bulk_update(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=MAIL_BULK_DELETE_DOCS)
    def bulk_delete(self, request, *args, **kwargs):
        return super().bulk_delete(request, *args, **kwargs)
