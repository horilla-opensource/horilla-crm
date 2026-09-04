"""
User picker views for horilla.contrib.generics.

Provides HTMX endpoints for the user picker modal:
 - UserPickerFilterView  : filter panel (add row / field change / operator change)
 - UserPickerListView    : paginated list of items with search + filter applied
"""

# Standard library imports
import importlib
import logging

# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.views import View

# First party imports (Horilla)
from horilla.apps import apps
from horilla.shortcuts import render
from horilla.utils.choices import FIELD_TYPE_MAP
from horilla.web import HttpResponse

logger = logging.getLogger(__name__)


def _get_model_fields(model):
    """Return filter-field metadata for a model."""
    from horilla.contrib.generics.filters import HorillaFilterSet

    fields = []
    for field in model._meta.fields:
        field_class = field.__class__.__name__
        if field.choices:
            ftype = "choice"
            choices = [{"value": v, "label": l} for v, l in field.choices]
        elif field_class == "ForeignKey":
            ftype = "foreignkey"
            choices = []
        elif field_class == "DateTimeField":
            ftype = "datetime"
            choices = []
        elif field_class == "DateField":
            ftype = "date"
            choices = []
        elif field_class == "BooleanField":
            ftype = "boolean"
            choices = [
                {"value": "True", "label": "Yes"},
                {"value": "False", "label": "No"},
            ]
        else:
            ftype = FIELD_TYPE_MAP.get(field_class, "other")
            choices = []

        operators = HorillaFilterSet.get_operators_for_field(ftype)
        fields.append(
            {
                "name": field.name,
                "verbose_name": str(field.verbose_name),
                "type": ftype,
                "choices": choices,
                "operators": operators,
                "model": (
                    field.related_model.__name__ if ftype == "foreignkey" else None
                ),
                "app_label": (
                    field.related_model._meta.app_label
                    if ftype == "foreignkey"
                    else None
                ),
            }
        )
    return fields


def _build_row_q(model, fname, op, index, values, starts, ends):
    """Build a Q object for one filter row, or None if the row can't be built."""
    from horilla.contrib.generics.filters import STRING_LIKE_FIELDS

    if op == "ne":
        v = values[index] if index < len(values) else None
        return ~Q(**{fname: v}) if v is not None else None
    if op == "between":
        s = starts[index] if index < len(starts) else None
        e = ends[index] if index < len(ends) else None
        if s and e:
            return Q(**{f"{fname}__gte": s, f"{fname}__lte": e})
        if s:
            return Q(**{f"{fname}__gte": s})
        if e:
            return Q(**{f"{fname}__lte": e})
        return None
    if op == "isnull":
        try:
            fobj = model._meta.get_field(fname)
        except Exception:
            fobj = None
        if fobj is not None and isinstance(fobj, STRING_LIKE_FIELDS):
            return Q(**{f"{fname}__isnull": True}) | Q(**{f"{fname}__exact": ""})
        return Q(**{f"{fname}__isnull": True})
    if op == "isnotnull":
        try:
            fobj = model._meta.get_field(fname)
        except Exception:
            fobj = None
        if fobj is not None and isinstance(fobj, STRING_LIKE_FIELDS):
            return ~Q(**{f"{fname}__isnull": True}) & ~Q(**{f"{fname}__exact": ""})
        return Q(**{f"{fname}__isnull": False})
    return None


def _apply_filters(queryset, request):
    """Apply field/operator/value/logic rows from GET params to queryset (AND/OR combined)."""
    from horilla.contrib.generics.filters import (
        OPERATOR_CHOICES,
        RELATIVE_DATE_OPERATORS,
        HorillaFilterSet,
    )

    valid_operators = {op for ops in OPERATOR_CHOICES.values() for op, _ in ops}
    valid_logics = {"AND", "OR"}

    fields = request.GET.getlist("field")
    operators = request.GET.getlist("operator")
    values = request.GET.getlist("value")
    starts = request.GET.getlist("start_value")
    ends = request.GET.getlist("end_value")
    logics = request.GET.getlist("logic")

    model = queryset.model
    combined_q = None

    for i, (fname, op) in enumerate(zip(fields, operators)):
        if not fname or op not in valid_operators:
            continue
        try:
            if op in RELATIVE_DATE_OPERATORS:
                queryset = HorillaFilterSet()._apply_relative_date_filter(
                    queryset, fname, op
                )
                continue
            if op not in ("ne", "between", "isnull", "isnotnull"):
                v = values[i] if i < len(values) else None
                row_q = Q(**{f"{fname}__{op}": v}) if v is not None else None
            else:
                row_q = _build_row_q(model, fname, op, i, values, starts, ends)
        except Exception:
            continue

        if row_q is None:
            continue

        logic = logics[i] if i < len(logics) else "AND"
        if logic not in valid_logics:
            logic = "AND"

        if combined_q is None:
            combined_q = row_q
        elif logic == "OR":
            combined_q = combined_q | row_q
        else:
            combined_q = combined_q & row_q

    if combined_q is not None:
        queryset = queryset.filter(combined_q)

    return queryset


class UserPickerModalView(LoginRequiredMixin, View):
    """Returns full modal content for the user picker, loaded into horillaModalBox via hx-get."""

    def get(self, request, **kwargs):
        """Render the full user-picker modal shell for HTMX injection."""
        app_label = kwargs.get("app_label")
        model_name = kwargs.get("model_name")
        field_id = request.GET.get("field_id", "")
        field_label = request.GET.get("field_label", "Select")
        form_class = request.GET.get("form_class", "")
        field_name = request.GET.get("field_name", "")
        object_id = request.GET.get("object_id", "")

        try:
            apps.get_model(app_label=app_label, model_name=model_name)
        except LookupError:
            return HttpResponse("Model not found", status=404)

        extra_qs = ""
        if form_class and field_name:
            from urllib.parse import urlencode

            qs_params = {"form_class": form_class, "field_name": field_name}
            if object_id:
                qs_params["object_id"] = object_id
            extra_qs = "?" + urlencode(qs_params)

        context = {
            "field_id": field_id,
            "field_label": field_label,
            "list_url": f"/generics/user-picker-list/{app_label}/{model_name}/{extra_qs}",
            "filter_url": f"/generics/user-picker-filter/{app_label}/{model_name}/",
            "app_label": app_label,
            "model_name": model_name,
        }
        return render(request, "partials/user_picker_modal.html", context)


class UserPickerListView(LoginRequiredMixin, View):
    """
    HTMX endpoint: returns a paginated HTML list of model items for the user picker modal.
    Accepts: search, field[], operator[], value[], start_value[], end_value[], page.
    """

    def _resolve_queryset(self, request, model):
        """Try to get a filtered queryset from the form field's queryset, fall back to all()."""
        from .select2 import _is_allowed_import_module_path

        form_class_path = request.GET.get("form_class", "").strip()
        field_name = request.GET.get("field_name", "").strip()
        object_id = request.GET.get("object_id", "").strip()
        if form_class_path and field_name:
            try:
                module_path, class_name = form_class_path.rsplit(".", 1)
                if _is_allowed_import_module_path(module_path):
                    module = importlib.import_module(module_path)
                    form_class = getattr(module, class_name)
                    form_kwargs = {"request": request}
                    if (
                        object_id
                        and hasattr(form_class, "_meta")
                        and hasattr(form_class._meta, "model")
                    ):
                        parent_model = form_class._meta.model
                        try:
                            form_kwargs["instance"] = parent_model.all_objects.get(
                                pk=object_id
                            )
                        except (parent_model.DoesNotExist, ValueError):
                            pass
                    form = form_class(**form_kwargs)
                    if field_name in form.fields:
                        qs = getattr(form.fields[field_name], "queryset", None)
                        if qs is not None:
                            return qs
            except Exception as e:
                logger.debug("[UserPicker] Could not resolve queryset from form: %s", e)
        return model.objects.all()

    def get(self, request, **kwargs):
        """Return a paginated HTML list slice for the picker, with search and filters applied."""
        app_label = kwargs.get("app_label")
        model_name = kwargs.get("model_name")

        try:
            model = apps.get_model(app_label=app_label, model_name=model_name)
        except LookupError:
            return HttpResponse("Model not found", status=404)

        queryset = self._resolve_queryset(request, model)

        # Apply search
        search = request.GET.get("search", "").strip()
        if search:
            matched_pks = [
                obj.pk for obj in queryset if search.lower() in str(obj).lower()
            ]
            queryset = queryset.filter(pk__in=matched_pks)

        # Apply filters
        queryset = _apply_filters(queryset, request)

        # Pagination
        per_page = 20
        try:
            page = int(request.GET.get("page", 1))
        except ValueError:
            page = 1

        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)

        items = [{"id": obj.pk, "text": str(obj)} for obj in page_obj.object_list]

        context = {
            "items": items,
            "page_obj": page_obj,
            "app_label": app_label,
            "model_name": model_name,
        }
        return render(request, "partials/user_picker_list.html", context)


class UserPickerFilterView(LoginRequiredMixin, View):
    """
    HTMX endpoint for the user picker modal filter panel.
    Handles: add_filter_row, field_change, operator_change, initial row render.
    """

    def get(self, request, **kwargs):
        """Render filter rows or field/operator UI fragments for the user picker."""
        app_label = kwargs.get("app_label")
        model_name = kwargs.get("model_name")

        try:
            model = apps.get_model(app_label=app_label, model_name=model_name)
        except LookupError:
            return HttpResponse("Model not found", status=404)

        filter_url = request.path
        filter_fields = _get_model_fields(model)

        # ── Add a new empty row ───────────────────────────────────────────────
        if request.GET.get("add_filter_row") == "true":
            row_id = int(request.GET.get("row_id", 0)) + 1
            context = {
                "filter_rows": [
                    {
                        "row_id": row_id,
                        "field": None,
                        "operator": None,
                        "value": None,
                        "logic": "AND",
                        "operators": [],
                        "type": None,
                        "choices": [],
                    }
                ],
                "filter_fields": filter_fields,
                "up_filter_url": filter_url,
                "is_appended_row": True,
            }
            return render(request, "partials/user_picker_filter_row.html", context)

        # ── Field changed → return new operator select ────────────────────────
        if request.GET.get("field_change") == "true":
            field_name = request.GET.get("field", "")
            row_id = request.GET.get("row_id", "0")
            field_info = next(
                (f for f in filter_fields if f["name"] == field_name), None
            )
            operators = field_info["operators"] if field_info else []
            context = {
                "operators": operators,
                "field_name": field_name,
                "row_id": row_id,
                "up_filter_url": filter_url,
            }
            return render(request, "partials/user_picker_operator_select.html", context)

        # ── Operator changed → return new value field ─────────────────────────
        if request.GET.get("operator_change") == "true":
            field_name = request.GET.get("field", "")
            operator = request.GET.get("operator", "")
            row_id = request.GET.get("row_id", "0")
            field_info = next(
                (f for f in filter_fields if f["name"] == field_name), None
            )
            context = {
                "field_info": field_info or {},
                "operator": operator,
                "row_id": row_id,
                "app_label": app_label,
                "model_name": model_name,
            }
            return render(request, "partials/user_picker_value_field.html", context)

        # ── Initial render (row 0) ────────────────────────────────────────────
        context = {
            "filter_rows": [
                {
                    "row_id": 0,
                    "field": None,
                    "operator": None,
                    "value": None,
                    "logic": "AND",
                    "operators": [],
                    "type": None,
                    "choices": [],
                }
            ],
            "filter_fields": filter_fields,
            "up_filter_url": filter_url,
        }
        return render(request, "partials/user_picker_filter_row.html", context)
