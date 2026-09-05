"""
``_inherit_view`` extensions so Horilla inline edit works for ``cf_*`` fields.

EditFieldView / UpdateFieldView / CancelEditView resolve columns via
``model._meta.get_fields()``. Custom fields are not model columns, so these
extensions intercept ``cf_*`` before Horilla looks them up.
"""

from horilla.contrib.generics.views.helpers.edit_field import (
    CancelEditView,
    EditFieldView,
    UpdateFieldView,
)
from horilla.extension.view import ViewExtension

from custom_fields.detail_hooks import (
    handle_custom_field_cancel_get,
    handle_custom_field_edit_get,
    handle_custom_field_update_post,
)
from custom_fields.utils import is_custom_field_name


class CustomFieldEditFieldViewExtension(ViewExtension):
    """Open the inline editor for a custom field."""

    _inherit_view = "horilla.contrib.generics.views.helpers.edit_field.EditFieldView"

    def get(self, request, pk, field_name, app_label, model_name):
        if is_custom_field_name(field_name):
            return handle_custom_field_edit_get(
                request, pk, field_name, app_label, model_name
            )
        return EditFieldView.get(self, request, pk, field_name, app_label, model_name)


class CustomFieldUpdateFieldViewExtension(ViewExtension):
    """Save an inline custom-field value."""

    _inherit_view = "horilla.contrib.generics.views.helpers.edit_field.UpdateFieldView"

    def post(self, request, pk, field_name, app_label, model_name):
        if is_custom_field_name(field_name):
            return handle_custom_field_update_post(
                request, pk, field_name, app_label, model_name
            )
        return UpdateFieldView.post(
            self, request, pk, field_name, app_label, model_name
        )


class CustomFieldCancelEditViewExtension(ViewExtension):
    """Cancel inline edit of a custom field."""

    _inherit_view = "horilla.contrib.generics.views.helpers.edit_field.CancelEditView"

    def get(self, request, pk, field_name, app_label, model_name):
        if is_custom_field_name(field_name):
            return handle_custom_field_cancel_get(
                request, pk, field_name, app_label, model_name
            )
        return CancelEditView.get(self, request, pk, field_name, app_label, model_name)
