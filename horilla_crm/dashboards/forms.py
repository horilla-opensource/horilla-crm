"""Forms for dashboards app."""

import logging

from django import forms
from django.apps import apps
from django.db import models
from django.urls import reverse_lazy

from horilla_core.models import HorillaContentType
from horilla_generics.forms import HorillaModelForm

from .models import ComponentCriteria, DashboardComponent

logger = logging.getLogger(__name__)


class DashboardCreateForm(HorillaModelForm):
    """Dashboard Create Form"""

    class Meta:
        """Meta class for DashboardCreateForm"""

        model = DashboardComponent
        fields = "__all__"
        exclude = [
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "additional_info",
        ]
        widgets = {
            "component_type": forms.Select(
                attrs={
                    "id": "id_component_type",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        self.row_id = kwargs.pop("row_id", "0")
        kwargs["condition_model"] = ComponentCriteria
        self.instance_obj = kwargs.get("instance")

        model_name = None
        request = kwargs.get("request")
        self.request = request

        if request:
            model_name = (
                request.GET.get("model_name")
                or request.POST.get("model_name")
                or request.GET.get("module")
            )
        module_id = request.GET.get("module") or request.POST.get("module")
        if module_id and module_id.isdigit():
            try:
                content_type = HorillaContentType.objects.get(pk=module_id)
                model_name = content_type.model
            except HorillaContentType.DoesNotExist:
                pass

        if not model_name and self.instance_obj and self.instance_obj.module:
            model_name = self.instance_obj.module.model

        if not model_name and "initial" in kwargs and "module" in kwargs["initial"]:
            initial_module = kwargs["initial"]["module"]
            if isinstance(initial_module, HorillaContentType):
                model_name = initial_module.model
            else:
                model_name = initial_module

        condition_field_choices = {
            "field": self._get_model_field_choices(model_name),
        }
        kwargs["condition_field_choices"] = condition_field_choices

        super().__init__(*args, **kwargs)

        if "module" in self.fields and request and hasattr(request, "user"):
            user = request.user
            allowed_modules = []

            module_map = {
                "lead": "leads.Lead",
                "opportunity": "opportunities.Opportunity",
                "campaign": "campaigns.Campaign",
                "activity": "activities.Activity",
                "account": "accounts.Account",
                "contact": "contacts.Contact",
            }

            for module, model_path in module_map.items():
                app_label, model_name_ = model_path.split(".")
                view_perm = f"{app_label}.view_{model_name_.lower()}"
                view_own_perm = f"{app_label}.view_own_{model_name_.lower()}"
                if user.has_perm(view_perm) or user.has_perm(view_own_perm):
                    allowed_modules.append((module, module.title()))

            self.fields["module"].choices = allowed_modules

        def hide_fields(field_list, nullify=False):
            for name in field_list:
                if name in self.fields:
                    self.fields[name].widget = forms.HiddenInput(
                        attrs={"required": False}
                    )
                    if nullify:
                        self.fields[name].initial = None
                        if self.data:
                            self.data = self.data.copy()
                            self.data[name] = None

        # Hide fields based on component_type
        component_type = self.request.GET.get("component_type") or (
            self.instance_obj.component_type if self.instance_obj else ""
        )

        nullify_values = (
            self.request.method == "GET" if hasattr(self, "request") else True
        )
        if component_type != "chart":
            hide_fields(["chart_type", "secondary_grouping"], nullify=nullify_values)

        if component_type != "kpi":
            hide_fields(["icon"], nullify=nullify_values)

        if component_type == "table_data":
            hide_fields(
                ["grouping_field", "metric_field", "metric_type"],
                nullify=nullify_values,
            )

        if component_type != "table_data":
            hide_fields(["columns"], nullify=nullify_values)
        else:
            if "columns" in self.fields:
                self.fields["columns"].widget = forms.SelectMultiple(
                    attrs={
                        "class": "js-example-basic-multiple headselect",
                        "id": "id_columns",
                        "name": "columns",
                        "data-placeholder": "Add Columns",
                        "tabindex": "-1",
                        "aria-hidden": "true",
                        "multiple": True,
                    }
                )

        self.model_name = model_name or ""
        self._add_htmx_to_field_selects()
        self._add_htmx_to_module_select()

        if self.instance_obj and self.instance_obj.pk and model_name:
            self._initialize_select_fields_for_edit(model_name)

        if self.instance_obj and self.instance_obj.pk:
            self._set_initial_condition_values()

    def _initialize_select_fields_for_edit(self, model_name):
        """Initialize select fields in edit mode by mimicking HTMX view behavior"""
        try:
            model = None
            for app_config in apps.get_app_configs():
                try:
                    model = apps.get_model(
                        app_label=app_config.label, model_name=model_name.lower()
                    )
                    break
                except LookupError:
                    continue

            if not model:
                return

            if "metric_field" in self.fields:
                metric_fields = []
                for field in model._meta.get_fields():
                    if field.concrete and not field.is_relation:
                        field_name = field.name
                        field_label = field.verbose_name or field.name

                        if hasattr(field, "get_internal_type"):
                            field_type = field.get_internal_type()
                            if field_type in [
                                "IntegerField",
                                "FloatField",
                                "DecimalField",
                                "BigIntegerField",
                                "SmallIntegerField",
                                "PositiveIntegerField",
                                "PositiveSmallIntegerField",
                                "CharField",
                                "TextField",
                                "BooleanField",
                                "DateField",
                                "DateTimeField",
                                "TimeField",
                                "EmailField",
                                "URLField",
                            ]:
                                metric_fields.append((field_name, f"{field_label}"))
                            elif hasattr(field, "choices") and field.choices:
                                metric_fields.append((field_name, f"{field_label}"))

                    elif hasattr(field, "related_model") and field.many_to_one:
                        field_name = field.name
                        field_label = field.verbose_name or field.name
                        metric_fields.append((field_name, f"{field_label}"))

                current_value = (
                    getattr(self.instance_obj, "metric_field", "")
                    if self.instance_obj
                    else ""
                )
                self.fields["metric_field"] = forms.ChoiceField(
                    choices=[("", "Select Metric Field")] + metric_fields,
                    required=False,
                    initial=current_value,
                    widget=forms.Select(
                        attrs={
                            "class": "js-example-basic-single headselect",
                            "id": "id_metric_field",
                            "name": "metric_field",
                        }
                    ),
                )

            if "grouping_field" in self.fields:
                grouping_fields = []
                for field in model._meta.get_fields():
                    if field.concrete and not field.is_relation:
                        field_name = field.name
                        field_label = field.verbose_name or field.name

                        if hasattr(field, "get_internal_type"):
                            field_type = field.get_internal_type()
                            if field_type in [
                                "CharField",
                                "TextField",
                                "BooleanField",
                                "DateField",
                                "DateTimeField",
                                "TimeField",
                                "EmailField",
                                "URLField",
                            ]:
                                grouping_fields.append((field_name, field_label))
                            elif hasattr(field, "choices") and field.choices:
                                grouping_fields.append((field_name, f"{field_label}"))

                    elif hasattr(field, "related_model") and field.many_to_one:
                        field_name = field.name
                        field_label = field.verbose_name or field.name
                        grouping_fields.append((field_name, f"{field_label}"))

                current_value = (
                    getattr(self.instance_obj, "grouping_field", "")
                    if self.instance_obj
                    else ""
                )
                self.fields["grouping_field"] = forms.ChoiceField(
                    choices=[("", "Select Grouping Field")] + grouping_fields,
                    required=False,
                    initial=current_value,
                    widget=forms.Select(
                        attrs={
                            "class": "js-example-basic-single headselect",
                            "id": "id_grouping_field",
                            "name": "grouping_field",
                        }
                    ),
                )

            # Initialize secondary_grouping_field
            if "secondary_grouping" in self.fields:
                secondary_grouping_fields = []
                for field in model._meta.get_fields():
                    if field.concrete and not field.is_relation:
                        field_name = field.name
                        field_label = field.verbose_name or field.name
                        if hasattr(field, "get_internal_type"):
                            field_type = field.get_internal_type()
                            if field_type in [
                                "CharField",
                                "TextField",
                                "BooleanField",
                                "DateField",
                                "DateTimeField",
                                "TimeField",
                                "EmailField",
                                "URLField",
                            ]:
                                secondary_grouping_fields.append(
                                    (field_name, field_label)
                                )
                            elif hasattr(field, "choices") and field.choices:
                                secondary_grouping_fields.append(
                                    (field_name, f"{field_label}")
                                )
                    elif hasattr(field, "related_model") and field.many_to_one:
                        field_name = field.name
                        field_label = field.verbose_name or field.name
                        secondary_grouping_fields.append((field_name, f"{field_label}"))

                current_value = (
                    getattr(self.instance_obj, "secondary_grouping_field", "")
                    if self.instance_obj
                    else ""
                )
                self.fields["secondary_grouping"] = forms.ChoiceField(
                    choices=[("", "Select Secondary Grouping Field")]
                    + secondary_grouping_fields,
                    required=False,
                    initial=current_value,
                    widget=forms.Select(
                        attrs={
                            "class": "js-example-basic-single headselect",
                            "id": "id_secondary_grouping",
                            "name": "secondary_grouping",
                        }
                    ),
                )

        except Exception as e:
            logger.error("Error initializing select fields for edit: {%s}", e)

    def _set_initial_condition_values(self):
        """Set initial values for condition fields in edit mode"""
        if not self.instance_obj or not self.instance_obj.pk:
            return

        existing_conditions = self.instance_obj.conditions.all().order_by("sequence")
        if hasattr(self, "row_id") and self.row_id != "0":
            return

        if existing_conditions.exists():
            first_condition = existing_conditions.first()
            for field_name in self.condition_fields:
                if field_name in self.fields:
                    value = getattr(first_condition, field_name, "")
                    self.fields[field_name].initial = value
                    field_key_0 = f"{field_name}_0"
                    if field_key_0 in self.fields:
                        self.fields[field_key_0].initial = value

    def _add_htmx_to_module_select(self):
        """Add HTMX attributes to the module select widget for dynamic condition field updates"""
        module_field = self.fields.get("module")
        if module_field and hasattr(module_field.widget, "attrs"):
            row_id = getattr(self, "row_id", "0")
            module_field.widget.attrs.update(
                {
                    "hx-get": reverse_lazy("dashboards:get_module_field_choices"),
                    "hx-target": f"#id_field_{row_id}_container",
                    "hx-swap": "innerHTML",
                    "hx-include": '[name="module"]',
                    "hx-vals": f'{{"row_id": "{row_id}"}}',
                    "hx-trigger": "change",
                    # Add additional HTMX attributes for multiple requests
                    "hx-get-metric": reverse_lazy(
                        "dashboards:get_metric_field_choices"
                    ),
                    "hx-target-metric": "#id_metric_field_container",
                    "hx-get-grouping": reverse_lazy(
                        "dashboards:get_grouping_field_choices"
                    ),
                    "hx-target-grouping": "#id_grouping_field_container",
                    "hx-get-columns": reverse_lazy(
                        "dashboards:get_columns_field_choices"
                    ),
                    "hx-target-columns": "#columns_container",
                    "hx-get-secondary-grouping": reverse_lazy(
                        "dashboards:get_secondary_grouping_field_choices"
                    ),
                    "hx-target-secondary-grouping": "#id_secondary_grouping_container",
                }
            )

    def _set_initial_condition_values(self):
        """Set initial values for condition fields in edit mode"""
        if not self.instance_obj or not self.instance_obj.pk:
            return

        existing_conditions = self.instance_obj.conditions.all().order_by("sequence")
        if hasattr(self, "row_id") and self.row_id != "0":
            return

        if existing_conditions.exists():
            first_condition = existing_conditions.first()
            for field_name in self.condition_fields:
                if field_name in self.fields:
                    value = getattr(first_condition, field_name, "")
                    self.fields[field_name].initial = value
                    field_key_0 = f"{field_name}_0"
                    if field_key_0 in self.fields:
                        self.fields[field_key_0].initial = value

    def _add_htmx_to_field_selects(self):
        """Add HTMX attributes to field select widgets for dynamic value field updates"""
        model_name = getattr(self, "model_name", "")
        row_id = getattr(self, "row_id", "0")

        for field_name, field in self.fields.items():
            if field_name.startswith("field") or field_name == "field":
                if hasattr(field.widget, "attrs"):
                    field.widget.attrs.update(
                        {
                            "name": f"field_{row_id}",
                            "id": f"id_field_{row_id}",
                            "hx-get": reverse_lazy(
                                "horilla_generics:get_field_value_widget"
                            ),
                            "hx-target": f"#id_value_{row_id}_container",
                            "hx-swap": "innerHTML",
                            "hx-include": f'[name="field_{row_id}"],#id_value_{row_id},[name="module"]',  # Include module
                            "hx-vals": f'{{"model_name": "{model_name}", "row_id": "{row_id}"}}',
                            "hx-trigger": "change,load",
                        }
                    )

    def _get_model_field_choices(self, model_name):
        """Get field choices for the specified model"""
        field_choices = [("", "---------")]

        if model_name:
            try:
                model = None
                for app_config in apps.get_app_configs():
                    try:
                        model = apps.get_model(
                            app_label=app_config.label, model_name=model_name
                        )
                        break
                    except LookupError:
                        continue

                if model:
                    model_fields = []
                    for field in model._meta.get_fields():
                        if field.concrete or field.is_relation:
                            verbose_name = getattr(field, "verbose_name", field.name)
                            if field.is_relation:
                                verbose_name = f"{verbose_name} (FK)"
                            model_fields.append((field.name, verbose_name))
                    field_choices.extend(model_fields)

            except Exception as e:
                logger.error("Error fetching model {model_name}: {%s}", e)

        return field_choices

    def _add_condition_fields(self):
        """Override to add HTMX-enabled condition fields with proper initialization"""
        for field_name in self.condition_fields:
            try:
                model_field = self.condition_model._meta.get_field(field_name)

                # Create base field (for row 0 and template access)
                if field_name == "field" and field_name in self.condition_field_choices:
                    model_name = getattr(self, "model_name", "")
                    form_field = forms.ChoiceField(
                        choices=self.condition_field_choices[field_name],
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.Select(
                            attrs={
                                "class": "js-example-basic-single headselect",
                                "data-placeholder": f'Select {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                                "hx-get": reverse_lazy(
                                    "horilla_generics:get_field_value_widget"
                                ),
                                "hx-target": "#id_value_0_container",
                                "hx-swap": "innerHTML",
                                "hx-vals": f'{{"model_name": "{model_name}", "row_id": "0"}}',
                                "hx-include": f'[name="{field_name}_0"],[name="module"]',  # Include module
                                "hx-trigger": "change,load",
                            }
                        ),
                    )
                elif field_name == "value":
                    form_field = forms.CharField(
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.TextInput(
                            attrs={
                                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                                "placeholder": f'Enter {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                                "data-container-id": "value-field-container-0",
                            }
                        ),
                    )
                elif field_name in self.condition_field_choices:
                    form_field = forms.ChoiceField(
                        choices=self.condition_field_choices[field_name],
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.Select(
                            attrs={
                                "class": "js-example-basic-single headselect",
                                "data-placeholder": f'Select {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )
                elif hasattr(model_field, "choices") and model_field.choices:
                    form_field = forms.ChoiceField(
                        choices=[("", "---------")] + list(model_field.choices),
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.Select(
                            attrs={
                                "class": "js-example-basic-single headselect",
                                "data-placeholder": f'Select {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )
                elif isinstance(model_field, models.CharField):
                    form_field = forms.CharField(
                        max_length=model_field.max_length,
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.TextInput(
                            attrs={
                                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                                "placeholder": f'Enter {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )
                elif isinstance(model_field, models.IntegerField):
                    form_field = forms.IntegerField(
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.NumberInput(
                            attrs={
                                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                                "placeholder": f'Enter {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )
                elif isinstance(model_field, models.BooleanField):
                    form_field = forms.BooleanField(
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.CheckboxInput(
                            attrs={
                                "class": "sr-only peer",
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )
                else:
                    form_field = forms.CharField(
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.TextInput(
                            attrs={
                                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                                "placeholder": f'Enter {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}_0",
                                "name": f"{field_name}_0",
                            }
                        ),
                    )

                form_field.is_custom_field = True
                self.fields[field_name] = form_field

            except Exception as e:
                logger.error("Error adding condition field {field_name}: %s", e)

    def _extract_condition_rows(self):
        condition_rows = []
        condition_fields = ["field", "operator", "value"]

        if not self.data:
            return condition_rows

        row_ids = set()

        for key in self.data.keys():
            for field_name in condition_fields:
                if key.startswith(f"{field_name}_"):
                    row_id = key.replace(f"{field_name}_", "")
                    if row_id.isdigit():
                        row_ids.add(row_id)

        if any(f in self.data for f in condition_fields) or any(
            f"{f}_0" in self.data for f in condition_fields
        ):
            row_ids.add("0")

        for row_id in sorted(row_ids, key=lambda x: int(x)):
            row_data = {}
            has_required_data = True

            for field_name in condition_fields:
                if row_id == "0":
                    field_key = (
                        f"{field_name}_0"
                        if f"{field_name}_0" in self.data
                        else field_name
                    )
                else:
                    field_key = f"{field_name}_{row_id}"

                value = self.data.get(field_key, "").strip()
                row_data[field_name] = value

                if field_name in ["field", "operator"] and not value:
                    has_required_data = False

            if has_required_data and row_data.get("field") and row_data.get("operator"):
                row_data["sequence"] = int(row_id)

                condition_rows.append(row_data)

        return condition_rows

    def clean(self):
        """Process multiple condition rows from form data"""
        cleaned_data = super().clean()

        condition_rows = self._extract_condition_rows()
        cleaned_data["condition_rows"] = condition_rows

        raw_columns = self.data.getlist("columns")
        if raw_columns and "columns" in cleaned_data:
            cleaned_data["columns"] = raw_columns

        return cleaned_data

    def clean_columns(self):
        """Clean the columns field to store as comma-separated values"""
        raw_columns = self.data.getlist("columns")
        columns = self.cleaned_data.get("columns")

        if raw_columns:
            columns = raw_columns

        elif isinstance(columns, str):
            columns = [col.strip() for col in columns.split(",") if col.strip()]

        elif not isinstance(columns, (list, tuple)):
            columns = raw_columns if raw_columns else [columns]

        if not columns:
            return ""

        column_list = [str(col) for col in columns if col]
        result = ",".join(column_list)
        return result
