"""Forms for managing Opportunity-related models in the CRM application."""

import logging

from django import forms
from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla_core.mixins import OwnerQuerysetMixin
from horilla_crm.opportunities.models import (
    DefaultOpportunityMember,
    Opportunity,
    OpportunityStage,
    OpportunityTeam,
    OpportunityTeamMember,
)
from horilla_generics.forms import HorillaModelForm, HorillaMultiStepForm

logger = logging.getLogger(__name__)


class OpportunityFormClass(OwnerQuerysetMixin, HorillaMultiStepForm):
    """Multi-step form for creating/editing Opportunity instances.
    Inherits from HorillaMultiStepForm to preserve all existing behavior.
    """

    class Meta:
        """Meta options for OpportunityFormClass."""

        model = Opportunity
        fields = "__all__"

    step_fields = {
        1: [
            "name",
            "amount",
            "quantity",
            "close_date",
            "stage",
            "probability",
            "account",
            "tracking_number",
        ],
        2: [
            "next_step",
            "primary_campaign_source",
            "owner",
            "opportunity_type",
            "order_number",
        ],
        3: [
            "lead_source",
            "delivery_installation_status",
            "forecast_category",
            "main_competitors",
        ],
        4: ["description"],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make created_by and updated_by optional in intermediate steps
        if self.current_step < len(self.step_fields):
            self.fields["created_by"].required = False
            self.fields["updated_by"].required = False


class OpportunityStageForm(HorillaModelForm):
    """
    Custom form for LeadStatus to add HTMX attributes to is_final field.
    Inherits from HorillaModelForm to preserve all existing behavior.
    """

    class Meta:
        """Meta options for OpportunityStageForm."""

        model = OpportunityStage
        fields = ["name", "probability", "is_final", "order", "stage_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "is_final" in self.fields:
            self.fields["is_final"].widget.attrs.update(
                {
                    "hx-post": reverse_lazy("opportunities:toggle_order_field"),
                    "hx-target": "#order_container",
                    "hx-swap": "outerHTML",
                    "hx-trigger": "change",
                }
            )


class OpportunityTeamForm(HorillaModelForm):
    """Custom form for OpportunityTeam to manage team members for opportunities."""

    def __init__(self, *args, **kwargs):
        self.row_id = kwargs.pop("row_id", "0")
        kwargs["condition_model"] = DefaultOpportunityMember
        self.instance_obj = kwargs.get("instance")

        model_name = None
        request = kwargs.get("request")
        if request:
            model_name = request.GET.get("model_name") or request.POST.get("model_name")

        # Set up condition field choices similar to ScoringCriterionForm
        condition_field_choices = self._get_condition_field_choices()
        kwargs["condition_field_choices"] = condition_field_choices

        super().__init__(*args, **kwargs)
        self.model_name = model_name or ""
        self.condition_field_choices = condition_field_choices

        # Set initial values for condition fields in edit mode
        if self.instance_obj and self.instance_obj.pk:
            self._set_initial_condition_values()

    def _get_condition_field_choices(self):
        """Get condition field choices for OpportunityTeam form"""
        condition_field_choices = {}

        try:
            # Get choices for user field (ForeignKey)
            from .models import HorillaUser  # Import here to avoid circular imports

            user_choices = [("", "---------")]
            users = HorillaUser.objects.all()[:100]  # Limit for performance
            user_choices.extend([(user.pk, str(user)) for user in users])
            condition_field_choices["user"] = user_choices

            # Get choices for team_role field (assuming it has choices)
            team_role_field = DefaultOpportunityMember._meta.get_field("team_role")
            if hasattr(team_role_field, "choices") and team_role_field.choices:
                condition_field_choices["team_role"] = [("", "---------")] + list(
                    team_role_field.choices
                )

            # Get choices for opportunity_access_level field (assuming it has choices)
            access_level_field = DefaultOpportunityMember._meta.get_field(
                "opportunity_access_level"
            )
            if hasattr(access_level_field, "choices") and access_level_field.choices:
                condition_field_choices["opportunity_access_level"] = [
                    ("", "---------")
                ] + list(access_level_field.choices)

        except Exception as e:
            logger.error("Error getting condition field choices: %s", e)

        return condition_field_choices

    def _add_condition_fields(self):
        """Override to add properly configured condition fields"""
        for field_name in self.condition_fields:
            try:
                model_field = self.condition_model._meta.get_field(field_name)

                # Create base field (for row 0 and template access)
                if field_name == "user" and field_name in self.condition_field_choices:
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
                elif isinstance(model_field, models.ForeignKey):
                    # Handle ForeignKey fields
                    related_model = model_field.related_model
                    app_label = related_model._meta.app_label
                    model_name = related_model._meta.model_name

                    initial_choices = []
                    try:
                        queryset = related_model.objects.all()[:100]
                        initial_choices = [(obj.pk, str(obj)) for obj in queryset]
                    except Exception as e:
                        logger.error("Error fetching choices for %s: %s", field_name, e)

                    form_field = forms.ChoiceField(
                        choices=[("", "---------")] + initial_choices,
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.Select(
                            attrs={
                                "class": "select2-pagination w-full",
                                "data-url": reverse_lazy(
                                    "horilla_generics:model_select2",
                                    kwargs={
                                        "app_label": app_label,
                                        "model_name": model_name,
                                    },
                                ),
                                "data-placeholder": f"Select {model_field.verbose_name.title()}",
                                "data-field-name": field_name,
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
                else:
                    # Fallback to text input for other field types
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

    def _set_initial_condition_values(self):
        """Set initial values for condition fields in edit mode"""
        if not self.instance_obj or not self.instance_obj.pk:
            return

        # Get existing team members (conditions) ordered by creation
        existing_members = DefaultOpportunityMember.objects.filter(
            team=self.instance_obj
        ).order_by("created_at")

        if hasattr(self, "row_id") and self.row_id != "0":
            return

        if existing_members.exists():
            first_member = existing_members.first()
            for field_name in self.condition_fields:
                if field_name in self.fields:
                    value = getattr(first_member, field_name, "")
                    # Handle ForeignKey fields
                    if field_name == "user" and value:
                        value = value.pk if hasattr(value, "pk") else value

                    self.fields[field_name].initial = value
                    field_key_0 = f"{field_name}_0"
                    if field_key_0 in self.fields:
                        self.fields[field_key_0].initial = value

    def _extract_condition_rows(self):
        """Extract condition rows from form data"""
        condition_rows = []
        row_ids = set()

        # Identify all row IDs from form data (e.g., user_0, team_role_1)
        for field_name in self.data:
            if "_" in field_name:
                base_name, row_id = field_name.rsplit("_", 1)
                if base_name in self.condition_fields and row_id.isdigit():
                    row_ids.add(row_id)

        for row_id in sorted(row_ids, key=int):
            row_data = {}
            valid_row = True
            for field_name in self.condition_fields:
                form_field_name = f"{field_name}_{row_id}"
                if form_field_name in self.data:
                    value = self.data.get(form_field_name)
                    if value:
                        if field_name == "user":
                            try:
                                from .models import (  # Import here to avoid circular imports
                                    HorillaUser,
                                )

                                value = HorillaUser.objects.get(pk=value)
                            except (HorillaUser.DoesNotExist, ValueError):
                                self.add_error(
                                    None, f"Invalid user selected for row {row_id}"
                                )
                                valid_row = False
                                continue
                        # Validate choices for fields with choices (e.g., team_role, opportunity_access_level)
                        model_field = self.condition_model._meta.get_field(field_name)
                        if hasattr(model_field, "choices") and model_field.choices:
                            choice_values = [
                                choice[0] for choice in model_field.choices
                            ]
                            if value not in choice_values:
                                self.add_error(
                                    None,
                                    f"Invalid {field_name} selected for row {row_id}",
                                )
                                valid_row = False
                                continue
                        row_data[field_name] = value
            if row_data and valid_row:
                condition_rows.append(row_data)

        return condition_rows

    def clean(self):
        """Process multiple condition rows from form data"""
        cleaned_data = super().clean()

        condition_rows = self._extract_condition_rows()

        if not condition_rows:
            raise forms.ValidationError(
                _("At least one valid condition row must be provided.")
            )

        cleaned_data["condition_rows"] = condition_rows

        return cleaned_data

    class Meta:
        """Meta options for OpportunityTeamForm."""

        model = OpportunityTeam
        fields = ["team_name", "description"]


class OpportunityTeamMemberForm(HorillaModelForm):
    """Form for managing Opportunity Team Members."""

    def __init__(self, *args, **kwargs):
        self.row_id = kwargs.pop("row_id", "0")
        super().__init__(*args, **kwargs)

        for field_name in ["user", "team_role", "opportunity_access_level"]:
            if field_name in self.fields:
                self.fields[field_name].required = False

    class Meta:
        """Meta options for OpportunityTeamMemberForm."""

        model = DefaultOpportunityMember
        fields = ["team", "user", "team_role", "opportunity_access_level"]


class OpportunityMemberForm(HorillaModelForm):
    """Form for managing Opportunity Team Members."""

    def __init__(self, *args, **kwargs):
        self.row_id = kwargs.pop("row_id", "0")
        super().__init__(*args, **kwargs)

        for field_name in ["user", "team_role", "opportunity_access"]:
            if field_name in self.fields:
                self.fields[field_name].required = False

    class Meta:
        """Meta options for OpportunityTeamMemberForm."""

        model = OpportunityTeamMember
        fields = ["opportunity", "user", "team_role", "opportunity_access"]


class AddDefaultTeamForm(forms.Form):
    """Form to select an OpportunityTeam to add its default members"""

    team = forms.ModelChoiceField(
        queryset=OpportunityTeam.objects.none(),
        label=_("Select Team"),
        help_text=_("Select a team to add all its default members to this opportunity"),
        widget=forms.Select(
            {
                "class": "js-example-basic-single headselect w-full",
                "id": "id_team",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        # Remove HorillaSingleFormView specific kwargs
        kwargs.pop("full_width_fields", None)
        kwargs.pop("dynamic_create_fields", None)
        kwargs.pop("condition_fields", None)
        kwargs.pop("condition_model", None)
        kwargs.pop("condition_field_choices", None)
        kwargs.pop("hidden_fields", None)
        kwargs.pop("row_id", None)
        self.request = kwargs.pop("request", None)
        self.opportunity = kwargs.pop("opportunity", None)
        super().__init__(*args, **kwargs)
        self.fields["team"].queryset = OpportunityTeam.objects.filter(
            owner=self.request.user
        )
