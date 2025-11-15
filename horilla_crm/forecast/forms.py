"""
Module containing forms for ForecastTarget and ForecastType management,
including dynamic condition handling and role-based logic.
"""

import logging

from django import forms
from django.apps import apps
from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla_core.models import HorillaUser
from horilla_crm.opportunities.models import Opportunity
from horilla_generics.forms import HorillaModelForm

from .models import ForecastCondition, ForecastTarget, ForecastType

logger = logging.getLogger(__name__)


class ForecastTargetForm(HorillaModelForm):
    """Form to create or update forecast targets with dynamic conditions."""

    is_role_based = forms.BooleanField(
        required=False,
        label="Role-Based Assignment",
        help_text="Filter users by selected role",
        widget=forms.CheckboxInput(
            attrs={
                "class": "sr-only peer",
                "hx-post": reverse_lazy("forecast:toggle_role_based"),
                "hx-target": "#condition-fields-container",
                "hx-swap": "innerHTML",
                "hx-include": '[name="role"],[name="is_role_based"],[name="is_period_same"],[name="is_target_same"],[name="is_forecast_type_same"],[name="period"],[name="target_amount"],[name="forcasts_type"]',
                "hx-trigger": "change",
            }
        ),
    )

    is_period_same = forms.BooleanField(
        required=False,
        label="Same Period for All",
        help_text="Apply the same period for all users",
        widget=forms.CheckboxInput(
            attrs={
                "class": "sr-only peer",
                "hx-post": reverse_lazy("forecast:toggle_condition_fields"),
                "hx-target": "#condition-fields-container",
                "hx-swap": "innerHTML",
                "hx-include": '[name="is_period_same"],[name="is_target_same"],[name="is_forecast_type_same"],[name="period"],[name="target_amount"],[name="forcasts_type"],[name="role"],[name="is_role_based"]',
                "hx-trigger": "change",
            }
        ),
    )

    is_target_same = forms.BooleanField(
        required=False,
        label="Same Target for All",
        help_text="Apply the same target amount for all users",
        widget=forms.CheckboxInput(
            attrs={
                "class": "sr-only peer",
                "hx-post": reverse_lazy("forecast:toggle_condition_fields"),
                "hx-target": "#condition-fields-container",
                "hx-swap": "innerHTML",
                "hx-include": '[name="is_period_same"],[name="is_target_same"],[name="is_forecast_type_same"],[name="period"],[name="target_amount"],[name="forcasts_type"],[name="role"],[name="is_role_based"]',
                "hx-trigger": "change",
            }
        ),
    )

    is_forecast_type_same = forms.BooleanField(
        required=False,
        label="Same Forecast Type for All",
        help_text="Apply the same forecast type for all users",
        widget=forms.CheckboxInput(
            attrs={
                "class": "sr-only peer",
                "hx-post": reverse_lazy("forecast:toggle_condition_fields"),
                "hx-target": "#condition-fields-container",
                "hx-swap": "innerHTML",
                "hx-include": '[name="is_period_same"],[name="is_target_same"],[name="is_forecast_type_same"],[name="period"],[name="target_amount"],[name="forcasts_type"],[name="role"],[name="is_role_based"]',
                "hx-trigger": "change",
            }
        ),
    )

    class Meta:
        """Meta settings for ForecastTargetForm."""

        model = ForecastTarget
        fields = [
            "role",
            "assigned_to",
            "period",
            "forcasts_type",
            "target_amount",
            "is_role_based",
            "is_period_same",
            "is_target_same",
            "is_forecast_type_same",
        ]
        exclude = [
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "additional_info",
        ]
        widgets = {
            "target_amount": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "placeholder": "Enter target"}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.row_id = kwargs.pop("row_id", None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.role:
            self.fields["is_role_based"].initial = True

        # Make these fields not required on the main form since they're handled in condition rows
        if "assigned_to" in self.fields:
            self.fields["assigned_to"].required = False
            self.fields["assigned_to"].label = "Assigned To"
            self.fields["assigned_to"].help_text = (
                "Select the user to assign this forecast target"
            )

        if "target_amount" in self.fields:
            self.fields["target_amount"].required = False
            self.fields["target_amount"].label = "Target Amount"
            self.fields["target_amount"].help_text = "Enter the forecast target amount"

        if "period" in self.fields:
            self.fields["period"].required = False

        if "forcasts_type" in self.fields:
            self.fields["forcasts_type"].required = False
            self.fields["forcasts_type"].widget.attrs.update(
                {
                    "hx-post": reverse_lazy("forecast:update_target_help_text"),
                    "hx-target": (
                        "#target_amount_help_text"
                        if not self.row_id
                        else f"#target_amount_help_text_{self.row_id}"
                    ),
                    "hx-swap": "innerHTML",
                    "hx-include": '[name="forcasts_type"]',
                    "hx-trigger": "change",
                }
            )

        if "role" in self.fields:
            self.fields["role"].widget.attrs.update(
                {
                    "hx-post": reverse_lazy("forecast:toggle_role_based"),
                    "hx-target": "#condition-fields-container",
                    "hx-swap": "innerHTML",
                    "hx-include": '[name="role"],[name="is_role_based"],[name="is_period_same"],[name="is_target_same"],[name="is_forecast_type_same"],[name="period"],[name="target_amount"],[name="forcasts_type"]',
                    "hx-trigger": "change",
                }
            )

    def clean_target_amount(self):
        """Validate that target amount is non-negative."""
        target_amount = self.cleaned_data.get("target_amount")
        if target_amount is not None and target_amount < 0:
            raise forms.ValidationError("Target amount cannot be negative.")
        return target_amount

    def clean(self):
        """Validate role-based assignment logic and user-role matching."""
        cleaned_data = super().clean()
        assigned_to = cleaned_data.get("assigned_to")
        role = cleaned_data.get("role")
        is_role_based = cleaned_data.get("is_role_based")

        # Only validate role-based logic, not required fields since this form doesn't save directly
        if is_role_based and not role:
            self.add_error(
                "role", "Role is required when role-based assignment is selected."
            )
        if is_role_based and assigned_to and role:
            if not HorillaUser.objects.filter(id=assigned_to.id, role=role).exists():
                self.add_error(
                    "assigned_to", "Selected user does not belong to the selected role."
                )

        return cleaned_data


class ForecastTypeForm(HorillaModelForm):
    """Form to create or update forecast types with condition rows."""

    def __init__(self, *args, **kwargs):
        self.row_id = kwargs.pop("row_id", "0")
        kwargs["condition_model"] = ForecastCondition
        self.instance_obj = kwargs.get("instance")

        model_name = "opportunity"  # Since forecast is always for opportunities
        request = kwargs.get("request")
        if request:
            model_name = (
                request.GET.get("model_name")
                or request.POST.get("model_name")
                or "opportunity"
            )

        condition_field_choices = {
            "field": self._get_model_field_choices(model_name),
            "operator": [
                ("", "---------"),
                ("equals", "Equals"),
                ("not_equals", "Not Equals"),
                ("contains", "Contains"),
                ("not_contains", "Does Not Contain"),
                ("starts_with", "Starts With"),
                ("ends_with", "Ends With"),
                ("greater_than", "Greater Than"),
                ("greater_than_equal", "Greater Than or Equal"),
                ("less_than", "Less Than"),
                ("less_than_equal", "Less Than or Equal"),
                ("is_empty", "Is Empty"),
                ("is_not_empty", "Is Not Empty"),
            ],
            "logical_operator": [
                ("", "---------"),
                ("and", "AND"),
                ("or", "OR"),
            ],
        }
        kwargs["condition_field_choices"] = condition_field_choices

        super().__init__(*args, **kwargs)
        self.model_name = model_name or "opportunity"
        self._add_htmx_to_field_selects()

        if self.instance_obj and self.instance_obj.pk:
            self._set_initial_condition_values()

    def _set_initial_condition_values(self):
        """Set initial values for condition fields in edit mode"""
        if not self.instance_obj or not self.instance_obj.pk:
            return

        existing_conditions = self.instance_obj.conditions.all().order_by("order")
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
        model_name = getattr(self, "model_name", "opportunity")
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
                            "hx-include": f'[name="field_{row_id}"],#id_value_{row_id}',
                            "hx-vals": f'{{"model_name": "{model_name}", "row_id": "{row_id}"}}',
                            "hx-trigger": "change,load",
                        }
                    )

    def _get_model_field_choices(self, _model_name):
        """Get field choices for the opportunity model"""
        field_choices = [("", "---------")]

        try:
            try:
                opportunity_model = apps.get_model("crm", "Opportunity")
            except Exception:
                opportunity_model = Opportunity

            if opportunity_model:
                for field in opportunity_model._meta.get_fields():
                    if (
                        not field.name.startswith("_")
                        and field.name
                        not in [
                            "id",
                            "created_at",
                            "updated_at",
                            "created_by",
                            "updated_by",
                        ]
                        and not field.one_to_many
                        and not field.many_to_many
                        and not getattr(field, "related_name", None)
                    ):
                        verbose_name = getattr(
                            field, "verbose_name", field.name.replace("_", " ").title()
                        )
                        field_choices.append((field.name, verbose_name))

        except Exception as e:
            logger.error("Error fetching model opportunity: %s", e)

        return field_choices

    def _add_condition_fields(self):
        """Override to add HTMX-enabled condition fields with proper initialization"""
        for field_name in self.condition_fields:
            try:
                model_field = self.condition_model._meta.get_field(field_name)

                # Create base field (for row 0 and template access)
                if field_name == "field" and field_name in self.condition_field_choices:
                    model_name = getattr(self, "model_name", "opportunity")
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
                                "hx-include": f'[name="{field_name}_0"]',
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
                logger.error("Error adding condition field %s: %s", field_name, e)

        # Set initial values for edit mode
        self._set_initial_condition_values()

    def clean(self):
        """Process multiple condition rows from form data"""
        cleaned_data = super().clean()

        condition_rows = self._extract_condition_rows()

        cleaned_data["condition_rows"] = condition_rows

        return cleaned_data

    def _extract_condition_rows(self):
        """Extract condition rows from POST data for saving."""
        condition_rows = []
        condition_fields = ["field", "operator", "value", "logical_operator"]

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
                row_data["order"] = int(row_id)
                condition_rows.append(row_data)

        return condition_rows

    class Meta:
        """Meta settings for ForecastTypeForm."""

        model = ForecastType
        fields = ["name", "forecast_type", "description"]
        exclude = [
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "additional_info",
        ]
