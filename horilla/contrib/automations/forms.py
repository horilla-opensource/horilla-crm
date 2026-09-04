"""
Forms for the automations app
"""

# Third-party imports (Django)
from django import forms

from horilla.apps import apps
from horilla.auth.models import User
from horilla.contrib.core.models import HorillaContentType
from horilla.contrib.generics.forms import HorillaModelForm
from horilla.contrib.mail.models import HorillaMailConfiguration

# First party imports (Horilla)
from horilla.db import models
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# Local imports
from .models import AutomationCondition, HorillaAutomation

# Schedule fields shown only when trigger is "scheduled"
SCHEDULE_FIELD_NAMES = [
    "schedule_date_field",
    "schedule_offset_amount",
    "schedule_offset_direction",
    "schedule_offset_unit",
    "schedule_run_time",
]


class HorillaAutomationForm(HorillaModelForm):
    """
    Form class for HorillaAutomation model
    """

    # Set HTMX URL for field choices (generic method will use this)
    htmx_field_choices_url = "automations:get_automation_field_choices"

    def __init__(self, *args, **kwargs):
        # Pop custom kwargs not supported by Django's BaseModelForm
        form_url = kwargs.pop("form_url", None)
        htmx_trigger_target = kwargs.pop("htmx_trigger_target", None)

        kwargs["condition_model"] = AutomationCondition
        super().__init__(*args, **kwargs)

        request = kwargs.get("request")
        # Resolve trigger: only show schedule fields when trigger is "scheduled"
        instance = getattr(self, "instance", None)
        initial = kwargs.get("initial", {})
        trigger = None
        # Prefer currently submitted form data (POST / bound form)
        if getattr(self, "is_bound", False) and self.data.get("trigger"):
            trigger = self.data.get("trigger")
        # IMPORTANT: prefer the current value coming from HTMX GET reload,
        # otherwise update form would always stick to the instance's saved trigger.
        if request and request.method == "GET" and request.GET.get("trigger"):
            trigger = request.GET.get("trigger")
        if trigger is None and initial.get("trigger"):
            trigger = initial.get("trigger")
        if trigger is None and instance and getattr(instance, "pk", None):
            trigger = getattr(instance, "trigger", None)

        if trigger != "scheduled":
            for name in SCHEDULE_FIELD_NAMES:
                self.fields.pop(name, None)

        # Update condition_field_choices if model_name changed
        if self.model_name and hasattr(self, "condition_field_choices"):
            if (
                not self.condition_field_choices.get("field")
                or len(self.condition_field_choices.get("field", [])) <= 1
            ):
                self.condition_field_choices["field"] = self._get_model_field_choices(
                    self.model_name
                )

        # Automation-specific: Update mail_to field
        self._update_mail_to_field(self.model_name)

        # Filter mail servers to only show outgoing mail servers
        if "mail_server" in self.fields:
            if request and hasattr(request, "user") and not request.user.is_anonymous:
                company = getattr(request.user, "company", None)
                queryset = HorillaMailConfiguration.objects.filter(
                    mail_channel="outgoing"
                )
                if company:
                    queryset = queryset.filter(company=company)
                self.fields["mail_server"].queryset = queryset
            else:
                self.fields["mail_server"].queryset = (
                    HorillaMailConfiguration.objects.filter(mail_channel="outgoing")
                )

        # Add HTMX attributes to delivery_channel field
        # This field will also trigger when model changes (pure HTMX solution)
        if "delivery_channel" in self.fields:
            automation_id = ""
            if self.instance_obj and self.instance_obj.pk:
                automation_id = str(self.instance_obj.pk)

            # Get the model field ID for the trigger
            model_field_id = "id_model"  # Default ID for model field

            self.fields["delivery_channel"].widget.attrs.update(
                {
                    "hx-get": reverse_lazy("automations:get_template_fields"),
                    "hx-target": "body",
                    "hx-swap": "none",
                    "hx-include": "[name='delivery_channel'],[name='model']",
                    "hx-vals": f'{{"automation_id": "{automation_id}"}}',
                    # Trigger on delivery_channel change, model change, and on load
                    "hx-trigger": f"change, change from:#{model_field_id}, load",
                }
            )

        # Trigger field: reload form when changed so schedule fields show/hide
        if "trigger" in self.fields and form_url and htmx_trigger_target:
            self.fields["trigger"].widget.attrs.update(
                {
                    "hx-get": form_url,
                    "hx-vals": "js:{'trigger': document.getElementById('id_trigger').value}",
                    # include the whole form so previously filled values are preserved on reload
                    "hx-include": "closest form",
                    "hx-trigger": "change",
                    "hx-target": htmx_trigger_target,
                    "hx-swap": "innerHTML",
                }
            )

        # Scheduled automation: set date field choices (Date/DateTime only) — only when visible
        if "schedule_date_field" in self.fields:
            # Model field is a CharField; replace with ChoiceField so choices render
            existing = self.fields["schedule_date_field"]
            choices = self._get_model_date_field_choices(self.model_name)
            initial_value = ""
            if self.instance_obj and getattr(self.instance_obj, "pk", None):
                initial_value = (
                    getattr(self.instance_obj, "schedule_date_field", "") or ""
                )
            elif self.initial.get("schedule_date_field"):
                initial_value = self.initial.get("schedule_date_field") or ""

            self.fields["schedule_date_field"] = forms.ChoiceField(
                choices=choices,
                required=False,
                label=existing.label,
                help_text=existing.help_text,
                initial=initial_value,
                widget=forms.Select(
                    attrs={
                        "class": "js-example-basic-single headselect w-full",
                    }
                ),
            )

        # Make schedule fields not required by default; validation happens in clean()
        for fname in [
            "schedule_offset_amount",
            "schedule_offset_direction",
            "schedule_offset_unit",
            "schedule_run_time",
        ]:
            if fname in self.fields:
                self.fields[fname].required = False

    def _get_model_field_choices(self, model_name):
        """Override to get field choices for automation conditions - exclude reverse relations"""
        field_choices = [("", "---------")]

        if not model_name:
            return field_choices

        try:
            model = None
            for app_config in apps.get_app_configs():
                try:
                    model = apps.get_model(
                        app_label=app_config.label, model_name=model_name.lower()
                    )
                    break
                except (LookupError, ValueError):
                    continue

            if model:
                # Use _meta.fields and _meta.many_to_many to get only forward fields (not reverse relations)
                # This excludes one-to-many and many-to-many reverse relationships
                all_forward_fields = list(model._meta.fields) + list(
                    model._meta.many_to_many
                )

                for field in all_forward_fields:
                    # Skip excluded fields (must match AUTOMATION_CONDITION_EXCLUDED_FIELDS in views)
                    if field.name in [
                        "id",
                        "pk",
                        "created_at",
                        "updated_at",
                        "created_by",
                        "updated_by",
                        "company",
                        "additional_info",
                        "password",
                    ]:
                        continue
                    # Skip non-editable fields (e.g. editable=False on the model)
                    if not getattr(field, "editable", True):
                        continue

                    verbose_name = (
                        getattr(field, "verbose_name", None)
                        or field.name.replace("_", " ").title()
                    )
                    field_choices.append((field.name, verbose_name))
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                "Error fetching model %s: %s", model_name, str(e), exc_info=True
            )

        return field_choices

    def _get_model_date_field_choices(self, model_name):
        """Return only date/datetime field choices for scheduled trigger."""
        field_choices = [("", "---------")]
        if not model_name:
            return field_choices
        try:
            model = None
            for app_config in apps.get_app_configs():
                try:
                    model = apps.get_model(
                        app_label=app_config.label, model_name=model_name.lower()
                    )
                    break
                except (LookupError, ValueError):
                    continue
            if model:
                for field in model._meta.fields:
                    # Only include DateField or DateTimeField
                    if isinstance(field, (models.DateField, models.DateTimeField)):
                        verbose_name = (
                            getattr(field, "verbose_name", None)
                            or field.name.replace("_", " ").title()
                        )
                        field_choices.append((field.name, verbose_name))
        except Exception:
            pass
        return field_choices

    def _get_user_foreignkey_fields(self, model_name):
        """Get all ForeignKey fields that point to User model"""
        field_choices = []

        if not model_name:
            return field_choices

        try:
            # Get the model class from the app registry
            model_class = None
            for app_config in apps.get_app_configs():
                try:
                    model_class = apps.get_model(app_config.label, model_name.lower())
                    break
                except (LookupError, ValueError):
                    continue

            if model_class:
                for field in model_class._meta.get_fields():
                    # Skip reverse relations (they don't have a 'name' attribute)
                    if not hasattr(field, "name"):
                        continue

                    # Check if it's a ForeignKey to User
                    if isinstance(field, models.ForeignKey):
                        try:
                            # Get the related model
                            related_model = field.related_model
                            # Check if it's User or a subclass of User
                            is_user_model = False
                            if related_model:
                                if related_model == User:
                                    is_user_model = True
                                elif hasattr(related_model, "__bases__"):
                                    try:
                                        is_user_model = issubclass(related_model, User)
                                    except (TypeError, AttributeError):
                                        pass
                                # Check using HorillaContentType (most reliable method)
                                if not is_user_model:
                                    try:
                                        user_content_type = (
                                            HorillaContentType.objects.get_for_model(
                                                User
                                            )
                                        )
                                        field_content_type = (
                                            HorillaContentType.objects.get_for_model(
                                                related_model
                                            )
                                        )
                                        if user_content_type == field_content_type:
                                            is_user_model = True
                                    except Exception:
                                        pass
                                # Also check the model name and AUTH_USER_MODEL as fallback
                                if not is_user_model:
                                    from django.conf import settings

                                    user_model_names = ["user", "horillauser"]
                                    if hasattr(settings, "AUTH_USER_MODEL"):
                                        user_model_names.append(
                                            settings.AUTH_USER_MODEL.split(".")[
                                                -1
                                            ].lower()
                                        )
                                    if (
                                        related_model.__name__.lower()
                                        in user_model_names
                                    ):
                                        is_user_model = True

                            if is_user_model:
                                verbose_name = (
                                    getattr(field, "verbose_name", None)
                                    or field.name.replace("_", " ").title()
                                )
                                # Return as 'instance.field_name' format for consistency
                                field_choices.append(
                                    (f"instance.{field.name}", verbose_name)
                                )
                        except Exception:
                            continue

                    # Also check for email fields (EmailField or CharField with 'email' in name)
                    elif isinstance(field, (models.EmailField, models.CharField)):
                        if "email" in field.name.lower():
                            verbose_name = (
                                getattr(field, "verbose_name", None)
                                or field.name.replace("_", " ").title()
                            )
                            field_choices.append(
                                (f"instance.{field.name}", verbose_name)
                            )

                # Also add 'self' option
                field_choices.insert(0, ("self", _("Self (User who triggered)")))
        except Exception:
            pass

        return field_choices

    def _update_mail_to_field(self, model_name):
        """Update mail_to field to show User ForeignKey fields from selected model"""
        if "mail_to" in self.fields:
            # Get User ForeignKey fields for the selected model
            user_fields = self._get_user_foreignkey_fields(model_name)

            # Convert current value to list if it exists
            initial_value = []
            if self.instance_obj and self.instance_obj.pk and self.instance_obj.mail_to:
                # Split comma-separated values
                initial_value = [
                    v.strip() for v in self.instance_obj.mail_to.split(",") if v.strip()
                ]
            elif self.initial.get("mail_to"):
                initial_value = [
                    v.strip()
                    for v in str(self.initial.get("mail_to")).split(",")
                    if v.strip()
                ]

            # Create a custom field that accepts any values without validation
            # We'll inherit from Field directly to bypass MultipleChoiceField validation
            class FlexibleMultipleChoiceField(forms.Field):
                """
                Custom field that accepts multiple values without strict choice validation.
                Used for mail_to field to allow dynamic field references.
                """

                widget = forms.SelectMultiple

                def __init__(self, choices=(), *args, **kwargs):
                    self.choices = choices
                    super().__init__(*args, **kwargs)
                    # Set choices on widget
                    if hasattr(self.widget, "choices"):
                        self.widget.choices = choices

                def to_python(self, value):
                    """Convert the value to a Python list"""
                    if value in self.empty_values:
                        return []
                    if isinstance(value, (list, tuple)):
                        return [str(v) for v in value if v]
                    return [str(value)] if value else []

                def validate(self, value):
                    """Only validate required, not choices"""
                    if self.required and not value:
                        raise forms.ValidationError(
                            self.error_messages["required"], code="required"
                        )

                def clean(self, value):
                    """Completely bypass choice validation - accept any values"""
                    value = self.to_python(value)
                    self.validate(value)
                    return value

                def prepare_value(self, value):
                    """Prepare value for display in widget"""
                    if value is None:
                        return []
                    if isinstance(value, str):
                        # Split comma-separated string
                        return [v.strip() for v in value.split(",") if v.strip()]
                    if isinstance(value, (list, tuple)):
                        return [str(v) for v in value if v]
                    return []

            # Create the field
            self.fields["mail_to"] = FlexibleMultipleChoiceField(
                choices=user_fields,
                required=False,
                label=self.fields["mail_to"].label,
                help_text=self.fields["mail_to"].help_text,
                widget=forms.SelectMultiple(
                    attrs={
                        "class": "js-example-basic-multiple headselect w-full",
                        "data-placeholder": _("Select user fields"),
                        "multiple": "multiple",
                    }
                ),
                initial=initial_value,
            )

    def clean_mail_to(self):
        """Convert list to comma-separated string"""
        # Get the value from cleaned_data (after field validation)
        mail_to = self.cleaned_data.get("mail_to")

        # If field wasn't in form data or is None, return empty string
        if mail_to is None:
            return ""

        # If it's already a string, return as is
        if isinstance(mail_to, str):
            return mail_to

        # If it's a list, convert to comma-separated string
        if isinstance(mail_to, list):
            # Filter out empty values and join
            valid_selections = [str(v).strip() for v in mail_to if v and str(v).strip()]
            if valid_selections:
                return ", ".join(valid_selections)
            return ""

        return str(mail_to) if mail_to else ""

    class Meta:
        """Meta class for HorillaAutomationForm"""

        model = HorillaAutomation
        fields = [
            "title",
            "model",
            "mail_to",
            "also_sent_to",
            "trigger",
            "schedule_date_field",
            "schedule_offset_amount",
            "schedule_offset_direction",
            "schedule_offset_unit",
            "schedule_run_time",
            "delivery_channel",
            "mail_template",
            "notification_template",
            "mail_server",
        ]

    def clean(self):
        """Conditional validation for scheduled trigger."""
        cleaned = super().clean()
        trigger = cleaned.get("trigger")
        if trigger == "scheduled":
            errors = {}
            if not cleaned.get("schedule_date_field"):
                errors["schedule_date_field"] = _("Required for scheduled automations.")
            if cleaned.get("schedule_offset_amount") is None:
                errors["schedule_offset_amount"] = _(
                    "Required for scheduled automations."
                )
            if not cleaned.get("schedule_offset_direction"):
                errors["schedule_offset_direction"] = _(
                    "Required for scheduled automations."
                )
            if not cleaned.get("schedule_offset_unit"):
                errors["schedule_offset_unit"] = _(
                    "Required for scheduled automations."
                )
            if errors:
                raise forms.ValidationError(errors)
        return cleaned

    def save(self, commit=True):
        """Clear schedule fields when trigger is not scheduled."""
        instance = super().save(commit=False)
        if self.cleaned_data.get("trigger") != "scheduled":
            instance.schedule_date_field = ""
            instance.schedule_offset_amount = None
            instance.schedule_offset_direction = ""
            instance.schedule_offset_unit = ""
            instance.schedule_run_time = None
        if commit:
            instance.save()
            self.save_m2m()
        return instance
