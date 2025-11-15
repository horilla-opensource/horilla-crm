"""
Custom permissions for horilla_core API
"""

from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to edit it
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner or admin
        if hasattr(obj, "created_by"):
            return obj.created_by == request.user or request.user.is_staff

        # For user objects
        if hasattr(obj, "id") and hasattr(request.user, "id"):
            return obj.id == request.user.id or request.user.is_staff

        return False


class IsCompanyMember(permissions.BasePermission):
    """
    Custom permission to only allow members of the same company to access objects
    """

    def has_object_permission(self, request, view, obj):
        # Check if user belongs to the same company
        if hasattr(obj, "company") and hasattr(request.user, "company"):
            return obj.company == request.user.company or request.user.is_staff

        return False
