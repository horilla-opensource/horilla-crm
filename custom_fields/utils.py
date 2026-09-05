from django import forms

from horilla.contrib.core.models import HorillaContentType
from horilla.utils.translation import gettext as _

from .models import CustomFieldDefinition, CustomFieldValue

CUSTOM_FIELD_PREFIX = "cf_"

INLINE_FIELD_TYPES = {
    "small_text": "text",
    "large_text": "textarea",
    "number": "number",
    "choice": "select",
}


def is_custom_field_name(name):
    """Return True if ``name`` is a custom-field form/detail key (``cf_<id>``)."""
    return str(name).startswith(CUSTOM_FIELD_PREFIX)


def custom_field_form_name(definition):
    """Return the form/detail key for a ``CustomFieldDefinition``."""
    return f"{CUSTOM_FIELD_PREFIX}{definition.pk}"


def parse_custom_field_pk(name):
    """Return the definition pk from ``cf_<id>``, or None if the name is invalid."""
    if not is_custom_field_name(name):
        return None
    try:
        return int(str(name)[len(CUSTOM_FIELD_PREFIX) :])
    except (TypeError, ValueError):
        return None


def get_definition_by_form_name(model, field_name):
    """
    Return the active ``CustomFieldDefinition`` for ``field_name`` on ``model``.

    ``field_name`` must be ``cf_<id>`` and belong to this model's content type.
    """
    pk = parse_custom_field_pk(field_name)
    if pk is None:
        return None
    ct = HorillaContentType.objects.get_for_model(model)
    try:
        return CustomFieldDefinition.objects.get(
            pk=pk, content_type=ct, is_active=True
        )
    except CustomFieldDefinition.DoesNotExist:
        return None


def get_custom_field_definitions(model):
    """Return all active custom field definitions for a given model class."""
    ct = HorillaContentType.objects.get_for_model(model)
    return CustomFieldDefinition.objects.filter(content_type=ct, is_active=True)


def build_custom_form_fields(model):
    """
    Build a dict of Django form fields for all custom field definitions
    attached to the given model. Keys are prefixed with CUSTOM_FIELD_PREFIX.
    """
    fields = {}
    for defn in get_custom_field_definitions(model):
        key = f"{CUSTOM_FIELD_PREFIX}{defn.pk}"
        if defn.field_type == "small_text":
            field = forms.CharField(
                max_length=255,
                required=defn.is_required,
                label=defn.name,
                widget=forms.TextInput(
                    attrs={
                        "class": "text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm transition duration-300 focus:border-primary-600",
                        "placeholder": _("Enter %(name)s") % {"name": defn.name},
                    }
                ),
            )
        elif defn.field_type == "large_text":
            field = forms.CharField(
                required=defn.is_required,
                label=defn.name,
                widget=forms.Textarea(
                    attrs={
                        "class": "text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm transition duration-300 focus:border-primary-600",
                        "rows": 3,
                        "placeholder": _("Enter %(name)s") % {"name": defn.name},
                    }
                ),
            )
        elif defn.field_type == "number":
            field = forms.DecimalField(
                max_digits=20,
                decimal_places=4,
                required=defn.is_required,
                label=defn.name,
                widget=forms.NumberInput(
                    attrs={
                        "class": "text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm transition duration-300 focus:border-primary-600",
                        "placeholder": _("Enter %(name)s") % {"name": defn.name},
                    }
                ),
            )
        elif defn.field_type == "choice":
            choices_list = [("", "---------")] + [
                (c, c) for c in defn.get_choices_list()
            ]
            field = forms.ChoiceField(
                choices=choices_list,
                required=defn.is_required,
                label=defn.name,
                widget=forms.Select(
                    attrs={
                        "class": "text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm transition duration-300 focus:border-primary-600",
                    }
                ),
            )
        else:
            continue
        fields[key] = field
    return fields


def load_custom_field_values(model_class, instance_pk):
    """Return a dict of {cf_<defn_pk>: value} for a saved instance."""
    ct = HorillaContentType.objects.get_for_model(model_class)
    values = {}
    for cfv in CustomFieldValue.objects.filter(
        content_type=ct, object_id=instance_pk
    ).select_related("field_definition"):
        key = f"{CUSTOM_FIELD_PREFIX}{cfv.field_definition_id}"
        values[key] = cfv.get_value()
    return values


def save_custom_field_values(model_class, instance_pk, cleaned_data, company=None):
    """
    Persist custom field values from cleaned_data for the given instance.
    Only processes keys that start with CUSTOM_FIELD_PREFIX.
    """
    ct = HorillaContentType.objects.get_for_model(model_class)
    for key, value in cleaned_data.items():
        if not key.startswith(CUSTOM_FIELD_PREFIX):
            continue
        defn_pk = int(key[len(CUSTOM_FIELD_PREFIX) :])
        try:
            defn = CustomFieldDefinition.objects.get(pk=defn_pk)
        except CustomFieldDefinition.DoesNotExist:
            continue

        cfv, _created = CustomFieldValue.objects.update_or_create(
            field_definition=defn,
            content_type=ct,
            object_id=instance_pk,
            defaults={"company": company} if company else {},
        )
        cfv.set_value(value)
        if company and cfv.company != company:
            cfv.company = company
        cfv.save()
