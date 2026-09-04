"""
Common mixin for single-form and multi-form views in Horilla generics.
Provides shared permission checks, dynamic create field filtering, related models info,
permission-denied response, object resolution, alternate form URL, and field permissions.
"""

# Third-party imports (Django)
from django.contrib import messages

from horilla.contrib.core.utils import get_field_permissions_for_model

# First party imports (Horilla)
from horilla.db import models
from horilla.shortcuts import get_object_or_404, render
from horilla.urls import reverse
from horilla.web import ScriptResponse


class FormViewCommonMixin:
    """
    Mixin with shared logic for HorillaSingleFormView and HorillaMultiStepFormView.
    Use as a first base so that get_filtered_dynamic_create_fields, permission methods,
    and get_related_models_info are available without code duplication.
    """

    def get_pk_key(self):
        """Return the URL keyword used for object pk (e.g. 'pk')."""
        return getattr(self, "pk_url_kwarg", "pk")

    def get_filtered_dynamic_create_fields(self):
        """Filter dynamic_create_fields based on user's add permissions."""
        dynamic_create_fields = getattr(self, "dynamic_create_fields", None)
        if not dynamic_create_fields or not self.model:
            return []

        dynamic_create_field_mapping = getattr(self, "dynamic_create_field_mapping", {})
        filtered_fields = []

        for field_name in dynamic_create_fields:
            try:
                field = self.model._meta.get_field(field_name)
                if not isinstance(field, (models.ForeignKey, models.ManyToManyField)):
                    continue

                related_model = field.related_model
                app_label = related_model._meta.app_label
                model_name = related_model._meta.model_name

                custom_perms = None
                if field_name in dynamic_create_field_mapping:
                    custom_perms = dynamic_create_field_mapping[field_name].get(
                        "permission"
                    )

                if custom_perms:
                    permissions = (
                        [custom_perms]
                        if isinstance(custom_perms, str)
                        else custom_perms
                    )
                else:
                    permissions = [f"{app_label}.add_{model_name}"]

                if any(self.request.user.has_perm(perm) for perm in permissions):
                    filtered_fields.append(field_name)
            except Exception:
                pass

        return filtered_fields

    def get_field_permissions(self):
        """Return field-level permissions for the view's model; empty dict if no model."""
        if not self.model:
            return {}
        return get_field_permissions_for_model(self.request.user, self.model)

    def get_permission_denied_response(self, request):
        """Return the standard 403 response when the user lacks permission."""
        return render(
            request,
            getattr(self, "permission_denied_template", "403.html"),
            {"modal": True},
        )

    def get_object_or_error_response(self, request):
        """
        Resolve the object by pk from URL kwargs. Return (object, None) on success,
        or (None, HttpResponse) on error (e.g. 404). Return (None, None) when no pk.
        Caller should set self.object when the first element is not None.
        """
        pk_key = self.get_pk_key()
        pk = self.kwargs.get(pk_key)
        if not pk:
            return (None, None)
        try:
            obj = get_object_or_404(self.model, pk=pk)
            return (obj, None)
        except Exception as e:
            messages.error(request, str(e))
            return (
                None,
                ScriptResponse(reload=True, close=True),
            )

    def get_alternate_form_url(self, url_name_attr):
        """
        Return the URL for the alternate form (single <-> multi) for create or edit.
        url_name_attr: name of the view attribute holding the URL name, e.g.
            'multi_step_url_name' or 'single_step_url_name'. Value can be a string
            or a dict with 'create' and 'edit' keys.
        """
        url_name = getattr(self, url_name_attr, None)
        if not url_name:
            return None
        pk_key = self.get_pk_key()
        pk = self.kwargs.get(pk_key)
        if pk:
            if isinstance(url_name, dict):
                name = url_name.get("edit")
                return reverse(name, kwargs={pk_key: pk}) if name else None
            return reverse(url_name, kwargs={pk_key: pk})
        if isinstance(url_name, dict):
            name = url_name.get("create")
            return reverse(name) if name else None
        return reverse(url_name)

    def get_auto_permissions(self):
        """
        Automatically generate the appropriate permission based on create/edit mode.
        Supports duplicate_mode (single form) so duplicate is treated as create.
        """
        if not self.model:
            return []

        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        pk_key = self.get_pk_key()
        is_edit_mode = bool(self.kwargs.get(pk_key))
        duplicate_mode = getattr(self, "duplicate_mode", False)

        if is_edit_mode and not duplicate_mode:
            return [f"{app_label}.change_{model_name}"]
        return [
            f"{app_label}.add_{model_name}",
            f"{app_label}.add_own_{model_name}",
        ]

    def has_permission(self):
        """
        Check if the user has the required permissions.
        Automatically checks both model permissions and object-level permissions.
        Supports duplicate_mode (single form).
        Superusers are always allowed (same as has_any_perms / Django convention).
        """
        user = self.request.user
        if getattr(user, "is_superuser", False):
            return True

        permissions = self.permission_required or self.get_auto_permissions()

        if isinstance(permissions, str):
            permissions = [permissions]

        if any(user.has_perm(perm) for perm in permissions):
            return True

        pk_key = self.get_pk_key()
        pk_value = self.kwargs.get(pk_key)
        duplicate_mode = getattr(self, "duplicate_mode", False)
        is_create_or_duplicate = not pk_value or duplicate_mode

        if pk_value and self.model:
            app_label = self.model._meta.app_label
            model_name = self.model._meta.model_name
            change_own_perm = f"{app_label}.change_own_{model_name}"
            model_supports_ownership = hasattr(self.model, "OWNER_FIELDS")
            if user.has_perm(change_own_perm) and model_supports_ownership:
                return self.has_object_permission()

        if is_create_or_duplicate and self.model:
            app_label = self.model._meta.app_label
            model_name = self.model._meta.model_name
            add_own_perm = f"{app_label}.add_own_{model_name}"
            if user.has_perm(add_own_perm):
                return True
        return False

    def has_object_permission(self):
        """
        Check object-level permissions (e.g., ownership) on self.model.
        Uses model's OWNER_FIELDS attribute or fallback owner fields.
        """
        pk_key = self.get_pk_key()
        if not self.kwargs.get(pk_key) or not self.model:
            return False

        try:
            obj = self.model.objects.get(pk=self.kwargs[pk_key])

            if hasattr(obj, "is_owned_by"):
                return obj.is_owned_by(self.request.user)

            if hasattr(self.model, "OWNER_FIELDS"):
                for owner_field in self.model.OWNER_FIELDS:
                    if hasattr(obj, owner_field):
                        if getattr(obj, owner_field) == self.request.user:
                            return True

            from ..helpers.queryset_utils import user_has_granted_access

            if user_has_granted_access(obj, self.request.user, "change"):
                return True

            fallback_owner_fields = [
                f"{self.model._meta.model_name}_owner",
                "owner",
                "created_by",
                "user",
            ]
            for owner_field in fallback_owner_fields:
                if hasattr(obj, owner_field):
                    if getattr(obj, owner_field) == self.request.user:
                        return True
            return False
        except self.model.DoesNotExist:
            return False

    def get_related_models_info(self):
        """
        Build related_models_info dict for context: dynamic create fields with
        permission and initial config. Used by both single-form and multi-form views.
        """
        related_models_info = {}
        filtered_fields = self.get_filtered_dynamic_create_fields()
        dynamic_create_field_mapping = getattr(self, "dynamic_create_field_mapping", {})

        for field_name in filtered_fields:
            try:
                field = self.model._meta.get_field(field_name)
                if not isinstance(field, (models.ForeignKey, models.ManyToManyField)):
                    continue

                related_model = field.related_model
                field_config = dynamic_create_field_mapping.get(field_name, {})

                permission = field_config.get("permission")
                permission_str = None
                if permission:
                    permission_str = (
                        ",".join(permission)
                        if isinstance(permission, list)
                        else permission
                    )

                initial_values = {}
                initial_config = field_config.get("initial", {})
                if initial_config:
                    company = getattr(self.request, "active_company", None)
                    for init_field, init_value in initial_config.items():
                        if callable(init_value):
                            try:
                                initial_values[init_field] = (
                                    init_value(company) if company else init_value()
                                )
                            except Exception:
                                pass
                        else:
                            initial_values[init_field] = init_value

                related_models_info[field_name] = {
                    "model_name": related_model._meta.model_name,
                    "app_label": related_model._meta.app_label,
                    "verbose_name": related_model._meta.verbose_name,
                    "permission": permission_str,
                    "initial": initial_values if initial_values else None,
                }
            except Exception:
                pass

        return related_models_info

    def _get_m2m_picker_info(self):
        """Return {field_name: {app_label, model_name}} for every multiple-select field on the form."""
        info = {}
        object_id = getattr(getattr(self, "object", None), "pk", None)
        try:
            form = self.get_form_class()()
        except Exception:
            return info
        for field_name, field in form.fields.items():
            if not getattr(field.widget, "attrs", {}).get("multiple"):
                continue
            related = None
            # Try to resolve related model from the model's meta field first
            if getattr(self, "model", None) is not None:
                try:
                    meta_field = self.model._meta.get_field(field_name)
                    related = getattr(meta_field, "related_model", None)
                except Exception:
                    pass
            # Fall back to the form field's queryset (e.g. plain ModelMultipleChoiceField)
            if related is None:
                qs = getattr(field, "queryset", None)
                if qs is not None:
                    related = qs.model
            if related:
                form_class = form.__class__
                form_class_path = f"{form_class.__module__}.{form_class.__name__}"
                info[field_name] = {
                    "app_label": related._meta.app_label,
                    "model_name": related._meta.model_name,
                    "form_class": form_class_path,
                    "object_id": object_id,
                }
        return info
