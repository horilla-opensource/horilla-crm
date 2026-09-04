"""
Form for configuring whether a model field is required on its forms.

The field choices depend on the selected model, so the model select drives an
HTMX request that swaps in the matching field options.
"""

# Third-party imports (Django)
from django import forms

# First party imports (Horilla)
from horilla.contrib.core.models import HorillaContentType
from horilla.contrib.generics.forms import HorillaModelForm
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# Local imports
from .models import FieldRequirement
from .registry import (
    can_relax_requirement,
    get_configurable_fields,
    limit_content_types,
)


def get_field_choices(model):
    """Return ``(field_name, label)`` pairs configurable on `model`.

    Fields that cannot be made optional are still offered, since an admin may
    legitimately want to confirm them as required. Attempting to relax one is
    refused by ``FieldRequirement.clean``.
    """
    choices = []
    for field in get_configurable_fields(model):
        label = str(field.verbose_name)
        if not can_relax_requirement(field):
            label = _("%(label)s (always required)") % {"label": label}
        choices.append((field.name, label))
    return choices


class FieldRequirementForm(HorillaModelForm):
    """Create/edit form for a single field requirement override."""

    class Meta:
        """Meta options for FieldRequirementForm."""

        model = FieldRequirement
        fields = ["content_type", "field_name", "is_required"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["content_type"].queryset = HorillaContentType.objects.filter(
            limit_content_types()
        )
        self.fields["content_type"].empty_label = _("Select Model")
        self.fields["content_type"].widget.attrs.update(
            {
                "hx-get": reverse_lazy(
                    "field_requirements:field_requirement_field_choices"
                ),
                "hx-target": "#id_field_name",
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
            }
        )

        # Rebuilt as a plain choice field so the options can be swapped in by
        # HTMX without the model form trying to validate against a stale list.
        self.fields["field_name"] = forms.ChoiceField(
            choices=self._resolve_field_choices(),
            label=_("Field"),
            widget=forms.Select(
                attrs={
                    "id": "id_field_name",
                    "class": "js-example-basic-single headselect",
                }
            ),
        )

    def _selected_model(self):
        """Return the model currently selected, from posted data or instance."""
        content_type_id = self.data.get("content_type") or (
            self.instance.content_type_id if self.instance else None
        )
        if not content_type_id:
            return None
        try:
            return HorillaContentType.objects.get(pk=content_type_id).model_class()
        except (HorillaContentType.DoesNotExist, ValueError, TypeError):
            return None

    def _resolve_field_choices(self):
        """Return the field choices for the currently selected model."""
        choices = [("", _("Select Field"))]
        model = self._selected_model()
        if model is None:
            return choices
        return choices + get_field_choices(model)
