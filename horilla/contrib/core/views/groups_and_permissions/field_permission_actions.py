"""
Views for managing field-level permissions in the permissions module."""

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

# First party imports (Horilla)
from horilla.apps import apps
from horilla.auth.models import User
from horilla.shortcuts import get_object_or_404
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _
from horilla.web import JsonResponse, ScriptResponse

# Local imports
from ...models import FieldPermission, HorillaContentType, Role


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class SaveBulkFieldPermissionsView(LoginRequiredMixin, View):
    """
    Save field permissions for multiple users at once (bulk assignment)
    """

    def post(self, request, *args, **kwargs):
        """Save field permissions for multiple users in bulk."""

        user_ids_str = request.POST.get("user_ids", "")
        if not user_ids_str:
            messages.error(
                request, _("No users selected. Please select at least one user.")
            )
            return ScriptResponse(close=True, msgs=True)

        try:
            user_ids = [
                int(uid.strip()) for uid in user_ids_str.split(",") if uid.strip()
            ]
        except (ValueError, AttributeError):
            messages.error(request, _("Invalid user selection."))
            return ScriptResponse(close=True, msgs=True)

        if not user_ids:
            messages.error(request, _("Please select at least one user."))
            return ScriptResponse(close=True, msgs=True)

        app_label = request.POST.get("app_label")
        model_name = request.POST.get("model_name")

        if not app_label or not model_name:
            messages.error(request, _("App label and model name are required"))
            return ScriptResponse(close=True, msgs=True)

        try:
            model = apps.get_model(app_label, model_name)
            content_type = HorillaContentType.objects.get_for_model(model)
        except LookupError:
            messages.error(request, _("Model not found"))
            return ScriptResponse(close=True, msgs=True)

        field_permissions = {}
        for key, value in request.POST.items():
            if key.startswith("field-"):
                field_name = key.replace("field-", "")
                field_permissions[field_name] = value

        if not field_permissions:
            messages.warning(request, _("No field permissions to save."))
            return ScriptResponse(close=True, msgs=True)

        try:
            users = User.objects.filter(id__in=user_ids, is_superuser=False)

            if not users.exists():
                messages.error(request, _("No valid users found."))
                return ScriptResponse(close=True, msgs=True)

            for user in users:
                for field_name, permission_type in field_permissions.items():
                    FieldPermission.objects.update_or_create(
                        user=user,
                        content_type=content_type,
                        field_name=field_name,
                        defaults={"permission_type": permission_type},
                    )

            messages.success(
                request,
                _(
                    "Successfully saved {count} field permission(s) for {user_count} user(s) on {model}."
                ).format(
                    count=len(field_permissions),
                    user_count=users.count(),
                    model=model._meta.verbose_name,
                ),
            )

            return ScriptResponse(close=True, msgs=True)

        except Exception as e:
            messages.error(
                request,
                _("Error saving field permissions: {error}").format(error=str(e)),
            )
            return ScriptResponse(close=True, msgs=True)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class UpdateFieldPermissionView(LoginRequiredMixin, View):
    """
    Update field-level permission for a user or role
    """

    def post(self, request, *args, **kwargs):
        """Update field permission for a user or role."""
        role_id = kwargs.get("role_id")
        user_id = kwargs.get("user_id")
        app_label = kwargs.get("app_label")
        model_name = kwargs.get("model_name")
        field_name = kwargs.get("field_name")
        permission_type = request.POST.get("permission_type")

        if not permission_type in ["readonly", "readwrite", "hidden"]:
            return JsonResponse(
                {"success": False, "message": "Invalid permission type"}
            )

        try:
            model = apps.get_model(app_label, model_name)
            content_type = HorillaContentType.objects.get_for_model(model)
        except LookupError:
            return JsonResponse({"success": False, "message": "Model not found"})

        try:
            if role_id:
                role = get_object_or_404(Role, id=role_id)
                _field_perm, created = FieldPermission.objects.update_or_create(
                    role=role,
                    content_type=content_type,
                    field_name=field_name,
                    defaults={"permission_type": permission_type},
                )
                target_name = role.role_name
            elif user_id:
                user = get_object_or_404(User, id=user_id)
                _field_perm, created = FieldPermission.objects.update_or_create(
                    user=user,
                    content_type=content_type,
                    field_name=field_name,
                    defaults={"permission_type": permission_type},
                )
                target_name = user.get_full_name()
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Either role_id or user_id must be provided",
                    }
                )

            action = "created" if created else "updated"
            messages.success(
                request,
                f"Field permission for '{field_name}' {action} successfully for {target_name}",
            )
            return JsonResponse(
                {"success": True, "message": "Field permission updated successfully"}
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"Error updating permission: {str(e)}"}
            )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "auth.view_permission",
            "auth.view_group",
            "auth.change_permission",
            "auth.change_group",
        ]
    ),
    name="dispatch",
)
class SaveAllFieldPermissionsView(LoginRequiredMixin, View):
    """
    Save all field permissions at once when user clicks 'Save Changes'
    """

    def post(self, request, *args, **kwargs):
        """Save all field permissions at once."""
        role_id = kwargs.get("role_id")
        user_id = kwargs.get("user_id")
        app_label = request.POST.get("app_label")
        model_name = request.POST.get("model_name")

        if not app_label or not model_name:
            messages.error(request, _("App label and model name are required"))
            return ScriptResponse(close=True, msgs=True)

        try:
            model = apps.get_model(app_label, model_name)
            content_type = HorillaContentType.objects.get_for_model(model)
        except LookupError:
            messages.error(request, _("Model not found"))
            return ScriptResponse(close=True, msgs=True)

        field_permissions = {}
        for key, value in request.POST.items():
            if key.startswith("field-"):
                field_name = key.replace("field-", "")
                field_permissions[field_name] = value

        try:
            saved_count = 0
            if role_id:
                role = get_object_or_404(Role, id=role_id)
                for field_name, permission_type in field_permissions.items():
                    FieldPermission.objects.update_or_create(
                        role=role,
                        content_type=content_type,
                        field_name=field_name,
                        defaults={"permission_type": permission_type},
                    )
                    saved_count += 1
                target_name = role.role_name

            elif user_id:
                user = get_object_or_404(User, id=user_id)
                for field_name, permission_type in field_permissions.items():
                    FieldPermission.objects.update_or_create(
                        user=user,
                        content_type=content_type,
                        field_name=field_name,
                        defaults={"permission_type": permission_type},
                    )
                    saved_count += 1
                target_name = user.get_full_name()
            else:
                messages.error(request, _("Either role or user must be specified"))
                return ScriptResponse(close=True, msgs=True)

            messages.success(
                request,
                f"Successfully saved {saved_count} field permissions for {target_name}",
            )

            return ScriptResponse(reload=True, msgs=True, close=True)

        except Exception as e:
            messages.error(request, f"Error saving field permissions: {str(e)}")
            return ScriptResponse(close=True, msgs=True)
