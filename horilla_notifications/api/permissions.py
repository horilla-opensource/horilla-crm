"""
Custom permissions for horilla_notifications API
"""

from rest_framework import permissions


class IsNotificationOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a notification to view or edit it
    """

    def has_object_permission(self, request, view, obj):
        # Check if the user is the owner of the notification
        return obj.user == request.user or request.user.is_staff
