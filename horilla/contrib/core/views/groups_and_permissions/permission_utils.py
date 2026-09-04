"""
This module contains utility functions and classes for handling permissions in the Horilla Core application.
"""

# Third-party imports (Django)
from django.contrib.auth.models import Permission

# First party imports (Horilla)
from horilla.apps import apps
from horilla.registry.permission_registry import is_permission_exempt
from horilla.utils.translation import gettext_lazy as _


class PermissionUtils:
    """Utility class to handle common permission-related logic."""

    FIXED_ORDER = [
        "add",
        "change",
        "view",
        "delete",
        "export",
        "add_own",
        "change_own",
        "view_own",
        "delete_own",
        "export_own",
    ]

    PERMISSION_MAP = {
        "add": _("Create"),
        "change": _("Change"),
        "view": _("View"),
        "delete": _("Delete"),
        "export": _("Export"),
        "add_own": _("Create Own"),
        "change_own": _("Change Own"),
        "view_own": _("View Own"),
        "delete_own": _("Delete Own"),
        "export_own": _("Export Own"),
    }

    @staticmethod
    def get_model_permissions(app_label, model_name, permissions=None):
        """Retrieve permissions for a specific model."""
        if permissions is None:
            permissions = list(
                Permission.objects.filter(
                    content_type__app_label=app_label,
                    content_type__model=model_name.lower(),
                )
            )

        by_codename = {perm.codename: perm for perm in permissions}
        model_name_lower = model_name.lower()

        simplified_permissions = []
        standard_codenames = set()
        for key in PermissionUtils.FIXED_ORDER:
            expected_codename = f"{key}_{model_name_lower}"
            standard_codenames.add(expected_codename)
            perm = by_codename.get(expected_codename)
            if perm:
                simplified_permissions.append(
                    {
                        "id": perm.id,
                        "codename": perm.codename,
                        "label": PermissionUtils.PERMISSION_MAP[key],
                    }
                )

        for perm in permissions:
            if perm.codename in standard_codenames:
                continue
            if perm.name:
                label = _(perm.name)
            else:
                label = _(perm.codename.replace("_", " ").title())

            simplified_permissions.append(
                {
                    "id": perm.id,
                    "codename": perm.codename,
                    "label": label,
                }
            )

        return simplified_permissions

    @staticmethod
    def get_all_models_data(user=None, role=None, search_query=None):
        """Retrieve all models with their permissions, optionally checking user or role permissions."""

        all_permissions = list(Permission.objects.select_related("content_type").all())
        permissions_by_model = {}
        for perm in all_permissions:
            key = (perm.content_type.app_label, perm.content_type.model)
            permissions_by_model.setdefault(key, []).append(perm)

        granted_ids = None
        if user is not None:
            granted_ids = set(user.user_permissions.values_list("id", flat=True))
        elif role is not None:
            granted_ids = set(role.permissions.values_list("id", flat=True))

        all_models = []
        for model in apps.get_models():
            model_name = model.__name__
            app_label = model._meta.app_label

            if is_permission_exempt(model):
                continue

            if search_query:
                verbose_name = model._meta.verbose_name.lower()
                verbose_name_plural = model._meta.verbose_name_plural.lower()
                search_lower = search_query.lower()

                if not (
                    search_lower in verbose_name
                    or search_lower in verbose_name_plural
                    or search_lower in model_name.lower()
                    or search_lower in app_label.lower()
                ):
                    continue

            model_permissions = permissions_by_model.get(
                (app_label, model_name.lower()), []
            )
            permissions = PermissionUtils.get_model_permissions(
                app_label, model_name, permissions=model_permissions
            )
            if permissions:
                has_export = any(
                    perm["codename"] == f"export_{model_name.lower()}"
                    for perm in permissions
                )
                model_data = {
                    "app_label": app_label,
                    "model_name": model_name,
                    "verbose_name": model._meta.verbose_name,
                    "verbose_name_plural": model._meta.verbose_name_plural,
                    "permissions": permissions,
                    "is_managed": model._meta.managed,
                    "has_export": has_export,
                }
                if granted_ids is not None:
                    all_permissions_checked = True
                    has_any_permission = False
                    for perm in permissions:
                        has_perm = perm["id"] in granted_ids
                        perm["has_perm"] = has_perm
                        if has_perm:
                            has_any_permission = True
                        else:
                            all_permissions_checked = False
                    model_data["select_all_checked"] = (
                        all_permissions_checked
                        and has_any_permission
                        and len(permissions) > 0
                    )
                all_models.append(model_data)
        return sorted(
            all_models,
            key=lambda m: (
                m["is_managed"],
                not m["has_export"],
                m["app_label"],
                m["model_name"],
            ),
        )
