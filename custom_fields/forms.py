from django import forms
from django.utils.safestring import mark_safe

from horilla.contrib.core.models import HorillaContentType
from horilla.contrib.generics.forms import HorillaModelForm
from horilla.utils.translation import gettext_lazy as _

from .models import CustomFieldDefinition

SUPPORTED_MODELS = ["leads.lead", "opportunities.opportunity"]

CHOICES_TOGGLE_SCRIPT = """
<script>
(function () {
  var select = document.getElementById("id_field_type");
  var box = document.getElementById("choices_container");
  function syncChoicesVisibility() {
    if (!select || !box) return;
    box.style.display = select.value === "choice" ? "" : "none";
  }
  if (!select) return;
  if (!select.dataset.cfChoicesBound) {
    select.dataset.cfChoicesBound = "1";
    select.addEventListener("change", syncChoicesVisibility);
    if (window.jQuery) {
      window.jQuery(select).on("change select2:select select2:clear", syncChoicesVisibility);
    }
  }
  syncChoicesVisibility();
})();
</script>
"""


class FieldTypeSelect(forms.Select):
    """Select that toggles the choices textarea when Multiple Choice is picked."""

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        return mark_safe(str(html) + CHOICES_TOGGLE_SCRIPT)


class CustomFieldDefinitionForm(HorillaModelForm):
    """Form for creating / editing a custom field definition."""

    class Meta:
        model = CustomFieldDefinition
        fields = [
            "content_type",
            "name",
            "field_type",
            "is_required",
            "choices",
            "order",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        supported_cts = HorillaContentType.objects.filter(
            app_label__in=["leads", "opportunities"],
            model__in=["lead", "opportunity"],
        )
        self.fields["content_type"].queryset = supported_cts
        self.fields["content_type"].label = _("Model")

        self.fields["choices"].required = False
        self.fields["choices"].widget.attrs.update(
            {
                "rows": 3,
                "placeholder": _("Option 1, Option 2, Option 3"),
            }
        )
        if self._current_field_type() == "choice":
            self.fields["choices"].widget.attrs.pop("container_style", None)
        else:
            self.fields["choices"].widget.attrs["container_style"] = "display: none;"

        field_type_widget = self.fields["field_type"].widget
        self.fields["field_type"].widget = FieldTypeSelect(
            attrs=field_type_widget.attrs,
            choices=list(self.fields["field_type"].choices),
        )

    def _current_field_type(self):
        if self.is_bound and self.data is not None:
            return self.data.get("field_type") or ""
        if getattr(self.instance, "pk", None):
            return self.instance.field_type or ""
        return self.initial.get("field_type") or ""

    def clean(self):
        cleaned_data = super().clean()
        field_type = cleaned_data.get("field_type")
        choices = cleaned_data.get("choices", "")
        if field_type == "choice" and not choices.strip():
            self.add_error(
                "choices", _("Choices are required for Multiple Choice fields.")
            )
        ct = cleaned_data.get("content_type")
        if ct and f"{ct.app_label}.{ct.model}" not in SUPPORTED_MODELS:
            self.add_error(
                "content_type",
                _("Custom fields are only supported for Leads and Opportunities."),
            )
        return cleaned_data
