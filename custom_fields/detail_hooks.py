"""
Runtime hooks for Horilla detail-field picker and inline field edit.

Horilla's selector and ``get_field`` paths only know about model columns.
This module patches those call sites from the custom_fields app so we do not
edit Horilla sources.
"""

import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.utils.encoding import force_str

from horilla.apps import apps
from horilla.contrib.generics.views.helpers.edit_field import (
    EditFieldView,
    UpdateFieldView,
)
from horilla.shortcuts import get_object_or_404, render
from horilla.utils.translation import gettext_lazy as _
from horilla.web import HttpResponse, ScriptResponse

from custom_fields.models import CustomFieldDefinition
from custom_fields.utils import (
    INLINE_FIELD_TYPES,
    custom_field_form_name,
    get_custom_field_definitions,
    get_definition_by_form_name,
    is_custom_field_name,
    load_custom_field_values,
    parse_custom_field_pk,
    save_custom_field_values,
)

logger = logging.getLogger(__name__)

_PATCHED = False


def field_names_from_list(fields_list):
    """Extract field names from ``[[verbose, name], ...]`` or name strings."""
    names = []
    for item in fields_list or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            names.append(str(item[1]))
        else:
            names.append(str(item))
    return names


def relabel_custom_field_pairs(fields_list):
    """Replace stored ``cf_*`` labels with the definition name."""
    pairs = list(fields_list or [])
    pks = []
    for item in pairs:
        if not (isinstance(item, (list, tuple)) and len(item) >= 2):
            continue
        pk = parse_custom_field_pk(item[1])
        if pk is not None:
            pks.append(pk)
    if not pks:
        return pairs
    labels = {
        custom_field_form_name(defn): defn.name
        for defn in CustomFieldDefinition.objects.filter(pk__in=pks)
    }
    relabeled = []
    for item in pairs:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            name = str(item[1])
            verbose = labels.get(name, item[0])
            relabeled.append([force_str(verbose), name])
        else:
            relabeled.append(item)
    return relabeled


def custom_field_selector_items(model):
    """Return ``[[name, cf_<id>], ...]`` for the model's active definitions."""
    return [
        [defn.name, custom_field_form_name(defn)]
        for defn in get_custom_field_definitions(model)
    ]


def inject_custom_fields_into_selector_context(context, request=None):
    """
    Add custom fields to the Change Detail View Fields modal lists.

    Selected columns keep saved order; unsaved custom fields appear in
    the matching Available list (header and details).
    """
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

    header_fields = relabel_custom_field_pairs(context.get("header_fields"))
    details_fields = relabel_custom_field_pairs(context.get("details_fields"))
    header_available = relabel_custom_field_pairs(context.get("header_available"))
    details_available = relabel_custom_field_pairs(context.get("details_available"))

    header_selected = set(field_names_from_list(header_fields))
    details_selected = set(field_names_from_list(details_fields))
    header_avail_names = set(field_names_from_list(header_available))
    details_avail_names = set(field_names_from_list(details_available))

    for item in extras:
        key = item[1]
        if key not in header_selected and key not in header_avail_names:
            header_available.append(item)
            header_avail_names.add(key)
        if key not in details_selected and key not in details_avail_names:
            details_available.append(item)
            details_avail_names.add(key)

    context["header_fields"] = header_fields
    context["details_fields"] = details_fields
    context["header_available"] = header_available
    context["details_available"] = details_available
    return context


def append_custom_fields_to_defaults(model, default_header, default_details):
    """Put custom fields in the default Details-tab selected list."""
    extras = custom_field_selector_items(model)
    if not extras:
        return default_header, default_details
    header_names = set(field_names_from_list(default_header))
    details_names = set(field_names_from_list(default_details))
    details = list(default_details or [])
    for item in extras:
        key = item[1]
        if key not in details_names and key not in header_names:
            details.append(item)
            details_names.add(key)
    return default_header, details


def install_detail_field_patches():
    """Monkey-patch Horilla detail-field helpers without editing their files."""
    global _PATCHED
    if _PATCHED:
        return

    from horilla.contrib.generics.views.helpers import detail_field as detail_field_mod

    original_render = detail_field_mod.render
    original_defaults = detail_field_mod._get_detail_field_defaults
    original_ensure = detail_field_mod._ensure_json_serializable

    def patched_render(request, template_name, context=None, *args, **kwargs):
        if template_name == "add_field_to_detail.html" and context is not None:
            inject_custom_fields_into_selector_context(context, request)
        return original_render(request, template_name, context, *args, **kwargs)

    def patched_defaults(model, request):
        default_header, default_details = original_defaults(model, request)
        try:
            return append_custom_fields_to_defaults(
                model, default_header, default_details
            )
        except Exception:
            logger.exception("custom_fields: could not add defaults for %s", model)
            return default_header, default_details

    def patched_ensure(fields_list):
        return relabel_custom_field_pairs(original_ensure(fields_list))

    detail_field_mod.render = patched_render
    detail_field_mod._get_detail_field_defaults = patched_defaults
    detail_field_mod._ensure_json_serializable = patched_ensure
    _PATCHED = True


def build_custom_field_info(definition, obj):
    """Build the ``field_info`` dict Horilla's edit/display partials expect."""
    key = custom_field_form_name(definition)
    values = load_custom_field_values(obj.__class__, obj.pk)
    value = values.get(key)
    if value is None:
        value = ""
    info = {
        "name": key,
        "verbose_name": definition.name,
        "field_type": INLINE_FIELD_TYPES.get(definition.field_type, "text"),
        "value": value,
        "choices": [],
        "display_value": "" if value in (None, "") else str(value),
        "use_select2": False,
        "input_attrs": {},
    }
    if definition.field_type == "choice":
        info["choices"] = [{"value": "", "label": "---------"}]
        info["choices"].extend(
            {"value": choice, "label": choice}
            for choice in definition.get_choices_list()
        )
    if definition.field_type == "number":
        info["step"] = "0.0001"
    return info


def _load_object_for_inline_edit(request, pk, app_label, model_name, perm_kind):
    model = apps.get_model(app_label, model_name)
    perm = f"{model._meta.app_label}.{perm_kind}_{model._meta.model_name}"
    if not request.user.has_perm(perm):
        return None, model, False
    return get_object_or_404(model, pk=pk), model, True


def _render_custom_field_edit(request, pk, field_info, app_label, model_name):
    return render(
        request,
        EditFieldView.template_name,
        {
            "object_id": pk,
            "field_info": field_info,
            "app_label": app_label,
            "model_name": model_name,
            "pipeline_field": request.GET.get("pipeline_field"),
        },
    )


def _render_custom_field_display(request, pk, field_info, app_label, model_name):
    return render(
        request,
        UpdateFieldView.template_name,
        {
            "object_id": pk,
            "field_info": field_info,
            "app_label": app_label,
            "model_name": model_name,
        },
    )


def handle_custom_field_edit_get(request, pk, field_name, app_label, model_name):
    """Render the inline editor for a ``cf_*`` field."""
    try:
        obj, model, allowed = _load_object_for_inline_edit(
            request, pk, app_label, model_name, "change"
        )
        if not allowed:
            messages.error(request, _("You do not have permission to edit this."))
            return ScriptResponse(reload=True)
        definition = get_definition_by_form_name(model, field_name)
        if definition is None:
            return HttpResponse(status=404)
        field_info = build_custom_field_info(definition, obj)
    except Exception as exc:
        messages.error(request, exc)
        return ScriptResponse(reload=True)
    return _render_custom_field_edit(request, pk, field_info, app_label, model_name)


def handle_custom_field_update_post(request, pk, field_name, app_label, model_name):
    """Save a ``cf_*`` inline edit and return the display partial."""
    try:
        obj, model, allowed = _load_object_for_inline_edit(
            request, pk, app_label, model_name, "change"
        )
        if not allowed:
            messages.error(request, _("You do not have permission to edit this."))
            return ScriptResponse(reload=True, status=403)
        definition = get_definition_by_form_name(model, field_name)
        if definition is None:
            return HttpResponse(status=404)
    except Exception as exc:
        messages.error(request, exc)
        return ScriptResponse(reload=True)

    raw_value = request.POST.get(field_name, "")
    error_message = _validate_inline_value(definition, raw_value)
    if error_message:
        field_info = build_custom_field_info(definition, obj)
        field_info["error"] = error_message
        field_info["value"] = raw_value
        field_info["display_value"] = raw_value
        return _render_custom_field_edit(
            request, pk, field_info, app_label, model_name
        )

    save_custom_field_values(
        model,
        obj.pk,
        {field_name: raw_value},
        company=getattr(obj, "company", None),
    )
    obj.refresh_from_db()
    field_info = build_custom_field_info(definition, obj)
    return _render_custom_field_display(
        request, pk, field_info, app_label, model_name
    )


def handle_custom_field_cancel_get(request, pk, field_name, app_label, model_name):
    """Return the display partial without saving."""
    try:
        obj, model, allowed = _load_object_for_inline_edit(
            request, pk, app_label, model_name, "view"
        )
        if not allowed:
            messages.error(request, _("You do not have permission to view this."))
            return ScriptResponse(reload=True)
        definition = get_definition_by_form_name(model, field_name)
        if definition is None:
            return HttpResponse(status=404)
        field_info = build_custom_field_info(definition, obj)
    except Exception as exc:
        messages.error(request, exc)
        return ScriptResponse(reload=True)
    return _render_custom_field_display(
        request, pk, field_info, app_label, model_name
    )


def _validate_inline_value(definition, raw_value):
    if definition.is_required and str(raw_value).strip() == "":
        return str(_("This field is required."))
    if definition.field_type == "number" and str(raw_value).strip() != "":
        try:
            Decimal(str(raw_value))
        except (InvalidOperation, ValueError):
            return str(_("Enter a valid number."))
    if definition.field_type == "choice" and str(raw_value).strip() != "":
        choices = definition.get_choices_list()
        if str(raw_value) not in choices:
            return str(_("Select a valid choice."))
    return None
