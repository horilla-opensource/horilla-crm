"""
Runtime hooks for Horilla list-column picker and list-cell values.

Horilla's Add Column to List modal only knows about model columns. This
module patches those call sites from the custom_fields app so we do not
edit Horilla sources.
"""

import logging

from django.core.cache import cache
from django.utils.encoding import force_str

from horilla.apps import apps
from horilla.contrib.core.models import HorillaContentType, ListColumnVisibility

from custom_fields.detail_hooks import (
    custom_field_selector_items,
    field_names_from_list,
    relabel_custom_field_pairs,
)
from custom_fields.models import CustomFieldValue
from custom_fields.utils import custom_field_form_name, get_custom_field_definitions

logger = logging.getLogger(__name__)

_PATCHED = False


def inject_custom_fields_into_column_selector(context):
    """Add custom fields to the Add Column to List modal lists."""
    app_label = context.get("app_label")
    model_name = context.get("model_name")
    if not app_label or not model_name:
        return context
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return context

    extras = custom_field_selector_items(model)
    if not extras:
        return context

    visible_fields = relabel_custom_field_pairs(context.get("visible_fields"))
    available_fields = relabel_custom_field_pairs(context.get("available_fields"))

    visible_names = set(field_names_from_list(visible_fields))
    available_names = set(field_names_from_list(available_fields))

    for item in extras:
        key = item[1]
        if key in visible_names:
            continue
        if key not in available_names:
            available_fields.append(item)
            available_names.add(key)

    context["visible_fields"] = visible_fields
    context["available_fields"] = available_fields
    return context


def relabel_saved_list_column_visibility(view):
    """Replace stored ``cf_*`` labels with the definition name after save."""
    request = getattr(view, "request", None)
    if request is None:
        return
    app_label = request.POST.get("app_label")
    model_name = request.POST.get("model_name")
    url_name = request.POST.get("url_name")
    if model_name:
        model_name = model_name.strip('"')
        if "." in model_name:
            model_name = model_name.split(".")[-1]
    if not app_label or not model_name:
        return

    from horilla.contrib.generics.views.helpers.list_column import _get_path_context

    path_context = _get_path_context(request)
    visibility = ListColumnVisibility.all_objects.filter(
        user=request.user,
        app_label=app_label,
        model_name=model_name,
        context=path_context,
        url_name=url_name,
    ).first()
    if visibility is None:
        return

    visibility.visible_fields = relabel_custom_field_pairs(visibility.visible_fields)
    visibility.removed_custom_fields = relabel_custom_field_pairs(
        visibility.removed_custom_fields
    )
    visibility.save(update_fields=["visible_fields", "removed_custom_fields"])

    cache_key = (
        f"visible_columns_{request.user.id}_{app_label}_{model_name}_"
        f"{path_context}_{url_name}"
    )
    cache.delete(cache_key)


def attach_custom_field_values_to_objects(model, objects, extras=None):
    """Set ``cf_<id>`` attributes on each object so list cells can render."""
    if extras is None:
        extras = custom_field_selector_items(model)
    if not extras:
        return

    items = []
    for obj in objects or []:
        if getattr(obj, "pk", None) is not None:
            items.append(obj)
    if not items:
        return

    keys = [item[1] for item in extras]
    for obj in items:
        for key in keys:
            setattr(obj, key, "")

    ct = HorillaContentType.objects.get_for_model(model)
    pks = [obj.pk for obj in items]
    definitions = list(get_custom_field_definitions(model))
    values = CustomFieldValue.objects.filter(
        content_type=ct,
        object_id__in=pks,
        field_definition__in=definitions,
    ).select_related("field_definition")

    by_pk = {}
    for cfv in values:
        key = custom_field_form_name(cfv.field_definition)
        val = cfv.get_value()
        by_pk.setdefault(cfv.object_id, {})[key] = "" if val is None else str(val)

    for obj in items:
        for key, val in by_pk.get(obj.pk, {}).items():
            setattr(obj, key, val)


def attach_custom_fields_to_list_context(view, context):
    """Attach values on the current page and skip sorting on ``cf_*`` columns."""
    model = getattr(view, "model", None)
    if model is None:
        return context
    extras = custom_field_selector_items(model)
    objects = context.get("queryset")
    if objects is None:
        objects = context.get("object_list")
    attach_custom_field_values_to_objects(model, objects, extras=extras)
    if extras:
        exclude = list(context.get("exclude_columns_from_sorting") or [])
        for _, name in extras:
            if name not in exclude:
                exclude.append(name)
        context["exclude_columns_from_sorting"] = exclude
    return context


def _patch_column_selection_form():
    """Include ``cf_*`` in column-form choices so save does not drop them."""
    from horilla.contrib.generics.forms.generics import ColumnSelectionForm

    if getattr(ColumnSelectionForm.__init__, "_custom_fields_patched", False):
        return

    original_init = ColumnSelectionForm.__init__

    def patched_init(self, *args, **kwargs):
        model = kwargs.get("model")
        original_data = kwargs.get("data")
        if original_data is None and args:
            original_data = args[0]
        original_init(self, *args, **kwargs)
        if model is None:
            return
        extras = custom_field_selector_items(model)
        if not extras:
            return
        extra_by_name = {name: force_str(label) for label, name in extras}
        field = self.fields.get("visible_fields")
        if field is not None:
            existing = {choice[0] for choice in field.choices}
            new_choices = list(field.choices)
            for name, label in extra_by_name.items():
                if name not in existing:
                    new_choices.append((name, label))
            field.choices = new_choices
        if original_data is None or not hasattr(original_data, "getlist"):
            return
        if field is None or getattr(self, "data", None) is None:
            return
        allowed = {choice[0] for choice in field.choices}
        posted = original_data.getlist("visible_fields")
        kept = [name for name in posted if name in allowed]
        current = (
            list(self.data.getlist("visible_fields"))
            if hasattr(self.data, "getlist")
            else []
        )
        if kept == current:
            return
        data = self.data.copy()
        if hasattr(data, "setlist"):
            data.setlist("visible_fields", kept)
        else:
            data["visible_fields"] = kept
        self.data = data

    patched_init._custom_fields_patched = True
    ColumnSelectionForm.__init__ = patched_init


def install_list_column_patches():
    """Monkey-patch Horilla list-column helpers without editing their files."""
    global _PATCHED
    if _PATCHED:
        return

    from horilla.contrib.generics.views.helpers.list_column import (
        ListColumnSelectFormView,
    )
    from horilla.contrib.generics.views.list import HorillaListView

    _patch_column_selection_form()

    original_get_context_data = ListColumnSelectFormView.get_context_data
    original_form_valid = ListColumnSelectFormView.form_valid
    original_list_get_context_data = HorillaListView.get_context_data

    def patched_get_context_data(self, **kwargs):
        context = original_get_context_data(self, **kwargs)
        try:
            inject_custom_fields_into_column_selector(context)
        except Exception:
            logger.exception("custom_fields: could not inject list columns")
        return context

    def patched_form_valid(self, form):
        response = original_form_valid(self, form)
        try:
            relabel_saved_list_column_visibility(self)
        except Exception:
            logger.exception("custom_fields: could not relabel saved list columns")
        return response

    def patched_list_get_context_data(self, **kwargs):
        context = original_list_get_context_data(self, **kwargs)
        try:
            attach_custom_fields_to_list_context(self, context)
        except Exception:
            logger.exception("custom_fields: could not attach list custom fields")
        return context

    ListColumnSelectFormView.get_context_data = patched_get_context_data
    ListColumnSelectFormView.form_valid = patched_form_valid
    HorillaListView.get_context_data = patched_list_get_context_data
    _PATCHED = True
