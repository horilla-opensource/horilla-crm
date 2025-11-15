"""
API views for horilla_notifications models

This module includes enhanced API views with search, filtering, bulk update, and bulk delete capabilities.
"""

from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from horilla_core.api.docs import BULK_DELETE_DOCS, BULK_UPDATE_DOCS, SEARCH_FILTER_DOCS
from horilla_core.api.mixins import BulkOperationsMixin, SearchFilterMixin
from horilla_notifications.api.docs import NOTIFICATION_API_DOCS
from horilla_notifications.api.filters import NotificationFilter
from horilla_notifications.api.permissions import IsNotificationOwner
from horilla_notifications.api.serializers import NotificationSerializer
from horilla_notifications.models import Notification

# Define common Swagger parameters for search and filtering
search_param = openapi.Parameter(
    "search",
    openapi.IN_QUERY,
    description="Search term for full-text search across relevant fields",
    type=openapi.TYPE_STRING,
)

# Define common Swagger request bodies for bulk operations
bulk_update_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "ids": openapi.Schema(
            type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)
        ),
        "data": openapi.Schema(type=openapi.TYPE_OBJECT, additional_properties=True),
    },
    required=["ids", "data"],
)

bulk_delete_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "ids": openapi.Schema(
            type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER)
        )
    },
    required=["ids"],
)


class NotificationPagination(PageNumberPagination):
    """Custom pagination for notifications"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificationViewSet(
    SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet
):
    """ViewSet for Notification model"""

    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsNotificationOwner]
    pagination_class = NotificationPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = NotificationFilter
    search_fields = ["message", "url"]
    ordering_fields = ["created_at", "read"]
    ordering = ["-created_at"]

    @swagger_auto_schema(
        manual_parameters=[search_param], operation_description=SEARCH_FILTER_DOCS
    )
    def list(self, request, *args, **kwargs):
        """List notifications with search and filter capabilities"""
        # Filter notifications for the current user only
        self.queryset = self.queryset.filter(user=request.user)
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=bulk_update_body, operation_description=BULK_UPDATE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Update multiple notifications in a single request"""
        return super().bulk_update(request)

    @swagger_auto_schema(
        request_body=bulk_delete_body, operation_description=BULK_DELETE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """Delete multiple notifications in a single request"""
        return super().bulk_delete(request)

    @action(detail=False, methods=["post"])
    def mark_all_as_read(self, request):
        """Mark all notifications as read for the current user"""
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        return Response(
            {"status": "success", "message": "All notifications marked as read"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        """Mark a specific notification as read"""
        notification = self.get_object()
        notification.read = True
        notification.save()
        return Response(
            {"status": "success", "message": "Notification marked as read"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Get count of unread notifications for the current user"""
        count = Notification.objects.filter(user=request.user, read=False).count()
        return Response({"count": count}, status=status.HTTP_200_OK)
