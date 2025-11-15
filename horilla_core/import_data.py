# views.py
import csv
import difflib
import json
import logging
import os
import time
import traceback
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from functools import cached_property
from io import StringIO

import pandas as pd
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connection, transaction
from django.db.models import CharField, ForeignKey
from django.forms.models import model_to_dict
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, View

from horilla.exceptions import HorillaHttp404
from horilla.registry.feature import FEATURE_REGISTRY
from horilla_core.decorators import htmx_required, permission_required_or_denied
from horilla_core.models import ImportHistory
from horilla_generics.views import HorillaListView, HorillaTabView

logger = logging.getLogger(__name__)


class ImportView(LoginRequiredMixin, TemplateView):

    template_name = "import/import_view.html"


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class ImportTabView(LoginRequiredMixin, HorillaTabView):
    """
    A generic class-based view for rendering the company information settings page.
    """

    view_id = "import-data-view"
    background_class = "bg-primary-100 rounded-md"
    tabs = [
        {
            "title": _("Import Data"),
            "url": reverse_lazy("horilla_core:import_data"),
            "target": "import-view-content",
            "id": "import-view",
        },
        {
            "title": _("Import History"),
            "url": reverse_lazy("horilla_core:import_history_view"),
            "target": "import-history-view-content",
            "id": "import-history-view",
        },
    ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class ImportDataView(TemplateView):
    template_name = "import/import_data.html"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        single_import = request.GET.get("single_import", "false").lower() == "true"
        model_name = request.GET.get("model_name", "")
        app_label = self.request.GET.get("app_label", "")

        if single_import:
            request.session.pop("import_data", None)
            request.session["import_config"] = {
                "single_import": True,
                "model_name": model_name,
                "app_label": app_label,
            }
            context["selected_module"] = model_name
        else:
            request.session.pop("import_config", None)
            import_data = request.session.get("import_data", {})
            if import_data:
                context["selected_module"] = import_data.get("module", "")
                context["selected_import_name"] = import_data.get("import_name", "")
                context["selected_filename"] = import_data.get("original_filename", "")

        context["single_import"] = single_import
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modules"] = self.get_available_models()
        return context

    def get_available_models(self):
        single_import = self.request.GET.get("single_import", "false").lower() == "true"
        import_config = self.request.session.get("import_config", {})
        model_name = self.request.GET.get("model_name", "") or import_config.get(
            "model_name", ""
        )
        app_label = self.request.GET.get("app_label", "") or import_config.get(
            "app_label", ""
        )

        models = []

        try:
            import_models = FEATURE_REGISTRY.get("import_models", [])

            if single_import and model_name and app_label:
                # Look up model in registry for single import
                model = next(
                    (
                        m
                        for m in import_models
                        if m._meta.model_name == model_name.lower()
                        and m._meta.app_label == app_label
                    ),
                    None,
                )
                if model:
                    models.append(self._format_model_info(model))
                else:
                    logger.warning(
                        f"Model {app_label}.{model_name} not found or not registered for import."
                    )
            else:
                # Return all registered importable models
                for model in import_models:
                    models.append(self._format_model_info(model))
        except Exception as e:
            logger.error(f"Error getting available models: {e}")

        return models

    def _format_model_info(self, model):
        return {
            "name": model.__name__,
            "label": model._meta.verbose_name.title(),
            "app_label": model._meta.app_label,
            "module": model.__module__,
        }


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class ImportStep1View(View):
    """Handle file upload and module selection"""

    def get(self, request, *args, **kwargs):
        """Handle navigation back to step 2"""
        import_data = request.session.get("import_data", {})
        if not import_data:
            return redirect("horilla_core:import_data")

    def post(self, request, *args, **kwargs):
        import_config = request.session.get("import_config", {})
        single_import = import_config.get("single_import", False)
        restricted_model_name = import_config.get("model_name", "")
        restricted_app_label = import_config.get("app_label", "")

        module = request.POST.get("module")
        import_name = request.POST.get("import_name")
        uploaded_file = request.FILES.get("file")

        if single_import:
            if module != restricted_model_name:
                view = ImportDataView()
                view.request = request
                modules = []
                try:
                    model = apps.get_model(restricted_app_label, restricted_model_name)
                    modules = [
                        {
                            "name": model.__name__,
                            "label": model._meta.verbose_name.title(),
                            "app_label": model._meta.app_label,
                            "module": model.__module__,
                        }
                    ]
                except LookupError:
                    logger.error(
                        f"Model {restricted_app_label}.{restricted_model_name} not found"
                    )
                context = {
                    "modules": modules,
                    "error_message": "Invalid module. Choose one of the available choice",
                    "single_import": single_import,
                    "selected_module": restricted_model_name,
                    "selected_import_name": import_name,  # Preserve user input
                }
                return render(request, "import/import_data.html", context)

        # Check if we have existing import data (back navigation scenario)
        existing_import_data = request.session.get("import_data", {})

        # For back navigation, we might not have a new file upload
        if existing_import_data and not uploaded_file:
            # Use existing file data if available
            existing_file_path = existing_import_data.get("file_path")
            existing_filename = existing_import_data.get("original_filename")

            if not all([module, import_name]):
                return HttpResponse(
                    """
                    <div class="text-red-500 text-sm">Module and Import Name are required</div>
                """
                )

            if existing_file_path and existing_filename:
                # Update session with new module/import_name but keep existing file
                existing_import_data.update(
                    {
                        "module": module,
                        "import_name": import_name,
                    }
                )
                request.session["import_data"] = existing_import_data

                # Get fresh data based on new module selection
                try:
                    app_label = self.get_app_label_for_model(module)
                    existing_import_data["app_label"] = app_label
                    request.session["import_data"] = existing_import_data

                    model_fields = self.get_model_fields(module, app_label)
                    if not model_fields:
                        return HttpResponse(
                            f"""
                            <div class="text-red-500 text-sm">No valid fields found for the selected model: {module}</div>
                        """
                        )

                    headers = existing_import_data.get("headers", [])
                    sample_data = existing_import_data.get("sample_data", [])
                    unique_values = existing_import_data.get("unique_values", {})

                    auto_mappings = self.auto_map_fields(headers, model_fields)
                    choice_mappings, fk_mappings = self.auto_map_values(
                        unique_values, model_fields, auto_mappings, app_label
                    )

                    if "field_mappings" not in existing_import_data:
                        existing_import_data["auto_mappings"] = auto_mappings
                    if "choice_mappings" not in existing_import_data:
                        existing_import_data["auto_choice_mappings"] = choice_mappings
                    if "fk_mappings" not in existing_import_data:
                        existing_import_data["auto_fk_mappings"] = fk_mappings

                    request.session["import_data"] = existing_import_data

                    return render(
                        request,
                        "import/import_step2.html",
                        {
                            "headers": headers,
                            "sample_data": sample_data,
                            "model_fields": model_fields,
                            "module": module,
                            "app_label": app_label,
                            "auto_mappings": existing_import_data.get(
                                "auto_mappings", {}
                            ),
                            "auto_choice_mappings": existing_import_data.get(
                                "auto_choice_mappings", {}
                            ),
                            "auto_fk_mappings": existing_import_data.get(
                                "auto_fk_mappings", {}
                            ),
                            "replace_values": existing_import_data.get(
                                "replace_values", {}
                            ),
                            "single_import": single_import,
                            "selected_module": restricted_model_name,
                        },
                    )
                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(tb)
                    return HttpResponse(
                        f"""
                        <div class="text-red-500 text-sm">Error processing module change: {str(e)}</div>
                    """
                    )

        # Original validation for new uploads
        if not all([module, import_name, uploaded_file]):
            return HttpResponse(
                """
                <div class="text-red-500 text-sm">All fields are required</div>
            """
            )

        if not uploaded_file.name.endswith((".csv", ".xlsx", ".xls")):
            return HttpResponse(
                """
                <div class="text-red-500 text-sm">Please upload a CSV or Excel file</div>
            """
            )

        try:
            app_label = self.get_app_label_for_model(module)
            file_path = default_storage.save(
                f"imports/{uploaded_file.name}", ContentFile(uploaded_file.read())
            )

            # Store minimal session data
            request.session["import_data"] = {
                "module": module,
                "import_name": import_name,
                "file_path": file_path,
                "original_filename": uploaded_file.name,
                "app_label": app_label,
            }

            # Parse file
            headers = self.get_file_headers(file_path)
            sample_data = self.get_sample_data(file_path)
            unique_values = self.get_unique_file_values(file_path, headers)

            # Store headers, sample data, and unique values in session
            request.session["import_data"]["headers"] = headers
            request.session["import_data"]["sample_data"] = sample_data[:1]
            request.session["import_data"]["unique_values"] = unique_values

            model_fields = self.get_model_fields(module, app_label)
            if not model_fields:
                return HttpResponse(
                    f"""
                    <div class="text-red-500 text-sm">No valid fields found for the selected model: {module}</div>
                """
                )

            # Auto-map fields
            auto_mappings = self.auto_map_fields(headers, model_fields)

            # Auto-map choice and foreign key values
            choice_mappings, fk_mappings = self.auto_map_values(
                unique_values, model_fields, auto_mappings, app_label
            )

            # Store auto-mappings in session for later use
            request.session["import_data"]["auto_mappings"] = auto_mappings
            request.session["import_data"]["auto_choice_mappings"] = choice_mappings
            request.session["import_data"]["auto_fk_mappings"] = fk_mappings

            return render(
                request,
                "import/import_step2.html",
                {
                    "headers": headers,
                    "sample_data": sample_data,
                    "model_fields": model_fields,
                    "module": module,
                    "app_label": app_label,
                    "auto_mappings": auto_mappings,
                    "auto_choice_mappings": choice_mappings,
                    "auto_fk_mappings": fk_mappings,
                    "single_import": single_import,
                    "selected_module": restricted_model_name,
                },
            )
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(tb)
            return HttpResponse(
                f"""
                <div class="text-red-500 text-sm">Error processing file: {str(e)}</div>
            """
            )

    def auto_map_fields(self, headers, model_fields):
        """Automatically map file headers to model fields using fuzzy matching"""
        auto_mappings = {}

        # Normalize headers and field names for better matching
        def normalize_text(text):
            return text.lower().replace("_", " ").replace("-", " ").strip()

        # Create normalized mappings
        normalized_headers = {normalize_text(header): header for header in headers}
        normalized_fields = {
            normalize_text(field["name"]): field["name"] for field in model_fields
        }
        normalized_verbose = {
            normalize_text(field["verbose_name"]): field["name"]
            for field in model_fields
        }

        # Direct exact matches (normalized)
        for norm_header, original_header in normalized_headers.items():
            if norm_header in normalized_fields:
                auto_mappings[normalized_fields[norm_header]] = original_header
            elif norm_header in normalized_verbose:
                auto_mappings[normalized_verbose[norm_header]] = original_header

        # Fuzzy matching for remaining fields
        mapped_headers = set(auto_mappings.values())
        unmapped_headers = [h for h in headers if h not in mapped_headers]
        mapped_fields = set(auto_mappings.keys())
        unmapped_fields = [
            f["name"] for f in model_fields if f["name"] not in mapped_fields
        ]

        for header in unmapped_headers:
            norm_header = normalize_text(header)
            best_match = None
            best_ratio = 0.6  # Minimum similarity threshold

            # Check against field names
            for field_name in unmapped_fields:
                norm_field = normalize_text(field_name)
                ratio = difflib.SequenceMatcher(None, norm_header, norm_field).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = field_name

            # Check against verbose names if no good field name match
            if not best_match:
                for field in model_fields:
                    if field["name"] in unmapped_fields:
                        norm_verbose = normalize_text(field["verbose_name"])
                        ratio = difflib.SequenceMatcher(
                            None, norm_header, norm_verbose
                        ).ratio()
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_match = field["name"]

            if best_match:
                auto_mappings[best_match] = header
                unmapped_fields.remove(best_match)

        return auto_mappings

    def auto_map_values(self, unique_values, model_fields, field_mappings, app_label):
        """Automatically map choice field and foreign key values"""
        choice_mappings = {}
        fk_mappings = {}

        for field in model_fields:
            field_name = field["name"]

            # Only process fields that are mapped
            if field_name not in field_mappings:
                continue

            file_header = field_mappings[field_name]
            file_values = unique_values.get(file_header, [])

            if not file_values:
                continue

            # Handle choice fields
            if field["is_choice_field"]:
                choice_dict = {
                    choice["value"]: choice["label"] for choice in field["choices"]
                }
                field_choice_mappings = {}

                for file_value in file_values:
                    best_match = self.find_best_choice_match(file_value, choice_dict)
                    if best_match:
                        slug_value = slugify(file_value)
                        field_choice_mappings[slug_value] = best_match

                if field_choice_mappings:
                    choice_mappings[field_name] = field_choice_mappings

            # Handle foreign key fields
            elif field["is_foreign_key"]:
                fk_objects = {
                    str(fk["display"]): fk["id"] for fk in field["foreign_key_choices"]
                }
                field_fk_mappings = {}

                for file_value in file_values:
                    best_match_id = self.find_best_fk_match(file_value, fk_objects)
                    if best_match_id:
                        slug_value = slugify(file_value)
                        field_fk_mappings[slug_value] = best_match_id

                if field_fk_mappings:
                    fk_mappings[field_name] = field_fk_mappings

        return choice_mappings, fk_mappings

    def find_best_choice_match(self, file_value, choice_dict):
        """Find the best matching choice using fuzzy string matching"""

        def normalize_text(text):
            return str(text).lower().strip().replace("_", " ").replace("-", " ")

        norm_file_value = normalize_text(file_value)

        # Try exact match first (normalized)
        for choice_value, choice_label in choice_dict.items():
            if norm_file_value == normalize_text(choice_value):
                return choice_value
            if norm_file_value == normalize_text(choice_label):
                return choice_value

        # Try fuzzy matching
        best_match = None
        best_ratio = 0.7  # Higher threshold for choices

        for choice_value, choice_label in choice_dict.items():
            # Check against choice value
            ratio = difflib.SequenceMatcher(
                None, norm_file_value, normalize_text(choice_value)
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = choice_value

            # Check against choice label
            ratio = difflib.SequenceMatcher(
                None, norm_file_value, normalize_text(choice_label)
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = choice_value

        return best_match

    def find_best_fk_match(self, file_value, fk_objects):
        """Find the best matching foreign key object using fuzzy string matching"""

        def normalize_text(text):
            return str(text).lower().strip().replace("_", " ").replace("-", " ")

        norm_file_value = normalize_text(file_value)

        # Try exact match first (normalized)
        for display_name, obj_id in fk_objects.items():
            if norm_file_value == normalize_text(display_name):
                return obj_id

        # Try fuzzy matching
        best_match_id = None
        best_ratio = 0.7  # Higher threshold for FK matches

        for display_name, obj_id in fk_objects.items():
            ratio = difflib.SequenceMatcher(
                None, norm_file_value, normalize_text(display_name)
            ).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match_id = obj_id

        return best_match_id

    def get_app_label_for_model(self, model_name):
        """Find the app_label for a given model name"""
        from django.apps import apps

        for app_config in apps.get_app_configs():
            try:
                model = apps.get_model(app_config.label, model_name)
                return app_config.label
            except LookupError:
                continue
        return None

    def get_model_fields(self, module_name, app_label):
        """Get fields from the selected model with choice and foreign key info"""

        try:
            model = apps.get_model(app_label, module_name)
            fields = []
            # Define fields to exclude
            excluded_fields = [
                "id",
                "created_at",
                "updated_at",
                "is_active",
                "additional_info",
                "company",
                "created_by",
                "updated_by",
                "history",
            ]
            for field in model._meta.fields:
                if field.name in excluded_fields:
                    continue
                field_info = {
                    "name": field.name,
                    "verbose_name": field.verbose_name.title(),
                    "required": not field.null and not field.blank,
                    "field_type": field.get_internal_type(),
                    "is_choice_field": False,
                    "is_foreign_key": False,
                    "choices": [],
                    "foreign_key_model": None,
                    "foreign_key_choices": [],
                }
                # Handle ChoiceField
                if isinstance(field, CharField) and field.choices:
                    field_info["is_choice_field"] = True
                    field_info["choices"] = [
                        {"value": value, "label": label}
                        for value, label in field.choices
                    ]
                # Handle ForeignKey
                elif isinstance(field, ForeignKey):
                    field_info["is_foreign_key"] = True
                    field_info["foreign_key_model"] = field.related_model
                    related_instances = field.related_model.objects.all()
                    field_info["foreign_key_choices"] = [
                        {"id": instance.pk, "display": str(instance)}
                        for instance in related_instances
                    ]
                fields.append(field_info)
            return fields
        except Exception as e:
            logger.error(
                f"Error in get_model_fields (app_label: {app_label}, module: {module_name}): {str(e)}"
            )
            return []

    def get_file_headers(self, file_path):
        """Extract headers from uploaded file"""
        full_path = default_storage.path(file_path)
        if file_path.endswith(".csv"):
            with open(full_path, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                headers = next(reader)
        else:
            df = pd.read_excel(full_path, nrows=0)
            headers = list(df.columns)
        return headers

    def get_sample_data(self, file_path):
        """Get sample data from file"""
        full_path = default_storage.path(file_path)
        sample_data = []
        if file_path.endswith(".csv"):
            with open(full_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for i, row in enumerate(reader):
                    if i >= 3:
                        break
                    sample_data.append(dict(row))
        else:
            df = pd.read_excel(full_path, nrows=3)
            sample_data = df.to_dict("records")
        return sample_data

    def get_unique_file_values(self, file_path, headers):
        """Extract unique values for each column in the file"""
        full_path = default_storage.path(file_path)
        unique_values = {header: set() for header in headers}
        if file_path.endswith(".csv"):
            with open(full_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    for header in headers:
                        value = str(row.get(header, "")).strip()
                        if value:
                            unique_values[header].add(value)
        else:
            df = pd.read_excel(full_path)
            for header in headers:
                if header in df.columns:
                    unique_values[header].update(
                        df[header].dropna().astype(str).str.strip()
                    )
        # Convert sets to sorted lists
        return {
            header: sorted(list(values)) for header, values in unique_values.items()
        }


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class ImportStep2View(View):
    """Handle field mapping"""

    def get(self, request, *args, **kwargs):
        """Handle navigation back to step 2"""
        import_data = request.session.get("import_data", {})
        import_config = request.session.get("import_config", {})
        single_import = import_config.get("single_import", False)
        model_name = import_config.get("model_name", "")
        if not import_data:
            return redirect("horilla_core:import_data")

        module = import_data.get("module")
        app_label = import_data.get("app_label")
        headers = import_data.get("headers", [])
        sample_data = import_data.get("sample_data", [])

        if not all([module, app_label, headers]):
            return redirect("horilla_core:import_data")

        # Get model fields
        model_fields = self.get_model_fields(module, app_label)
        if not model_fields:
            return HttpResponse(
                f"""
                <div class="text-red-500 text-sm">No valid fields found for the selected model: {module}</div>
            """
            )

        # Get existing mappings from session
        auto_mappings = import_data.get("auto_mappings", {})
        auto_choice_mappings = import_data.get("auto_choice_mappings", {})
        auto_fk_mappings = import_data.get("auto_fk_mappings", {})
        field_mappings = import_data.get("field_mappings", {})
        replace_values = import_data.get("replace_values", {})
        choice_mappings = import_data.get("choice_mappings", {})
        fk_mappings = import_data.get("fk_mappings", {})

        # Merge auto mappings with manual mappings
        current_mappings = auto_mappings.copy()
        current_mappings.update(field_mappings)

        return render(
            request,
            "import/import_step2.html",
            {
                "headers": headers,
                "sample_data": sample_data,
                "model_fields": model_fields,
                "module": module,
                "app_label": app_label,
                "auto_mappings": current_mappings,
                "auto_choice_mappings": auto_choice_mappings,
                "auto_fk_mappings": auto_fk_mappings,
                "replace_values": replace_values,
                "choice_mappings": choice_mappings,
                "fk_mappings": fk_mappings,
                "validation_errors": {},
                "single_import": single_import,
                "selected_module": model_name,
            },
        )

    def post(self, request, *args, **kwargs):
        from django.apps import apps

        import_data = request.session.get("import_data", {})
        import_config = request.session.get("import_config", {})
        single_import = import_config.get("single_import", False)
        model_name = import_config.get("model_name", "")
        module = import_data.get("module")
        app_label = import_data.get("app_label")
        unique_values = import_data.get("unique_values", {})

        if not module or not app_label:
            return HttpResponse(
                """
                <div class="text-red-500 text-sm">Missing module or app_label in session</div>
            """
            )

        try:
            field_mappings = {}
            replace_values = {}
            choice_mappings = {}
            fk_mappings = {}
            validation_errors = {}

            # Get model fields for validation
            model_fields = self.get_model_fields(module, app_label)
            if not model_fields:
                return HttpResponse(
                    f"""
                    <div class="text-red-500 text-sm">No valid fields found for the selected model: {module}</div>
                """
                )

            # Get model for field names
            model = apps.get_model(app_label, module)
            model_field_names = [field.name for field in model._meta.fields]

            # Process form data
            for key, value in request.POST.items():
                if key.startswith("file_header_"):
                    field_name = key.replace("file_header_", "")
                    if value:
                        field_mappings[field_name] = value
                elif key.startswith("replace_"):
                    field_name = key.replace("replace_", "")
                    if value:
                        replace_values[field_name] = value
                elif key.startswith("choice_mapping_") or key.startswith("fk_mapping_"):
                    is_choice = key.startswith("choice_mapping_")
                    prefix = "choice_mapping_" if is_choice else "fk_mapping_"
                    remaining = key.replace(prefix, "")

                    field_name = None
                    slugified_value = None

                    for model_field in sorted(model_field_names, key=len, reverse=True):
                        if remaining.startswith(model_field + "_"):
                            field_name = model_field
                            slugified_value = remaining[len(model_field) + 1 :]
                            break

                    if field_name and slugified_value and value:
                        target_dict = choice_mappings if is_choice else fk_mappings
                        if field_name not in target_dict:
                            target_dict[field_name] = {}
                        target_dict[field_name][slugified_value] = value

            # Validate required fields
            for field in model_fields:
                if field["required"]:
                    field_name = field["name"]

                    if field_name in replace_values:
                        continue

                    # Check if field is mapped
                    if field_name not in field_mappings:
                        validation_errors[field_name] = [
                            "This required field must be mapped to a file header."
                        ]
                        continue

                    file_header = field_mappings[field_name]

                    # For choice and foreign key fields, check if all values are mapped
                    if field["is_choice_field"] or field["is_foreign_key"]:
                        file_values = unique_values.get(file_header, [])
                        mappings = (
                            choice_mappings.get(field_name, {})
                            if field["is_choice_field"]
                            else fk_mappings.get(field_name, {})
                        )

                        # Check if all unique values are mapped
                        unmapped_values = [
                            val
                            for val in file_values
                            if val and slugify(val) not in mappings
                        ]
                        if unmapped_values and field_name not in replace_values:
                            validation_errors[field_name] = [
                                "All values must be mapped or a default replace value must be provided."
                            ]
                        # Check if replace value is provided when there are empty values
                        elif "" in file_values and field_name not in replace_values:
                            validation_errors[field_name] = [
                                "A default replace value is required for empty values in this field."
                            ]

            # If there are validation errors, re-render the form
            if validation_errors:
                return render(
                    request,
                    "import/import_step2.html",
                    {
                        "headers": import_data.get("headers", []),
                        "sample_data": import_data.get("sample_data", []),
                        "model_fields": model_fields,
                        "module": module,
                        "app_label": app_label,
                        "auto_mappings": import_data.get("auto_mappings", {}),
                        "auto_choice_mappings": import_data.get(
                            "auto_choice_mappings", {}
                        ),
                        "auto_fk_mappings": import_data.get("auto_fk_mappings", {}),
                        "replace_values": replace_values,
                        "choice_mappings": choice_mappings,
                        "fk_mappings": fk_mappings,
                        "validation_errors": validation_errors,
                        "single_import": single_import,
                        "selected_module": model_name,
                    },
                )

            # Get auto-mappings from session
            auto_choice_mappings = import_data.get("auto_choice_mappings", {})
            auto_fk_mappings = import_data.get("auto_fk_mappings", {})

            for field_name, auto_mappings in auto_choice_mappings.items():
                if field_name not in choice_mappings:
                    choice_mappings[field_name] = auto_mappings.copy()

            for field_name, auto_mappings in auto_fk_mappings.items():
                if field_name not in fk_mappings:
                    fk_mappings[field_name] = auto_mappings.copy()

            # Store mappings in session
            import_data["field_mappings"] = field_mappings
            import_data["replace_values"] = replace_values
            import_data["choice_mappings"] = choice_mappings
            import_data["fk_mappings"] = fk_mappings
            request.session["import_data"] = import_data

            return render(
                request,
                "import/import_step3.html",
                {
                    "module": module,
                    "model_fields": model_fields,
                    "app_label": app_label,
                    "single_import": single_import,
                },
            )

        except Exception as e:
            logger.error(f"Error in ImportStep2View.post: {str(e)}")
            tb = traceback.format_exc()
            logger.error(tb)
            return HttpResponse(
                f"""
                <div class="text-red-500 text-sm">Error processing field mappings: {str(e)}</div>
            """
            )

    def get_model_fields(self, module_name, app_label):
        """Get fields from the selected model with choice and foreign key info"""
        from django.apps import apps
        from django.db.models import CharField, ForeignKey

        try:
            model = apps.get_model(app_label, module_name)
            fields = []
            excluded_fields = [
                "id",
                "created_at",
                "updated_at",
                "is_active",
                "additional_info",
                "company",
                "created_by",
                "updated_by",
                "history",
            ]
            for field in model._meta.fields:
                if field.name in excluded_fields:
                    continue
                field_info = {
                    "name": field.name,
                    "verbose_name": field.verbose_name.title(),
                    "required": not field.null and not field.blank,
                    "field_type": field.get_internal_type(),
                    "is_choice_field": False,
                    "is_foreign_key": False,
                    "choices": [],
                    "foreign_key_model": None,
                    "foreign_key_choices": [],
                }
                if isinstance(field, CharField) and field.choices:
                    field_info["is_choice_field"] = True
                    field_info["choices"] = [
                        {"value": value, "label": label}
                        for value, label in field.choices
                    ]
                elif isinstance(field, ForeignKey):
                    field_info["is_foreign_key"] = True
                    field_info["foreign_key_model"] = field.related_model
                    related_instances = field.related_model.objects.all()
                    field_info["foreign_key_choices"] = [
                        {"id": instance.pk, "display": str(instance)}
                        for instance in related_instances
                    ]
                fields.append(field_info)
            return fields
        except Exception as e:
            logger.error(
                f"Error in get_model_fields (app_label: {app_label}, module: {module_name}): {str(e)}"
            )
            return []


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class ImportStep3View(View):
    """Handle import options"""

    def get(self, request, *args, **kwargs):
        """Handle navigation back to step 3"""
        import_data = request.session.get("import_data", {})
        import_config = request.session.get("import_config", {})
        single_import = import_config.get("single_import", False)
        if not import_data:
            return redirect("horilla_core:import_data")

        module = import_data.get("module")
        app_label = import_data.get("app_label")

        if not module or not app_label:
            return redirect("horilla_core:import_data")

        model_fields = self.get_model_fields(module, app_label)

        # Get existing selections from session
        selected_import_option = import_data.get("import_option", "1")
        selected_match_fields = import_data.get("match_fields", [])

        return render(
            request,
            "import/import_step3.html",
            {
                "module": module,
                "app_label": app_label,
                "model_fields": model_fields,
                "selected_import_option": selected_import_option,
                "selected_match_fields": selected_match_fields,
                "single_import": single_import,
            },
        )

    def post(self, request, *args, **kwargs):
        import_data = request.session.get("import_data", {})
        module = import_data.get("module")
        app_label = import_data.get("app_label")
        import_config = request.session.get("import_config", {})
        single_import = import_config.get("single_import", False)

        if not module or not app_label:
            return HttpResponse(
                """
                <div class="text-red-500 text-sm">Missing module or app_label in session</div>
            """
            )

        try:
            import_option = request.POST.get(
                "import_option"
            )  # 1=create, 2=update, 3=both
            match_fields = request.POST.getlist("match_fields")

            if import_option in ["2", "3"] and not match_fields:
                model_fields = self.get_model_fields(module, app_label)
                return render(
                    request,
                    "import/import_step3.html",
                    {
                        "module": module,
                        "app_label": app_label,
                        "model_fields": model_fields,
                        "error_message": "Please select at least one field to match records for update operations.",
                        "selected_import_option": import_option,
                        "selected_match_fields": match_fields,
                    },
                )

            import_data["import_option"] = import_option
            import_data["match_fields"] = match_fields
            request.session["import_data"] = import_data

            # Calculate mapped and unmapped fields
            field_mappings = import_data.get("field_mappings", {})
            headers = import_data.get("headers", [])

            mapped_count = len(field_mappings)
            unmapped_count = len(headers) - mapped_count

            try:
                return render(
                    request,
                    "import/import_step4.html",
                    {
                        "import_data": import_data,
                        "mapped_count": mapped_count,
                        "unmapped_count": unmapped_count,
                        "module": module,
                        "app_label": app_label,
                        "single_import": single_import,
                    },
                )
            except Exception as e:
                logger.error(f"Template rendering error in ImportStep3View: {str(e)}")
                tb = traceback.format_exc()
                logger.error(tb)
                return HttpResponse(
                    f"""
                    <div class="text-red-500 text-sm">Template rendering error: {str(e)}</div>
                """
                )

        except Exception as e:
            logger.error(f"Error in ImportStep3View.post: {str(e)}")
            tb = traceback.format_exc()
            logger.error(tb)
            return HttpResponse(
                f"""
                <div class="text-red-500 text-sm">Error processing import options: {str(e)}</div>
                """
            )

    def get_model_fields(self, module_name, app_label):
        """Get fields from the selected model with choice and foreign key info"""
        from django.apps import apps
        from django.db.models import CharField, ForeignKey

        try:
            model = apps.get_model(app_label, module_name)
            fields = []
            # Define fields to exclude
            excluded_fields = [
                "id",
                "created_at",
                "updated_at",
                "is_active",
                "additional_info",
                "company",
                "created_by",
                "updated_by",
                "history",
            ]
            for field in model._meta.fields:
                if field.name in excluded_fields:
                    continue
                field_info = {
                    "name": field.name,
                    "verbose_name": field.verbose_name.title(),
                    "required": not field.null and not field.blank,
                    "field_type": field.get_internal_type(),
                    "is_choice_field": False,
                    "is_foreign_key": False,
                    "choices": [],
                    "foreign_key_model": None,
                    "foreign_key_choices": [],
                }
                # Handle ChoiceField
                if isinstance(field, CharField) and field.choices:
                    field_info["is_choice_field"] = True
                    field_info["choices"] = [
                        {"value": value, "label": label}
                        for value, label in field.choices
                    ]
                # Handle ForeignKey
                elif isinstance(field, ForeignKey):
                    field_info["is_foreign_key"] = True
                    field_info["foreign_key_model"] = field.related_model
                    related_instances = field.related_model.objects.all()
                    field_info["foreign_key_choices"] = [
                        {"id": instance.pk, "display": str(instance)}
                        for instance in related_instances
                    ]
                fields.append(field_info)
            return fields
        except Exception as e:
            logger.error(
                f"Error in get_model_fields (app_label: {app_label}, module: {module_name}): {str(e)}"
            )
            return []


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class ImportStep4View(View):
    """Handle final import process"""

    def get(self, request, *args, **kwargs):
        """Handle navigation back to step 4 (review)"""
        import_data = request.session.get("import_data", {})
        import_config = request.session.get("import_config", {})
        single_import = import_config.get("single_import", False)

        if not import_data:
            return redirect("horilla_core:import_data")

        module = import_data.get("module")
        app_label = import_data.get("app_label")

        if not module or not app_label:
            return redirect("horilla_core:import_data")

        # Calculate mapped and unmapped fields
        field_mappings = import_data.get("field_mappings", {})
        headers = import_data.get("headers", [])

        mapped_count = len(field_mappings)
        unmapped_count = len(headers) - mapped_count

        return render(
            request,
            "import/import_step4.html",
            {
                "import_data": import_data,
                "mapped_count": mapped_count,
                "unmapped_count": unmapped_count,
                "module": module,
                "app_label": app_label,
                "single_import": single_import,
            },
        )

    def post(self, request, *args, **kwargs):
        """Handle the actual import when user clicks Import button"""
        start_time = time.perf_counter()

        import_data = request.session.get("import_data", {})
        import_config = request.session.get("import_config", {})
        single_import = import_config.get("single_import", False)

        if not import_data:
            return HttpResponse(
                """
                <div class="text-red-500 text-sm">No import data found in session</div>
            """
            )

        # Create import history record
        import_history = ImportHistory.objects.create(
            import_name=import_data.get("import_name", ""),
            module_name=import_data.get("module", ""),
            app_label=import_data.get("app_label", ""),
            original_filename=import_data.get("original_filename", ""),
            imported_file_path=import_data.get("file_path", ""),
            import_option=import_data.get("import_option", "1"),
            match_fields=import_data.get("match_fields", []),
            field_mappings=import_data.get("field_mappings", {}),
            created_by=request.user if request.user.is_authenticated else None,
            company=getattr(request, "active_company", None),
            status="processing",
        )

        try:
            # Process the import
            process_start = time.perf_counter()
            result = self.process_import(import_data)
            duration = time.perf_counter() - process_start

            # Update import history with results
            import_history.total_rows = result["total_rows"]
            import_history.created_count = result["created_count"]
            import_history.updated_count = result["updated_count"]
            import_history.error_count = result["error_count"]
            import_history.success_rate = Decimal(str(result["success_rate"]))
            import_history.error_file_path = result.get("error_file_path", "")
            import_history.error_summary = result.get("errors", [])[
                :5
            ]  # Store first 5 errors
            import_history.duration_seconds = Decimal(str(duration))

            # Determine status
            if result["error_count"] == 0:
                import_history.status = "success"
            elif result["successful_rows"] > 0:
                import_history.status = "partial"
            else:
                import_history.status = "failed"

            import_history.save()

            # Render success page with results
            render_start = time.perf_counter()
            response = render(
                request,
                "import/import_success.html",
                {
                    "result": result,
                    "import_data": import_data,
                    "import_history": import_history,
                    "single_import": single_import,
                },
            )
            return response

        except Exception as e:
            # Update import history with error
            import_history.status = "failed"
            import_history.error_summary = [str(e)]
            import_history.duration_seconds = Decimal(
                str(time.perf_counter() - process_start)
            )
            import_history.save()

            return HttpResponse(
                f"""
                <div class="text-red-500 text-sm">Error during import: {str(e)}</div>
            """
            )

    def generate_error_csv(self, detailed_errors, import_data):
        """Generate a CSV file with original file structure plus error column"""
        try:
            import_name = import_data.get("import_name", "import")
            original_filename = import_data.get("original_filename", "file")

            # Extract filename without extension for error file naming
            if "." in original_filename:
                base_filename = original_filename.rsplit(".", 1)[0]
            else:
                base_filename = original_filename

            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base_filename}_errors_{timestamp}.csv"
            file_path = f"import_errors/{filename}"

            # Read original file to get structure
            original_file_path = import_data.get("file_path")
            original_headers = import_data.get("headers", [])

            if not original_file_path or not original_headers:
                raise ValueError("Original file path or headers not found")

            # Read all original data
            original_data = self.read_file_data(original_file_path)

            # Create error lookup by row number
            error_lookup = {
                error["row_number"]: error["errors"] for error in detailed_errors
            }

            # Create CSV content with original structure + error column
            csv_content = StringIO()
            writer = csv.writer(csv_content)

            # Write headers (original headers + Error column)
            headers_with_error = original_headers + ["Import_Error"]
            writer.writerow(headers_with_error)

            # Write data rows
            for row_index, row_data in enumerate(original_data, 1):
                # Get original row values in correct order
                row_values = []
                for header in original_headers:
                    row_values.append(row_data.get(header, ""))

                # Add error information if this row had errors
                error_info = error_lookup.get(row_index, "")
                row_values.append(error_info)

                # Only write rows that had errors
                if error_info:
                    writer.writerow(row_values)

            # Save to storage
            full_file_path = default_storage.save(
                file_path, ContentFile(csv_content.getvalue().encode("utf-8"))
            )

            return full_file_path

        except Exception as e:
            logger.error(f"Error generating error CSV: {str(e)}")
            return None

    def process_import(self, import_data):
        start_time = time.perf_counter()

        # Database-specific batch size optimization
        is_postgres = connection.vendor == "postgresql"
        is_sqlite = connection.vendor == "sqlite"
        create_batch_size = 1000 if is_postgres else (500 if is_sqlite else 999)
        update_batch_size = 500 if is_postgres else (100 if is_sqlite else 200)

        module_name = import_data["module"]
        app_label = import_data["app_label"]
        file_path = import_data["file_path"]
        field_mappings = import_data.get("field_mappings", {})
        replace_values = import_data.get("replace_values", {})
        choice_mappings = import_data.get("choice_mappings", {})
        fk_mappings = import_data.get("fk_mappings", {})
        import_option = import_data["import_option"]
        match_fields = import_data.get("match_fields", [])

        model = apps.get_model(app_label, module_name)
        field_metadata = {
            f.name: {
                "type": f.get_internal_type(),
                "is_fk": isinstance(f, ForeignKey),
                "is_choice": isinstance(f, CharField) and f.choices,
                "related_model": f.related_model if isinstance(f, ForeignKey) else None,
                "choices": (
                    dict(f.choices) if isinstance(f, CharField) and f.choices else {}
                ),
                "null": f.null,
                "blank": f.blank,
                "verbose_name": f.verbose_name,
            }
            for f in model._meta.fields
        }

        # Precompute update fields for bulk operations
        base_update_fields = set()
        for field in model._meta.fields:
            if field.primary_key:
                continue
            if field.name in field_mappings or field.name in [
                "updated_at",
                "updated_by",
                "company",
            ]:
                base_update_fields.add(field.name)
        update_fields_for_update = list(
            base_update_fields - {"created_at", "created_by"}
        )

        data_rows = self.read_file_data(file_path)

        created, errors = [], []
        detailed_errors = []  # For CSV export
        created_count = updated_count = error_count = 0
        current_time = timezone.now()
        user = self.request.user if self.request.user.is_authenticated else None
        company = getattr(self.request, "active_company", None)

        # Preload FK objects referenced in mappings
        fk_cache = {}
        fk_start = time.perf_counter()
        for field, mapping in fk_mappings.items():
            related_model = field_metadata[field]["related_model"]
            fk_cache[field] = {
                k: related_model.objects.filter(pk=v).first()
                for k, v in mapping.items()
            }

        # Preload replace_values FKs
        replace_start = time.perf_counter()
        for field, value in replace_values.items():
            if field_metadata[field]["is_fk"]:
                related_model = field_metadata[field]["related_model"]
                fk_cache.setdefault(field, {})
                fk_cache[field]["__replace__"] = related_model.objects.filter(
                    pk=value
                ).first()

        with transaction.atomic():
            existing_objs = {}
            if match_fields and import_option in ["1", "2", "3"]:
                filter_start = time.perf_counter()
                filters = {
                    f"{f}__in": [
                        str(row.get(field_mappings.get(f, ""), "")).strip()
                        for row in data_rows
                        if f in field_mappings
                    ]
                    for f in match_fields
                }
                qset = model.objects.filter(**{k: v for k, v in filters.items() if v})
                existing_objs = {
                    tuple(getattr(obj, f) for f in match_fields): obj for obj in qset
                }

            # Group objects by changed fields for efficient updates
            updated_groups = defaultdict(list)
            row_processing_start = time.perf_counter()

            for row_index, row_data in enumerate(data_rows, 1):
                row_errors = []
                try:
                    mapped = {}
                    for model_field, file_header in field_mappings.items():
                        value = str(row_data.get(file_header, "")).strip()
                        meta = field_metadata[model_field]
                        original_value = value  # Keep original for error reporting

                        if not value and model_field in replace_values:
                            value = replace_values[model_field]

                        if meta["is_fk"]:
                            slug_val = slugify(value) if value else None
                            obj = fk_cache.get(model_field, {}).get(slug_val)
                            if not obj and model_field in replace_values:
                                obj = fk_cache.get(model_field, {}).get("__replace__")

                            # Enhanced FK validation
                            if not obj and value and not meta["null"]:
                                row_errors.append(
                                    f"Foreign key '{meta['verbose_name']}': No matching record found for '{original_value}'"
                                )
                            elif (
                                not obj
                                and not value
                                and not meta["null"]
                                and not meta["blank"]
                            ):
                                row_errors.append(
                                    f"Foreign key '{meta['verbose_name']}': Required field cannot be empty"
                                )

                            mapped[model_field] = obj

                        elif meta["is_choice"]:
                            if value and model_field in choice_mappings:
                                slug_val = slugify(value)
                                if slug_val in choice_mappings[model_field]:
                                    value = choice_mappings[model_field][slug_val]
                                elif model_field in replace_values:
                                    value = replace_values[model_field]
                            elif not value and model_field in replace_values:
                                value = replace_values[model_field]

                            # Enhanced choice validation
                            if value and value not in meta["choices"]:
                                valid_choices = ", ".join(
                                    [f"'{choice}'" for choice in meta["choices"].keys()]
                                )
                                row_errors.append(
                                    f"Choice field '{meta['verbose_name']}': Invalid value '{original_value}'. Valid choices are: {valid_choices}"
                                )
                            elif not value and not meta["null"] and not meta["blank"]:
                                row_errors.append(
                                    f"Choice field '{meta['verbose_name']}': Required field cannot be empty"
                                )

                            mapped[model_field] = value

                        else:
                            if not value and model_field in replace_values:
                                value = replace_values[model_field]

                            # Enhanced type conversion with error reporting
                            if meta["type"] in ["IntegerField", "BigIntegerField"]:
                                if value:
                                    try:
                                        value = int(value)
                                    except ValueError:
                                        row_errors.append(
                                            f"Integer field '{meta['verbose_name']}': Cannot convert '{original_value}' to integer"
                                        )
                                        value = None
                                else:
                                    value = None

                            elif meta["type"] == "DecimalField":
                                if value:
                                    try:
                                        value = float(value)
                                    except ValueError:
                                        row_errors.append(
                                            f"Decimal field '{meta['verbose_name']}': Cannot convert '{original_value}' to decimal"
                                        )
                                        value = None
                                else:
                                    value = None

                            elif meta["type"] == "BooleanField":
                                if value:
                                    str_value = str(value).lower().strip()
                                    if str_value in (
                                        "true",
                                        "1",
                                        "yes",
                                        "on",
                                        "false",
                                        "0",
                                        "no",
                                        "off",
                                    ):
                                        value = str_value in ("true", "1", "yes", "on")
                                    else:
                                        row_errors.append(
                                            f"Replace value for '{meta['verbose_name']}': Invalid boolean value '{replace_value}'. Valid values are: true, false, 1, 0, yes, no, on, off"
                                        )
                                        value = None
                                else:
                                    value = False

                            elif meta["type"] in ["DateField", "DateTimeField"]:
                                if value:
                                    try:
                                        if meta["type"] == "DateField":
                                            try:
                                                value = datetime.strptime(
                                                    value, "%Y-%m-%d"
                                                ).date()
                                            except ValueError:
                                                try:
                                                    value = datetime.strptime(
                                                        value, "%m/%d/%Y"
                                                    ).date()
                                                except ValueError:
                                                    try:
                                                        value = datetime.strptime(
                                                            value, "%d/%m/%Y"
                                                        ).date()
                                                    except ValueError:
                                                        raise ValueError(
                                                            f"Invalid date format for '{original_value}'. Expected YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY"
                                                        )
                                        else:
                                            try:
                                                value = datetime.fromisoformat(value)
                                            except ValueError:
                                                # Try other common datetime formats
                                                formats = [
                                                    "%Y-%m-%d %H:%M:%S",
                                                    "%m/%d/%Y %H:%M:%S",
                                                    "%d/%m/%Y %H:%M:%S",
                                                    "%Y-%m-%d %I:%M:%S %p",
                                                    "%m/%d/%Y %I:%M:%S %p",
                                                    "%d/%m/%Y %I:%M:%S %p",
                                                ]
                                                parsed = False
                                                for fmt in formats:
                                                    try:
                                                        value = datetime.strptime(
                                                            value, fmt
                                                        )
                                                        parsed = True
                                                        break
                                                    except ValueError:
                                                        continue

                                                if not parsed:
                                                    raise ValueError(
                                                        f"Invalid datetime format for '{original_value}'"
                                                    )
                                    except ValueError as e:
                                        row_errors.append(
                                            f"Date field '{meta['verbose_name']}': {str(e)}"
                                        )
                                        value = None
                                else:
                                    value = None

                            # Check for required field violations
                            if value is None and not meta["null"] and not meta["blank"]:
                                row_errors.append(
                                    f"Required field '{meta['verbose_name']}': Cannot be empty or invalid"
                                )

                            mapped[model_field] = value

                    for field, replace_value in replace_values.items():
                        if field not in field_mappings and field in field_metadata:
                            meta = field_metadata[field]

                            if meta["is_fk"]:
                                obj = fk_cache.get(field, {}).get("__replace__")
                                mapped[field] = obj
                            elif meta["is_choice"]:
                                if replace_value in meta["choices"]:
                                    mapped[field] = replace_value
                                else:
                                    row_errors.append(
                                        f"Replace value for '{meta['verbose_name']}': Invalid choice '{replace_value}'"
                                    )
                            else:
                                value = replace_value
                                if meta["type"] in ["IntegerField", "BigIntegerField"]:
                                    try:
                                        value = int(value)
                                    except ValueError:
                                        row_errors.append(
                                            f"Replace value for '{meta['verbose_name']}': Cannot convert '{replace_value}' to integer"
                                        )
                                        value = None
                                elif meta["type"] == "DecimalField":
                                    try:
                                        value = float(value)
                                    except ValueError:
                                        row_errors.append(
                                            f"Replace value for '{meta['verbose_name']}': Cannot convert '{replace_value}' to decimal"
                                        )
                                        value = None
                                elif meta["type"] == "BooleanField":
                                    str_value = str(value).lower().strip()
                                    if str_value in (
                                        "true",
                                        "1",
                                        "yes",
                                        "on",
                                        "false",
                                        "0",
                                        "no",
                                        "off",
                                    ):
                                        value = str_value in ("true", "1", "yes", "on")
                                    else:
                                        row_errors.append(
                                            f"Replace value for '{meta['verbose_name']}': Invalid boolean value '{replace_value}'. Valid values are: true, false, 1, 0, yes, no, on, off"
                                        )
                                        value = None
                                elif meta["type"] in ["DateField", "DateTimeField"]:
                                    if value:
                                        try:
                                            if meta["type"] == "DateField":
                                                try:
                                                    value = datetime.strptime(
                                                        value, "%Y-%m-%d"
                                                    ).date()
                                                except ValueError:
                                                    try:
                                                        value = datetime.strptime(
                                                            value, "%m/%d/%Y"
                                                        ).date()
                                                    except ValueError:
                                                        try:
                                                            value = datetime.strptime(
                                                                value, "%d/%m/%Y"
                                                            ).date()
                                                        except ValueError:
                                                            raise ValueError(
                                                                f"Invalid date format for '{original_value}'. Expected YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY"
                                                            )
                                            else:
                                                try:
                                                    value = datetime.fromisoformat(
                                                        value
                                                    )
                                                except ValueError:
                                                    formats = [
                                                        "%Y-%m-%d %H:%M:%S",
                                                        "%m/%d/%Y %H:%M:%S",
                                                        "%d/%m/%Y %H:%M:%S",
                                                        "%Y-%m-%d %I:%M:%S %p",
                                                        "%m/%d/%Y %I:%M:%S %p",
                                                        "%d/%m/%Y %I:%M:%S %p",
                                                    ]
                                                    parsed = False
                                                    for fmt in formats:
                                                        try:
                                                            value = datetime.strptime(
                                                                value, fmt
                                                            )
                                                            parsed = True
                                                            break
                                                        except ValueError:
                                                            continue

                                                    if not parsed:
                                                        raise ValueError(
                                                            f"Invalid datetime format for '{original_value}'"
                                                        )
                                        except ValueError as e:
                                            row_errors.append(
                                                f"Date field '{meta['verbose_name']}': {str(e)}"
                                            )
                                            value = None
                                    else:
                                        value = None
                                mapped[field] = value

                    if row_errors:
                        error_count += 1
                        row_error_summary = f"Row {row_index}: {'; '.join(row_errors)}"
                        errors.append(row_error_summary)

                        # Add detailed error for CSV export
                        detailed_errors.append(
                            {"row_number": row_index, "errors": "; ".join(row_errors)}
                        )
                        continue

                    # Handle import_option
                    if import_option == "1":  # create only
                        if match_fields:
                            key = tuple(mapped.get(f) for f in match_fields)
                            if key in existing_objs:
                                # Add error for existing record when in create-only mode
                                error_count += 1
                                match_field_values = []
                                for field in match_fields:
                                    field_value = mapped.get(field, "N/A")
                                    if field_value is None:
                                        field_value = "N/A"
                                    match_field_values.append(
                                        f"{field}='{field_value}'"
                                    )
                                match_criteria = ", ".join(match_field_values)

                                error_msg = f"Row {row_index}: Record already exists with matching criteria: {match_criteria}. Skipped in create-only mode."
                                errors.append(error_msg)

                                # Add detailed error for CSV export
                                detailed_errors.append(
                                    {
                                        "row_number": row_index,
                                        "errors": f"Record already exists with matching criteria: {match_criteria}. Skipped in create-only mode.",
                                    }
                                )
                                continue

                        obj = model(**mapped)
                        obj.created_at = mapped.get("created_at", current_time)
                        obj.updated_at = current_time
                        if user:
                            obj.created_by = mapped.get("created_by", user)
                            obj.updated_by = user
                        obj.company = company
                        created.append(obj)

                    elif import_option == "2":  # update only
                        key = tuple(mapped.get(f) for f in match_fields)
                        instance = existing_objs.get(key)
                        if instance:
                            changed_fields = self._update_instance(
                                instance,
                                mapped,
                                field_metadata,
                                update_fields_for_update,
                                current_time,
                                user,
                                company,
                            )
                            updated_groups[frozenset(changed_fields)].append(instance)
                        else:
                            error_count += 1
                            match_field_values = []
                            for field in match_fields:
                                field_value = mapped.get(field, "N/A")
                                if field_value is None:
                                    field_value = "N/A"
                                match_field_values.append(f"{field}='{field_value}'")
                            match_criteria = ", ".join(match_field_values)

                            error_msg = f"Row {row_index}: No existing record found to update with matching criteria: {match_criteria}"
                            errors.append(error_msg)

                            # Add detailed error for CSV export
                            detailed_errors.append(
                                {
                                    "row_number": row_index,
                                    "errors": f"No existing record found to update with matching criteria: {match_criteria}",
                                }
                            )

                    elif import_option == "3":  # create + update
                        key = tuple(mapped.get(f) for f in match_fields)
                        instance = existing_objs.get(key)
                        if instance:
                            changed_fields = self._update_instance(
                                instance,
                                mapped,
                                field_metadata,
                                update_fields_for_update,
                                current_time,
                                user,
                                company,
                            )
                            updated_groups[frozenset(changed_fields)].append(instance)
                        else:
                            obj = model(**mapped)
                            obj.created_at = mapped.get("created_at", current_time)
                            obj.updated_at = current_time
                            if user:
                                obj.created_by = mapped.get("created_by", user)
                                obj.updated_by = user
                            obj.company = company
                            created.append(obj)
                            if match_fields:
                                existing_objs[key] = obj

                except Exception as e:
                    error_count += 1
                    error_msg = f"Row {row_index}: Unexpected error - {str(e)}"
                    errors.append(error_msg)
                    detailed_errors.append(
                        {
                            "row_number": row_index,
                            "errors": f"Unexpected error - {str(e)}",
                        }
                    )

            if created:
                bulk_create_start = time.perf_counter()
                model.objects.bulk_create(created, batch_size=create_batch_size)
                created_count = len(created)

            bulk_update_start = time.perf_counter()
            for fields, objs in updated_groups.items():
                if fields:
                    for i in range(0, len(objs), update_batch_size):
                        batch = objs[i : i + update_batch_size]
                        model.objects.bulk_update(
                            batch, fields=list(fields), batch_size=len(batch)
                        )
                        updated_count += len(batch)

        # Generate error CSV if there are errors
        error_file_path = None
        if detailed_errors:
            error_file_path = self.generate_error_csv(detailed_errors, import_data)

        session_cleanup_start = time.perf_counter()
        if "import_data" in self.request.session:
            del self.request.session["import_data"]
            self.request.session.modified = True

        successful_rows = created_count + updated_count
        total_rows = len(data_rows)
        success_rate = (successful_rows / total_rows * 100) if total_rows > 0 else 0

        return {
            "created_count": created_count,
            "updated_count": updated_count,
            "error_count": error_count,
            "errors": errors[:5],
            "total_rows": total_rows,
            "successful_rows": successful_rows,
            "success_rate": round(success_rate, 1),
            "error_file_path": error_file_path,
            "has_more_errors": len(errors) > 5,
        }

    def _update_instance(
        self,
        instance,
        mapped,
        field_metadata,
        update_fields,
        current_time,
        user,
        company,
    ):
        """Update instance with change detection and return changed fields"""
        changed_fields = {"updated_at", "company"}  # System fields always change
        if user:
            changed_fields.add("updated_by")

        # Update data fields with change detection
        for field in update_fields:
            if field in ["updated_at", "updated_by", "company"]:
                continue

            new_value = mapped.get(field)
            old_value = getattr(instance, field)

            # Skip if values are the same
            if old_value == new_value:
                continue

            # Handle special field types
            meta = field_metadata.get(field, {})
            if meta.get("is_fk"):
                # Foreign keys are already resolved in mapped
                pass
            elif meta.get("is_choice"):
                # Choices are already converted in mapped
                pass
            else:
                # Type conversion already handled in mapped
                pass

            setattr(instance, field, new_value)
            changed_fields.add(field)

        # Update system fields
        instance.updated_at = current_time
        if user:
            instance.updated_by = user
        instance.company = company

        return changed_fields

    def read_file_data(self, file_path):
        """Read data from the uploaded file"""
        start_time = time.perf_counter()
        full_path = default_storage.path(file_path)
        data_rows = []
        if file_path.endswith(".csv"):
            with open(full_path, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    data_rows.append(dict(row))
        else:
            df = pd.read_excel(full_path)
            data_rows = df.to_dict("records")
        return data_rows


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class GetModelFieldsView(View):
    """HTMX view to get model fields when module is selected"""

    def get(self, request, *args, **kwargs):
        import_data = request.session.get("import_data", {})
        unique_values = import_data.get("unique_values", {})
        field_name = request.GET.get("field_name", "")

        # Get file header from either GET parameter or form data
        file_header = request.GET.get(f"file_header_{field_name}", "")
        if not file_header:
            file_header = request.GET.get("file_header_", "")

        app_label = request.GET.get("app_label", "")
        module = request.GET.get("module", "")

        if not all([file_header, field_name, app_label, module]):
            missing_params = [
                param
                for param, value in [
                    ("file_header", file_header),
                    ("field_name", field_name),
                    ("app_label", app_label),
                    ("module", module),
                ]
                if not value
            ]
            raise HorillaHttp404(f"Missing parameters: {', '.join(missing_params)}")
            # return HttpResponse(f'<div class="text-xs p-2 border text-red-500">Missing parameters: {", ".join(missing_params)}</div>')

        try:
            from django.apps import apps
            from django.db.models import CharField, ForeignKey

            model = apps.get_model(app_label, module)
            field = next((f for f in model._meta.fields if f.name == field_name), None)
            if not field:
                return HttpResponse(
                    f'<div class="text-xs p-2 border text-red-500">Field not found: {field_name}</div>'
                )

            unique_file_values = unique_values.get(file_header, [])
            is_choice_field = isinstance(field, CharField) and field.choices
            is_foreign_key = isinstance(field, ForeignKey)

            context = {
                "field": {
                    "name": field_name,
                    "verbose_name": field.verbose_name.title(),
                    "is_choice_field": is_choice_field,
                    "is_foreign_key": is_foreign_key,
                    "choices": (
                        [
                            {"value": value, "label": label}
                            for value, label in field.choices
                        ]
                        if is_choice_field
                        else []
                    ),
                    "foreign_key_choices": (
                        [
                            {"id": instance.pk, "display": str(instance)}
                            for instance in field.related_model.objects.all()
                        ]
                        if is_foreign_key
                        else []
                    ),
                    "unique_file_values": unique_file_values,
                },
                "choice_mappings": import_data.get("choice_mappings", {}).get(
                    field_name, {}
                ),
                "fk_mappings": import_data.get("fk_mappings", {}).get(field_name, {}),
                "auto_choice_mappings": import_data.get("auto_choice_mappings", {}).get(
                    field_name, {}
                ),
                "auto_fk_mappings": import_data.get("auto_fk_mappings", {}).get(
                    field_name, {}
                ),
            }

            return render(request, "import/value_mapping_partial.html", context)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(tb)
            return HttpResponse(
                f'<div class="text-xs p-2 border text-red-500">Error: {str(e)}</div>'
            )


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class UpdateFieldStatusView(View):
    """HTMX view to update field mapping status"""

    def post(self, request, *args, **kwargs):
        field_name = request.GET.get("field_name")
        file_header = request.POST.get(f"file_header_{field_name}")

        if file_header:
            status_html = '<span class="bg-green-100 text-green-500 text-xs font-medium me-2 px-2.5 py-0.5 rounded-full">Mapped</span>'
        else:
            status_html = '<span class="bg-red-100 text-red-500 text-xs font-medium me-2 px-2.5 py-0.5 rounded-full">Not Mapped</span>'

        return HttpResponse(status_html)


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class GetUniqueValuesView(View):
    """HTMX view to get unique values for a selected file header with auto-mapping"""

    def get(self, request, *args, **kwargs):
        import_data = request.session.get("import_data", {})
        unique_values = import_data.get("unique_values", {})
        field_name = request.GET.get("field_name", "")

        # Get file header from either GET parameter or form data
        file_header = request.GET.get(f"file_header_{field_name}", "")
        if not file_header:
            file_header = request.GET.get("file_header", "")

        app_label = request.GET.get("app_label", "")
        module = request.GET.get("module", "")

        if not all([file_header, field_name, app_label, module]):
            missing_params = [
                param
                for param, value in [
                    ("file_header", file_header),
                    ("field_name", field_name),
                    ("app_label", app_label),
                    ("module", module),
                ]
                if not value
            ]
            raise HorillaHttp404(f"Missing parameters: {', '.join(missing_params)}")

        try:
            from django.apps import apps
            from django.db.models import CharField, ForeignKey

            model = apps.get_model(app_label, module)
            field = next((f for f in model._meta.fields if f.name == field_name), None)
            if not field:
                return HttpResponse(
                    f'<div class="text-xs p-2 border text-red-500">Field not found: {field_name}</div>'
                )

            unique_file_values = unique_values.get(file_header, [])
            is_choice_field = isinstance(field, CharField) and field.choices
            is_foreign_key = isinstance(field, ForeignKey)

            # Get auto-mappings from session
            auto_choice_mappings = import_data.get("auto_choice_mappings", {})
            auto_fk_mappings = import_data.get("auto_fk_mappings", {})
            context = {
                "field": {
                    "name": field_name,
                    "verbose_name": field.verbose_name.title(),
                    "is_choice_field": is_choice_field,
                    "is_foreign_key": is_foreign_key,
                    "choices": (
                        [
                            {"value": value, "label": label}
                            for value, label in field.choices
                        ]
                        if is_choice_field
                        else []
                    ),
                    "foreign_key_choices": (
                        [
                            {"id": instance.pk, "display": str(instance)}
                            for instance in field.related_model.objects.all()
                        ]
                        if is_foreign_key
                        else []
                    ),
                    "unique_file_values": unique_file_values,
                },
                # add missing mappings for manual selections
                "choice_mappings": import_data.get("choice_mappings", {}).get(
                    field_name, {}
                ),
                "fk_mappings": import_data.get("fk_mappings", {}).get(field_name, {}),
                "auto_choice_mappings": auto_choice_mappings.get(field_name, {}),
                "auto_fk_mappings": auto_fk_mappings.get(field_name, {}),
            }

            return render(request, "import/value_mapping_partial.html", context)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(tb)
            return HttpResponse(
                f'<div class="text-xs p-2 border text-red-500">Error: {str(e)}</div>'
            )


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class UpdateValueMappingStatusView(View):
    def post(self, request, *args, **kwargs):
        import_data = request.session.get("import_data", {})
        field_name = request.GET.get("field_name")
        slug_value = request.GET.get("slug_value")
        value = request.POST.get(
            f"choice_mapping_{field_name}_{slug_value}"
        ) or request.POST.get(f"fk_mapping_{field_name}_{slug_value}")

        if not all([field_name, slug_value, value]):
            return HttpResponse(
                '<span class="bg-red-100 text-red-500 text-xs font-medium px-2 py-0.5 rounded-full">Error: Missing parameters</span>'
            )

        try:
            from django.apps import apps

            module = import_data.get("module")
            app_label = import_data.get("app_label")
            model = apps.get_model(app_label, module)
            field = next((f for f in model._meta.fields if f.name == field_name), None)

            if not field:
                return HttpResponse(
                    '<span class="bg-red-100 text-red-500 text-xs font-medium px-2 py-0.5 rounded-full">Error: Field not found</span>'
                )

            is_choice_field = isinstance(field, CharField) and field.choices
            is_foreign_key = isinstance(field, ForeignKey)

            if is_choice_field:
                import_data.setdefault("choice_mappings", {})
                import_data["choice_mappings"].setdefault(field_name, {})
                import_data["choice_mappings"][field_name][slug_value] = value
            elif is_foreign_key:
                import_data.setdefault("fk_mappings", {})
                import_data["fk_mappings"].setdefault(field_name, {})
                import_data["fk_mappings"][field_name][slug_value] = str(
                    value
                )  # Store as string
            else:
                return HttpResponse(
                    '<span class="bg-red-100 text-red-500 text-xs font-medium px-2 py-0.5 rounded-full">Error: Invalid field type</span>'
                )

            request.session["import_data"] = import_data
            request.session.modified = True

            return HttpResponse(
                '<span class="bg-green-100 text-green-500 text-xs font-medium px-2 py-0.5 rounded-full">Mapped</span>'
            )
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(tb)
            return HttpResponse(
                f'<span class="bg-red-100 text-red-500 text-xs font-medium px-2 py-0.5 rounded-full">Error: {str(e)}</span>'
            )


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class DownloadErrorFileView(LoginRequiredMixin, View):
    """Download error CSV file"""

    def get(self, request, *args, **kwargs):
        file_path = request.GET.get("file_path")
        if not file_path:
            raise HorillaHttp404("File path not provided")

        try:
            if not default_storage.exists(file_path):
                return HttpResponse("File not found", status=404)

            if not file_path.startswith("import_errors/"):
                return HttpResponse("Access denied", status=403)

            with default_storage.open(file_path, "rb") as file:
                response = HttpResponse(file.read(), content_type="text/csv")

                # Extract filename from path
                filename = file_path.split("/")[-1]
                response["Content-Disposition"] = f'attachment; filename="{filename}"'

                return response

        except Exception as e:
            logger.error(f"Error downloading error file: {str(e)}")
            return HttpResponse("Error downloading file", status=500)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class ImportHistoryView(LoginRequiredMixin, HorillaListView):

    model = ImportHistory
    view_id = "import-history"
    search_url = reverse_lazy("horilla_core:import_history_view")
    main_url = reverse_lazy("horilla_core:import_history_view")
    table_width = False
    table_height_as_class = "h-[58vh]"

    header_attrs = [
        {"imported_file_path": {"style": "width: 300px;"}},
        {"error_file_path": {"style": "width: 500px;"}},
    ]

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("import_name").verbose_name, "import_name"),
            (instance._meta.get_field("module_name").verbose_name, "module_name"),
            (
                instance._meta.get_field("original_filename").verbose_name,
                "original_filename",
            ),
            (instance._meta.get_field("status").verbose_name, "get_status_display"),
            (instance._meta.get_field("success_rate").verbose_name, "success_rate"),
            (
                instance._meta.get_field("duration_seconds").verbose_name,
                "duration_seconds",
            ),
            (instance._meta.get_field("created_at").verbose_name, "created_at"),
            (instance._meta.get_field("created_by").verbose_name, "created_by"),
            (
                instance._meta.get_field("imported_file_path").verbose_name,
                "imported_file",
            ),
            (instance._meta.get_field("error_file_path").verbose_name, "error_list"),
        ]


@method_decorator(
    permission_required_or_denied("horilla_core.can_view_horilla_import"),
    name="dispatch",
)
class DownloadImportedFileView(LoginRequiredMixin, View):
    """Download the original imported file"""

    def get(self, request, *args, **kwargs):
        file_path = request.GET.get("file_path")

        if not file_path:
            raise HorillaHttp404("File path not provided")

        try:
            if not default_storage.exists(file_path):
                return HttpResponse("Imported file not found", status=404)

            # Optional: Add a security check to ensure the file is in a specific directory
            if not file_path.startswith(
                "imports/"
            ):  # Adjust the directory as per your storage structure
                return HttpResponse("Access denied", status=403)

            with default_storage.open(file_path, "rb") as file:
                content = file.read()

                # Determine content type based on file extension
                content_type = (
                    "text/csv"
                    if file_path.endswith(".csv")
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                response = HttpResponse(content, content_type=content_type)
                filename = file_path.split("/")[-1]
                response["Content-Disposition"] = f'attachment; filename="{filename}"'
                return response

        except Exception as e:
            logger.error(f"Error downloading imported file: {str(e)}")
            tb = traceback.format_exc()
            logger.error(tb)
            return HttpResponse(
                f"Error downloading imported file: {str(e)}", status=500
            )
