"""
API views for horilla_crm.activity models

This module mirrors horilla_core and accounts API patterns including search, filtering,
bulk update, bulk delete, permissions, and documentation, adapted for activity-specific logic.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from horilla_core.api.docs import BULK_DELETE_DOCS, BULK_UPDATE_DOCS, SEARCH_FILTER_DOCS
from horilla_core.api.mixins import BulkOperationsMixin, SearchFilterMixin
from horilla_core.api.permissions import IsCompanyMember
from horilla_crm.activity.api.docs import (
    ACTIVITY_BY_ASSIGNED_DOCS,
    ACTIVITY_BY_OWNER_DOCS,
    ACTIVITY_BY_PARTICIPANT_DOCS,
    ACTIVITY_BY_RELATED_DOCS,
    ACTIVITY_BY_TYPE_DOCS,
    ACTIVITY_COMPLETED_DOCS,
    ACTIVITY_CREATE_DOCS,
    ACTIVITY_DETAIL_DOCS,
    ACTIVITY_LIST_DOCS,
    ACTIVITY_PENDING_DOCS,
    ACTIVITY_UPCOMING_DOCS,
)
from horilla_crm.activity.api.serializers import ActivitySerializer
from horilla_crm.activity.models import Activity

# Define common Swagger parameters and bodies consistent with horilla_core/accounts
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


class ActivityViewSet(SearchFilterMixin, BulkOperationsMixin, viewsets.ModelViewSet):
    """ViewSet for Activity model"""

    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyMember]

    # Search across common activity fields
    search_fields = [
        "subject",
        "description",
        "title",
        "location",
        "notes",
        "call_purpose",
    ]

    # Filtering on key fields and common core fields
    filterset_fields = [
        "activity_type",
        "status",
        "is_all_day",
        "owner",
        "meeting_host",
        "assigned_to",
        "participants",
        "start_datetime",
        "end_datetime",
        "due_datetime",
        "company",
        "created_by",
        "content_type",
        "object_id",
        "call_type",
        "task_priority",
        "is_active",
    ]

    @swagger_auto_schema(
        manual_parameters=[search_param],
        operation_description=ACTIVITY_LIST_DOCS,
    )
    def list(self, request, *args, **kwargs):
        """List activities with search and filter capabilities"""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=ACTIVITY_DETAIL_DOCS)
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a specific activity"""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(operation_description=ACTIVITY_CREATE_DOCS)
    def create(self, request, *args, **kwargs):
        """Create a new activity"""
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=bulk_update_body, operation_description=BULK_UPDATE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """Update multiple activities in a single request"""
        return super().bulk_update(request)

    @swagger_auto_schema(
        request_body=bulk_delete_body, operation_description=BULK_DELETE_DOCS
    )
    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """Delete multiple activities in a single request"""
        return super().bulk_delete(request)

    @swagger_auto_schema(operation_description=ACTIVITY_BY_RELATED_DOCS)
    @action(detail=False, methods=["get"])
    def by_related(self, request):
        """Get activities related to a specific object"""
        content_type_id = request.query_params.get("content_type_id")
        content_type_str = request.query_params.get("content_type")
        object_id = request.query_params.get("object_id")

        if not object_id or (not content_type_id and not content_type_str):
            return Response(
                {"error": "content_type_id or content_type and object_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if content_type_id:
                ct = ContentType.objects.get(id=content_type_id)
            else:
                app_label, model = content_type_str.split(".")
                ct = ContentType.objects.get(app_label=app_label, model=model)
        except Exception:
            return Response(
                {"error": "Invalid content type"}, status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.filter_queryset(
            self.get_queryset().filter(content_type=ct, object_id=object_id)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(operation_description=ACTIVITY_BY_OWNER_DOCS)
    @action(detail=False, methods=["get"])
    def by_owner(self, request):
        """Get activities filtered by owner ID"""
        owner_id = request.query_params.get("owner_id")
        if not owner_id:
            return Response(
                {"error": "owner_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = self.filter_queryset(self.get_queryset().filter(owner_id=owner_id))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(operation_description=ACTIVITY_BY_ASSIGNED_DOCS)
    @action(detail=False, methods=["get"], url_path="by-assigned")
    def by_assigned(self, request):
        """Get activities where assigned_to contains the given user ID"""
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"error": "user_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = self.filter_queryset(
            self.get_queryset().filter(assigned_to__id=user_id)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(operation_description=ACTIVITY_BY_PARTICIPANT_DOCS)
    @action(detail=False, methods=["get"], url_path="by-participant")
    def by_participant(self, request):
        """Get activities where participants contains the given user ID"""
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"error": "user_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = self.filter_queryset(
            self.get_queryset().filter(participants__id=user_id)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(operation_description=ACTIVITY_BY_TYPE_DOCS)
    @action(detail=False, methods=["get"], url_path="by-type")
    def by_type(self, request):
        """Get activities filtered by activity type"""
        activity_type = request.query_params.get("type")
        if not activity_type:
            return Response(
                {"error": "type parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = self.filter_queryset(
            self.get_queryset().filter(activity_type=activity_type)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(operation_description=ACTIVITY_COMPLETED_DOCS)
    @action(detail=False, methods=["get"])
    def completed(self, request):
        """Get activities marked as completed"""
        queryset = self.filter_queryset(self.get_queryset().filter(status="completed"))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(operation_description=ACTIVITY_PENDING_DOCS)
    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Get activities marked as pending"""
        queryset = self.filter_queryset(self.get_queryset().filter(status="pending"))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(operation_description=ACTIVITY_UPCOMING_DOCS)
    @action(detail=False, methods=["get"])
    def upcoming(self, request):
        """Get upcoming activities based on start or due date"""
        now = timezone.now()
        queryset = self.filter_queryset(
            self.get_queryset().filter(
                models.Q(start_datetime__gte=now) | models.Q(due_datetime__gte=now)
            )
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
