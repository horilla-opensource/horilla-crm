import logging
from datetime import date, datetime
from decimal import Decimal

from django import forms
from django.db import models
from django.db.models.fields import Field
from django.db.models.fields.files import ImageFieldFile
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_countries.fields import Country, CountryField
from django_summernote.widgets import SummernoteWidget

from horilla_core.models import HorillaAttachment, KanbanGroupBy, ListColumnVisibility
from horilla_utils.middlewares import _thread_local

logger = logging.getLogger(__name__)
# Define your horilla_generics forms here


class KanbanGroupByForm(forms.ModelForm):
    class Meta:
        model = KanbanGroupBy
        fields = ["model_name", "field_name", "app_label"]
        widgets = {
            "model_name": forms.HiddenInput(),
            "app_label": forms.HiddenInput(),
            "field_name": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        self.request = getattr(_thread_local, "request")
        exclude_fields = kwargs.pop("exclude_fields", [])
        include_fields = kwargs.pop("include_fields", [])
        super().__init__(*args, **kwargs)

        # Try to resolve model/app from data, then initial, then instance
        model_name = (
            self.data.get("model_name")
            or self.initial.get("model_name")
            or getattr(self.instance, "model_name", None)
        )
        app_label = (
            self.data.get("app_label")
            or self.initial.get("app_label")
            or getattr(self.instance, "app_label", None)
        )

        if model_name and app_label:
            temp_instance = KanbanGroupBy(model_name=model_name, app_label=app_label)
            self.fields["field_name"].choices = temp_instance.get_model_groupby_fields(
                exclude_fields=exclude_fields,
                include_fields=include_fields,
            )
        else:
            self.fields["field_name"].choices = []

    def clean(self):
        cleaned_data = super().clean()
        model_name = cleaned_data.get("model_name")
        app_label = cleaned_data.get("app_label")
        field_name = cleaned_data.get("field_name")

        # Only validate if field_name is filled
        if model_name and field_name:
            temp_instance = KanbanGroupBy(
                model_name=model_name,
                field_name=field_name,
                app_label=app_label,
                user=self.request.user,
            )
            try:
                temp_instance.clean()
            except Exception as e:
                self.add_error("field_name", e)

        return cleaned_data

    def validate_unique(self):
        pass


class ColumnSelectionForm(forms.Form):
    visible_fields = forms.MultipleChoiceField(
        required=False, widget=forms.MultipleHiddenInput
    )

    def __init__(self, *args, **kwargs):
        model = kwargs.pop("model", None)
        app_label = kwargs.pop("app_label", None)
        path_context = kwargs.pop("path_context", None)
        user = kwargs.pop("user", None)
        model_name = kwargs.pop("model_name", None)
        url_name = kwargs.pop("url_name", None)
        super().__init__(*args, **kwargs)

        if model:
            excluded_fields = ["history"]
            # Get model fields and methods as [verbose_name, field_name]
            instance = model()
            model_fields = [
                [
                    force_str(f.verbose_name or f.name.title()),
                    (
                        f.name
                        if not getattr(f, "choices", None)
                        else f"get_{f.name}_display"
                    ),
                ]
                for f in model._meta.get_fields()
                if isinstance(f, Field) and f.name not in excluded_fields
            ]

            # Use columns property if available, otherwise use model_fields
            all_fields = (
                getattr(instance, "columns", model_fields)
                if hasattr(instance, "columns")
                else model_fields
            )
            field_name_to_verbose = {f[1]: f[0] for f in all_fields}
            unique_field_names = {f[1] for f in all_fields}

            visible_field_lists = []
            removed_custom_field_lists = []
            if app_label and model_name and path_context and user:
                visibility = ListColumnVisibility.all_objects.filter(
                    user=user,
                    app_label=app_label,
                    model_name=model_name,
                    context=path_context,
                ).first()
                if visibility:
                    visible_field_lists = visibility.visible_fields
                    removed_custom_field_lists = visibility.removed_custom_fields

            choices = [(f[1], f[0]) for f in all_fields]

            for visible_field in visible_field_lists:
                if (
                    len(visible_field) >= 2
                    and visible_field[1] not in unique_field_names
                ):
                    choices.append((visible_field[1], visible_field[0]))
                    unique_field_names.add(visible_field[1])
                    field_name_to_verbose[visible_field[1]] = visible_field[0]

            for custom_field in removed_custom_field_lists:
                if len(custom_field) >= 2 and custom_field[1] not in unique_field_names:
                    choices.append((custom_field[1], custom_field[0]))
                    unique_field_names.add(custom_field[1])
                    field_name_to_verbose[custom_field[1]] = custom_field[0]

            choices.sort(key=lambda x: x[1].lower())
            self.fields["visible_fields"].choices = choices

            if self.data:
                field_names = (
                    self.data.getlist("visible_fields")
                    if hasattr(self.data, "getlist")
                    else self.data.get("visible_fields", [])
                )
                if not isinstance(field_names, list):
                    field_names = [field_names] if field_names else []
                valid_field_names = [f for f in field_names if f in unique_field_names]
                if valid_field_names:
                    self.data = self.data.copy() if hasattr(self.data, "copy") else {}
                    if hasattr(self.data, "setlist"):
                        self.data.setlist("visible_fields", valid_field_names)
                    else:
                        self.data["visible_fields"] = valid_field_names


class HorillaMultiStepForm(forms.ModelForm):
    step_fields = {}

    def __init__(self, *args, **kwargs):
        self.current_step = int(kwargs.pop("step", 1))
        self.form_data = kwargs.pop("form_data", {}) or {}
        self.full_width_fields = kwargs.pop("full_width_fields", [])
        self.dynamic_create_fields = kwargs.pop("dynamic_create_fields", [])
        self.request = kwargs.pop("request", None)

        self.stored_files = {}

        super().__init__(*args, **kwargs)

        if self.request and self.request.FILES:
            self.files = self.request.FILES

        if hasattr(self, "files") and self.files:
            for field_name, file_obj in self.files.items():
                self.stored_files[field_name] = file_obj

        if self.instance and self.instance.pk:
            for field_name in self.fields:
                if field_name not in self.form_data or self.form_data[field_name] in [
                    None,
                    "",
                    [],
                ]:
                    field_value = getattr(self.instance, field_name, None)
                    if field_value is not None:
                        if hasattr(field_value, "pk"):
                            self.form_data[field_name] = field_value.pk
                        elif hasattr(field_value, "all"):
                            self.form_data[field_name] = [
                                obj.pk for obj in field_value.all()
                            ]
                        elif isinstance(field_value, datetime):
                            self.form_data[field_name] = field_value.strftime(
                                "%Y-%m-%dT%H:%M"
                            )
                        elif isinstance(field_value, date):
                            self.form_data[field_name] = field_value.strftime(
                                "%Y-%m-%d"
                            )
                        elif isinstance(field_value, Decimal):
                            self.form_data[field_name] = str(field_value)
                        elif isinstance(field_value, bool):
                            self.form_data[field_name] = field_value
                        elif isinstance(field_value, Country):
                            self.form_data[field_name] = str(field_value)
                        elif isinstance(field_value, (ImageFieldFile)):
                            # For existing files, we need to preserve the file info
                            if field_value.name:
                                self.form_data[field_name] = field_value.name
                                # Only set filename if not already set from session
                                if f"{field_name}_filename" not in self.form_data:
                                    self.form_data[f"{field_name}_filename"] = (
                                        field_value.name.split("/")[-1]
                                    )
                        else:
                            self.form_data[field_name] = field_value

        if self.form_data:
            # Clean up form data to ensure proper formatting for date/datetime fields
            cleaned_form_data = {}
            for field_name, field_value in self.form_data.items():
                if field_name in self.fields:
                    try:
                        model_field = self._meta.model._meta.get_field(field_name)
                        if isinstance(model_field, models.BooleanField):
                            # Convert string values to boolean
                            if isinstance(field_value, str):
                                cleaned_form_data[field_name] = field_value.lower() in (
                                    "true",
                                    "on",
                                    "1",
                                )
                            else:
                                cleaned_form_data[field_name] = bool(field_value)
                        elif isinstance(
                            model_field, models.DateField
                        ) and not isinstance(model_field, models.DateTimeField):
                            if isinstance(field_value, str) and "T" in field_value:
                                cleaned_form_data[field_name] = field_value.split("T")[
                                    0
                                ]
                            elif isinstance(field_value, (datetime, date)):
                                cleaned_form_data[field_name] = field_value.strftime(
                                    "%Y-%m-%d"
                                )
                            else:
                                cleaned_form_data[field_name] = field_value
                        elif isinstance(model_field, models.DateTimeField):
                            if isinstance(field_value, str) and "T" not in field_value:
                                cleaned_form_data[field_name] = f"{field_value}T00:00"
                            elif isinstance(field_value, datetime):
                                cleaned_form_data[field_name] = field_value.strftime(
                                    "%Y-%m-%dT%H:%M"
                                )
                            elif isinstance(field_value, date):
                                cleaned_form_data[field_name] = (
                                    f"{field_value.strftime('%Y-%m-%d')}T00:00"
                                )
                            else:
                                cleaned_form_data[field_name] = field_value
                        elif isinstance(model_field, CountryField):
                            cleaned_form_data[field_name] = str(field_value)
                        else:
                            cleaned_form_data[field_name] = field_value
                    except models.FieldDoesNotExist:
                        cleaned_form_data[field_name] = field_value
                else:
                    cleaned_form_data[field_name] = field_value

            self.data = cleaned_form_data

        self._configure_field_widgets()

        # Handle step-specific field visibility
        if self.current_step <= len(self.step_fields):
            current_fields = self.step_fields.get(self.current_step, [])
            for field_name in self.fields:
                if field_name not in [
                    f for step_fields in self.step_fields.values() for f in step_fields
                ]:
                    self.fields[field_name].required = False
                    continue
                if field_name not in current_fields:
                    self.fields[field_name].required = False
                    self.fields[field_name].widget = forms.HiddenInput()
                else:
                    try:
                        original_field = self._meta.model._meta.get_field(field_name)
                        if hasattr(original_field, "blank"):
                            # For file fields, only make them not required if they have existing content
                            if isinstance(
                                original_field, (models.FileField, models.ImageField)
                            ):
                                # Check if we have existing file, new file, or stored file
                                has_existing_file = (
                                    self.instance
                                    and self.instance.pk
                                    and getattr(self.instance, field_name, None)
                                )
                                has_new_file = field_name in self.stored_files
                                has_stored_filename = (
                                    f"{field_name}_filename" in self.form_data
                                )

                                # Only make not required if we actually have a file AND field allows blank
                                if (
                                    has_existing_file
                                    or has_new_file
                                    or has_stored_filename
                                ) and original_field.blank:
                                    self.fields[field_name].required = False
                                else:
                                    # Keep original required setting
                                    self.fields[field_name].required = (
                                        not original_field.blank
                                    )
                            else:
                                self.fields[field_name].required = (
                                    not original_field.blank
                                )
                    except models.FieldDoesNotExist:
                        pass

    def _configure_field_widgets(self):
        """Configure widgets for all form fields with pagination support"""
        for field_name, field in self.fields.items():
            widget_attrs = {
                "class": "text-color-600 p-2 placeholder:text-xs  w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
            }

            if field_name in self.full_width_fields:
                widget_attrs["fullwidth"] = True

            # Get the model field to determine its type
            try:
                model_field = self._meta.model._meta.get_field(field_name)
            except models.FieldDoesNotExist:
                model_field = None

            if model_field:
                if isinstance(model_field, (models.ImageField, models.FileField)):
                    # Check if we have existing file or new file
                    has_existing_file = (
                        self.instance
                        and self.instance.pk
                        and getattr(self.instance, field_name, None)
                    )
                    has_new_file = field_name in self.stored_files

                    # Only make field not required if we have an existing/new file AND field allows blank
                    # AND we're not in the current step OR we have a file
                    current_fields = self.step_fields.get(self.current_step, [])
                    if field_name not in current_fields:
                        # Not in current step, make not required
                        field.required = False
                    elif (has_existing_file or has_new_file) and model_field.blank:
                        # In current step but has file and field allows blank
                        field.required = False
                    else:
                        # In current step, respect original field requirements
                        field.required = not model_field.blank

                    if isinstance(model_field, models.ImageField):
                        field.widget.attrs["accept"] = "image/*"

                    field.widget.attrs["formnovalidate"] = "formnovalidate"

                    if not field.widget.attrs.get("placeholder"):
                        field_label = (
                            field.label or field_name.replace("_", " ").title()
                        )
                        widget_attrs["placeholder"] = f"Upload {field_label}"

                elif isinstance(model_field, models.DateField) and not isinstance(
                    model_field, models.DateTimeField
                ):
                    field.widget = forms.DateInput(
                        attrs={"type": "date"}, format="%Y-%m-%d"
                    )
                    field.input_formats = ["%Y-%m-%d"]

                elif isinstance(model_field, models.DateTimeField):
                    field.widget = forms.DateTimeInput(
                        attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
                    )
                    field.input_formats = [
                        "%Y-%m-%dT%H:%M",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d %H:%M",
                    ]
                elif isinstance(model_field, models.TimeField):
                    if not isinstance(field.widget, forms.HiddenInput):
                        field.widget = forms.TimeInput(
                            attrs={
                                "type": "time",
                                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                            }
                        )

                elif isinstance(model_field, models.ManyToManyField):
                    self._configure_many_to_many_field(field, field_name, model_field)

                elif isinstance(model_field, models.ForeignKey):
                    self._configure_foreign_key_field(field, field_name, model_field)

                elif isinstance(model_field, models.TextField):
                    field.widget = forms.Textarea()
                    if not field.widget.attrs.get("placeholder"):
                        field_label = (
                            field.label or field_name.replace("_", " ").title()
                        )
                        widget_attrs["placeholder"] = f"Enter {field_label}"

                elif isinstance(model_field, models.BooleanField):
                    field.widget = forms.CheckboxInput()

                else:
                    # For all other field types, use generic placeholder
                    if not field.widget.attrs.get("placeholder"):
                        field_label = (
                            field.label or field_name.replace("_", " ").title()
                        )
                        widget_attrs["placeholder"] = f"Enter {field_label}"
            else:
                # If no model field found, use generic placeholder
                if not field.widget.attrs.get("placeholder"):
                    field_label = field.label or field_name.replace("_", " ").title()
                    widget_attrs["placeholder"] = f"Enter {field_label}"

            # Apply widget-specific classes and attributes
            if isinstance(field.widget, forms.Select):
                widget_attrs["class"] += " js-example-basic-single headselect"
            elif isinstance(field.widget, forms.Textarea):
                widget_attrs["class"] += " w-full"
            elif isinstance(field.widget, forms.CheckboxInput):
                widget_attrs["class"] = "sr-only peer"
            elif isinstance(field.widget, (forms.DateInput, forms.DateTimeInput)):
                # Don't add placeholder to date/datetime inputs
                if "placeholder" in widget_attrs:
                    del widget_attrs["placeholder"]

            if not hasattr(field.widget, "_pagination_configured"):
                field.widget.attrs.update(widget_attrs)

    def _configure_many_to_many_field(self, field, field_name, model_field):
        """Configure ManyToManyField with pagination support"""
        related_model = model_field.related_model
        app_label = related_model._meta.app_label
        model_name = related_model._meta.model_name

        initial_value = []
        if field_name in self.form_data:
            form_data_value = self.form_data[field_name]
            if isinstance(form_data_value, list):
                initial_value = form_data_value
            elif form_data_value:
                initial_value = [form_data_value]
        elif self.instance and self.instance.pk:
            initial_value = list(
                getattr(self.instance, field_name).values_list("pk", flat=True)
            )
        elif field_name in self.initial:
            initial_data = self.initial[field_name]
            if isinstance(initial_data, list):
                initial_value = []
                for item in initial_data:
                    if hasattr(item, "pk"):
                        initial_value.append(item.pk)
                    else:
                        initial_value.append(item)
            else:
                if hasattr(initial_data, "pk"):
                    initial_value = [initial_data.pk]
                else:
                    initial_value = [initial_data]

        # Get the selected objects for initial display
        initial_choices = []
        if initial_value:
            try:
                selected_objects = related_model.objects.filter(pk__in=initial_value)
                initial_choices = [(obj.pk, str(obj)) for obj in selected_objects]
            except Exception as e:
                logger.error(
                    f"Error loading initial choices for {field_name}: {str(e)}"
                )

        field.widget = forms.SelectMultiple(
            choices=initial_choices,
            attrs={
                "class": "select2-pagination w-full text-sm",
                "data-url": reverse_lazy(
                    f"horilla_generics:model_select2",
                    kwargs={"app_label": app_label, "model_name": model_name},
                ),
                "data-placeholder": f"Select {model_field.verbose_name.title()}",
                "multiple": "multiple",
                "data-initial": (
                    ",".join(map(str, initial_value)) if initial_value else ""
                ),
                "data-field-name": field_name,
                "id": f"id_{field_name}",
                "data-form-class": f"{self.__module__}.{self.__class__.__name__}",
            },
        )
        field.widget._pagination_configured = True

    def _configure_foreign_key_field(self, field, field_name, model_field):
        """Configure ForeignKey field with pagination support"""
        related_model = model_field.related_model
        app_label = related_model._meta.app_label
        model_name = related_model._meta.model_name

        # Get initial value properly
        initial_value = None
        if self.instance and self.instance.pk:
            related_obj = getattr(self.instance, field_name, None)
            initial_value = related_obj.pk if related_obj else None
        elif field_name in self.initial:
            initial_data = self.initial[field_name]
            if hasattr(initial_data, "pk"):
                initial_value = initial_data.pk
            else:
                initial_value = initial_data
        elif field_name in self.form_data:
            initial_value = self.form_data[field_name]

        # Get the selected object for initial display
        initial_choices = []
        if initial_value:
            try:
                selected_object = related_model.objects.get(pk=initial_value)
                initial_choices = [(selected_object.pk, str(selected_object))]
            except related_model.DoesNotExist:
                logger.error(
                    f"Initial object not found for {field_name}: {initial_value}"
                )
            except Exception as e:
                logger.error(f"Error loading initial choice for {field_name}: {str(e)}")

        field.widget = forms.Select(
            choices=[("", "---------")] + initial_choices,  # Set initial choices
            attrs={
                "class": "select2-pagination w-full",
                "data-url": reverse_lazy(
                    f"horilla_generics:model_select2",
                    kwargs={"app_label": app_label, "model_name": model_name},
                ),
                "data-placeholder": f"Select {model_field.verbose_name.title()}",
                "data-initial": str(initial_value) if initial_value else "",
                "data-field-name": field_name,  # Add unique identifier
                "id": f"id_{field_name}",
                "data-form-class": f"{self.__module__}.{self.__class__.__name__}",
            },
        )
        field.widget._pagination_configured = True

    def clean(self):
        cleaned_data = super().clean()

        current_fields = self.step_fields.get(self.current_step, [])

        errors_to_remove = []
        for field_name in list(self.errors.keys()):
            if field_name not in current_fields:
                errors_to_remove.append(field_name)

        for field_name in errors_to_remove:
            if field_name in self.errors:
                del self.errors[field_name]

        # For current step fields, handle file field validation properly
        for field_name in current_fields:
            if field_name in self.fields:
                try:
                    model_field = self._meta.model._meta.get_field(field_name)
                    if isinstance(model_field, (models.FileField, models.ImageField)):
                        has_stored_file = field_name in self.stored_files
                        has_existing_file = (
                            self.instance
                            and self.instance.pk
                            and getattr(self.instance, field_name, None)
                        )
                        has_form_data_file = (
                            field_name + "_filename" in self.form_data
                            or field_name + "_new_file" in self.form_data
                        )

                        # If field is required and no file exists, ensure error is present
                        if not model_field.blank and not (
                            has_stored_file or has_existing_file or has_form_data_file
                        ):
                            # Add required error if not already present
                            if field_name not in self.errors:
                                self.add_error(field_name, "This field is required.")
                        elif (
                            model_field.blank
                            or has_stored_file
                            or has_existing_file
                            or has_form_data_file
                        ):
                            # Remove error if field allows blank or has file
                            if field_name in self.errors:
                                # Only remove required errors, keep format/other validation errors
                                error_messages = self.errors[field_name].as_data()
                                non_required_errors = [
                                    error
                                    for error in error_messages
                                    if error.code != "required"
                                ]
                                if non_required_errors:
                                    # Keep non-required errors
                                    self.errors[field_name] = forms.ValidationError(
                                        non_required_errors
                                    )
                                else:
                                    # Remove all errors if only required errors
                                    del self.errors[field_name]
                except models.FieldDoesNotExist:
                    pass

        return cleaned_data


class SaveFilterListForm(forms.Form):
    list_name = forms.CharField(
        max_length=100,
        required=True,
        label="List View Name",
        widget=forms.TextInput(
            attrs={
                "class": "text-color-600 p-2 placeholder:text-xs  w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": "Specify the list view name",
            }
        ),
    )
    model_name = forms.CharField(
        max_length=100, required=True, widget=forms.HiddenInput()
    )
    main_url = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        list_name = cleaned_data.get("list_name")
        if not list_name or not list_name.strip():
            self.add_error("list_name", "List name cannot be empty.")
        return cleaned_data


class PasswordInputWithEye(forms.PasswordInput):
    def __init__(self, attrs=None):
        default_attrs = {
            "class": "text-color-600 p-2 placeholder:text-xs font-normal w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm transition duration-300 focus:border-primary-600 pr-10",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        password_input = super().render(name, value, attrs, renderer)

        eye_toggle = f"""
        <div class="relative">
            {password_input}
            <button type="button"
                    class="absolute inset-y-0 right-0 pr-3 flex items-center"
                    onclick="togglePassword('{attrs.get('id', name)}')">
                <img id="eye-icon-{attrs.get('id', name)}"
                     src="/static/assets/icons/eye-hide.svg"
                     alt="Toggle Password"
                     class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-pointer" />
            </button>
        </div>
        <script>
        function togglePassword(fieldId) {{
            const passwordField = document.getElementById(fieldId);
            const eyeIcon = document.getElementById('eye-icon-' + fieldId);

            if (passwordField.type === 'password') {{
                passwordField.type = 'text';
                eyeIcon.src = '/static/assets/icons/eye.svg';
            }} else {{
                passwordField.type = 'password';
                eyeIcon.src = '/static/assets/icons/eye-hide.svg';
            }}
        }}
        </script>
        """

        return mark_safe(eye_toggle)


class HorillaModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.full_width_fields = kwargs.pop("full_width_fields", [])
        self.dynamic_create_fields = kwargs.pop("dynamic_create_fields", [])
        self.hidden_fields = kwargs.pop("hidden_fields", [])
        self.condition_fields = kwargs.pop("condition_fields", [])
        self.condition_model = kwargs.pop("condition_model", None)
        self.condition_field_choices = kwargs.pop("condition_field_choices", {})
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            for field_name, field in self.fields.items():
                if isinstance(field, (forms.FileField, forms.ImageField)):
                    if self.data and self.data.get(f"id_{field_name}_clear") == "true":
                        self.initial[field_name] = None
                        field.widget.attrs["data_cleared"] = "true"
                    elif self.files and field_name in self.files:
                        uploaded_file = self.files[field_name]
                        field.widget.attrs["data_uploaded_filename"] = (
                            uploaded_file.name
                        )
                        field.widget.attrs["data_cleared"] = "false"
                    else:
                        existing_file = getattr(self.instance, field_name, None)
                        if existing_file:
                            self.initial[field_name] = existing_file
                            field.widget.attrs["data_existing_filename"] = (
                                existing_file.name
                            )
                            field.widget.attrs["data_cleared"] = "false"

        if self.request and self.request.method == "POST" and self.request.FILES:
            for field_name in self.request.FILES:
                if field_name in self.fields:
                    if not self.initial.get(field_name):
                        self.initial[field_name] = self.request.FILES[field_name].name
                    field = self.fields[field_name]
                    uploaded_file = self.request.FILES[field_name]
                    field.widget.attrs["data_uploaded_filename"] = uploaded_file.name
                    field.widget.attrs["data_cleared"] = "false"

        if self.condition_model and self.condition_fields:
            self._add_condition_fields()

        for field_name, field in self.fields.items():
            if getattr(field, "is_custom_field", False):
                continue
            if field_name in self.hidden_fields or isinstance(
                field.widget, forms.HiddenInput
            ):
                field.widget = forms.HiddenInput()
                field.widget.attrs.update({"class": "hidden-input"})
                continue

            existing_attrs = getattr(field.widget, "attrs", {}).copy()

            # Apply default styling for non-checkbox fields
            if not isinstance(field.widget, forms.CheckboxInput):
                existing_placeholder = existing_attrs.get("placeholder", "")
                default_placeholder = (
                    f"Enter {field.label}"
                    if not isinstance(field.widget, forms.Select)
                    else ""
                )

                field.widget.attrs.update(
                    {
                        "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                        "placeholder": existing_placeholder or default_placeholder,
                    }
                )

            try:
                # Try to get the field from the main model or condition model
                model_field = None
                model = self._meta.model
                try:
                    model_field = model._meta.get_field(field_name)
                except:
                    if self.condition_model and field_name in self.condition_fields:
                        try:
                            model_field = self.condition_model._meta.get_field(
                                field_name
                            )
                        except:
                            pass

                if model_field:
                    if isinstance(model_field, models.DateTimeField):
                        if not isinstance(field.widget, forms.HiddenInput):
                            field.widget = forms.DateTimeInput(
                                attrs={
                                    "type": "datetime-local",
                                    "class": (
                                        "text-color-600 p-2 placeholder:text-xs w-full "
                                        "border border-dark-50 rounded-md mt-1 "
                                        "focus-visible:outline-0 placeholder:text-dark-100 "
                                        "text-sm [transition:.3s] focus:border-primary-600"
                                    ),
                                    **existing_attrs,
                                },
                                format="%Y-%m-%dT%H:%M",
                            )
                            field.input_formats = ["%Y-%m-%dT%H:%M"]

                    elif isinstance(model_field, models.DateField):
                        if not isinstance(field.widget, forms.HiddenInput):
                            field.widget = forms.DateInput(
                                attrs={
                                    "type": "date",
                                    "class": "text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                                    **existing_attrs,
                                }
                            )

                    elif isinstance(model_field, models.TimeField):
                        if not isinstance(field.widget, forms.HiddenInput):
                            field.widget = forms.TimeInput(
                                attrs={
                                    "type": "time",
                                    "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm transition duration-300 focus:border-primary-600",
                                    "style": f'background-image: url("{static("assets/icons/clock_icon.svg")}"); background-repeat: no-repeat; background-position: right 12px center; background-size: 18px;',
                                    **existing_attrs,
                                }
                            )

                    elif isinstance(model_field, models.ManyToManyField):
                        if not isinstance(field.widget, forms.HiddenInput):
                            related_model = model_field.related_model
                            app_label = related_model._meta.app_label
                            model_name = related_model._meta.model_name

                            initial_value = []
                            if self.instance and self.instance.pk:
                                initial_value = list(
                                    getattr(self.instance, field_name).values_list(
                                        "pk", flat=True
                                    )
                                )
                            elif field_name in self.initial:
                                initial_data = self.initial[field_name]
                                if isinstance(initial_data, list):
                                    initial_value = [
                                        item.pk if hasattr(item, "pk") else item
                                        for item in initial_data
                                    ]
                                else:
                                    initial_value = [
                                        (
                                            initial_data.pk
                                            if hasattr(initial_data, "pk")
                                            else initial_data
                                        )
                                    ]

                            submitted_values = (
                                self.data.getlist(field_name, [])
                                if field_name in self.data
                                else []
                            )
                            submitted_values = [v for v in submitted_values if v]

                            all_values = list(
                                set(
                                    [v for v in (initial_value + submitted_values) if v]
                                )
                            )
                            initial_choices = []
                            if all_values:
                                selected_objects = related_model.objects.filter(
                                    pk__in=all_values
                                )
                                initial_choices = [
                                    (obj.pk, str(obj)) for obj in selected_objects
                                ]

                            widget_attrs = {
                                "class": "select2-pagination w-full text-sm",
                                "data-url": reverse_lazy(
                                    f"horilla_generics:model_select2",
                                    kwargs={
                                        "app_label": app_label,
                                        "model_name": model_name,
                                    },
                                ),
                                "data-placeholder": f"Select {model_field.verbose_name.title()}",
                                "multiple": "multiple",
                                "data-initial": (
                                    ",".join(
                                        map(str, submitted_values or initial_value)
                                    )
                                    if (submitted_values or initial_value)
                                    else ""
                                ),
                                "data-field-name": field_name,
                                "id": f"id_{field_name}",
                                "data-form-class": f"{self.__module__}.{self.__class__.__name__}",
                                **existing_attrs,
                            }

                            field.widget = forms.SelectMultiple(
                                choices=initial_choices, attrs=widget_attrs
                            )

                    elif isinstance(model_field, models.ForeignKey):
                        if not isinstance(field.widget, forms.HiddenInput):
                            related_model = model_field.related_model
                            app_label = related_model._meta.app_label
                            model_name = related_model._meta.model_name

                            initial_value = None
                            if self.instance and self.instance.pk:
                                related_obj = getattr(self.instance, field_name, None)
                                initial_value = related_obj.pk if related_obj else None
                            elif field_name in self.initial:
                                initial_data = self.initial[field_name]
                                initial_value = (
                                    initial_data.pk
                                    if hasattr(initial_data, "pk")
                                    else initial_data
                                )

                            submitted_value = (
                                self.data.get(field_name)
                                if field_name in self.data
                                else None
                            )
                            all_values = [
                                v for v in [initial_value, submitted_value] if v
                            ]
                            initial_choices = []
                            try:
                                # Pre-fetch choices for initial rendering
                                queryset = related_model.objects.all()[
                                    :100
                                ]  # Limit to avoid performance issues
                                initial_choices = [
                                    (obj.pk, str(obj)) for obj in queryset
                                ]
                                if all_values:
                                    selected_objects = related_model.objects.filter(
                                        pk__in=all_values
                                    )
                                    initial_choices = [
                                        (obj.pk, str(obj)) for obj in selected_objects
                                    ] + [
                                        (obj.pk, str(obj))
                                        for obj in queryset
                                        if obj.pk not in all_values
                                    ]
                            except Exception as e:
                                logger.error(
                                    f"Error fetching choices for {field_name}: {str(e)}"
                                )

                            widget_attrs = {
                                "class": "select2-pagination w-full",
                                "data-url": reverse_lazy(
                                    f"horilla_generics:model_select2",
                                    kwargs={
                                        "app_label": app_label,
                                        "model_name": model_name,
                                    },
                                ),
                                "data-placeholder": f"Select {model_field.verbose_name.title()}",
                                "data-initial": (
                                    str(submitted_value or initial_value)
                                    if (submitted_value or initial_value)
                                    else ""
                                ),
                                "data-field-name": field_name,
                                "id": f"id_{field_name}",
                                "data-form-class": f"{self.__module__}.{self.__class__.__name__}",
                                **existing_attrs,
                            }

                            field.widget = forms.Select(
                                choices=[("", "---------")] + initial_choices,
                                attrs=widget_attrs,
                            )

                    elif isinstance(field.widget, forms.Select):
                        field.widget.attrs.update(
                            {"class": "js-example-basic-single headselect"}
                        )

            except Exception as e:
                logger.error(f"Error processing field {field_name}: {str(e)}")

            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "sr-only peer"})
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update(
                    {
                        "rows": 4,
                        "placeholder": "Enter description here...",
                    }
                )

    def _add_condition_fields(self):
        """Add condition fields dynamically from the condition model"""
        for field_name in self.condition_fields:
            try:
                model_field = self.condition_model._meta.get_field(field_name)

                if hasattr(model_field, "choices") and model_field.choices:
                    form_field = forms.ChoiceField(
                        choices=[("", "---------")] + list(model_field.choices),
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.Select(
                            attrs={
                                "class": "js-example-basic-single headselect",
                                "data-placeholder": f'Select {field_name.replace("_", " ").title()}',
                                "id": f"id_{field_name}",
                            }
                        ),
                    )
                elif isinstance(model_field, models.ForeignKey):
                    related_model = model_field.related_model
                    app_label = related_model._meta.app_label
                    model_name = related_model._meta.model_name

                    initial_choices = []
                    try:
                        # Pre-fetch a limited set of choices for initial rendering
                        queryset = related_model.objects.all()[
                            :100
                        ]  # Limit to avoid performance issues
                        initial_choices = [(obj.pk, str(obj)) for obj in queryset]
                    except Exception as e:
                        logger.error(
                            f"Error fetching choices for condition field {field_name}: {str(e)}"
                        )

                    form_field = forms.ChoiceField(
                        choices=[("", "---------")] + initial_choices,
                        required=False,
                        label=model_field.verbose_name
                        or field_name.replace("_", " ").title(),
                        widget=forms.Select(
                            attrs={
                                "class": "select2-pagination w-full",
                                "data-url": reverse_lazy(
                                    f"horilla_generics:model_select2",
                                    kwargs={
                                        "app_label": app_label,
                                        "model_name": model_name,
                                    },
                                ),
                                "data-placeholder": f"Select {model_field.verbose_name.title()}",
                                "data-field-name": field_name,
                                "id": f"id_{field_name}",
                                "data-form-class": f"{self.__module__}.{self.__class__.__name__}",
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
                                "id": f"id_{field_name}",
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
                                "id": f"id_{field_name}",
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
                                "id": f"id_{field_name}",
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
                                "id": f"id_{field_name}",
                            }
                        ),
                    )

                form_field.is_custom_field = True
                self.fields[field_name] = form_field

            except Exception as e:
                logger.error(f"Error adding condition field {field_name}: {str(e)}")


class HorillaHistoryForm(forms.Form):
    """Base form for filtering history by date using calendar picker"""

    filter_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": "Select date to filter",
            }
        ),
    )

    def apply_filter(self, history_by_date):
        if not self.is_valid():
            return history_by_date

        filter_date = self.cleaned_data.get("filter_date")
        if filter_date:
            return [
                (date, entries)
                for date, entries in history_by_date
                if date == filter_date
            ]
        return history_by_date


class RowFieldWidget(forms.MultiWidget):
    template_name = "forms/widgets/row_field_widget.html"

    def __init__(self, field_configs, attrs=None):
        widgets = []
        self.field_configs = field_configs
        for config in field_configs:
            if config["type"] == "select":
                widgets.append(
                    forms.Select(
                        attrs={
                            "class": "normal-seclect headselect",
                            "choices": config.get("choices", []),
                        }
                    )
                )
            elif config["type"] == "text":
                widgets.append(
                    forms.TextInput(
                        attrs={
                            "class": "h-[35px] text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md focus-visible:outline-0 placeholder:text-dark-100 text-sm transition focus:border-primary-600",
                            "placeholder": config.get("placeholder", "Enter Value"),
                        }
                    )
                )
        super().__init__(widgets, attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["field_configs"] = self.field_configs
        return context


class RowField(forms.MultiValueField):
    widget = RowFieldWidget

    def __init__(self, field_configs, *args, **kwargs):
        fields = []
        self.field_configs = field_configs
        for config in field_configs:
            if config["type"] == "select":
                fields.append(
                    forms.ChoiceField(
                        choices=config.get("choices", []),
                        required=config.get("required", True),
                    )
                )
            elif config["type"] == "text":
                fields.append(
                    forms.CharField(
                        required=config.get("required", True),
                        max_length=config.get("max_length", None),
                    )
                )
        super().__init__(fields, *args, **kwargs)
        self.is_row_field = True

    def compress(self, data_list):
        # Process the data into your desired format
        return data_list


class CustomFileInput(forms.ClearableFileInput):
    template_name = "forms/widgets/custom_file_input.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        selected_filename = None
        if value:
            # Check if it's a FieldFile object
            if hasattr(value, "name") and value.name:
                # Extract just the filename from the full path
                selected_filename = value.name.split("/")[-1]
            elif isinstance(value, str):
                selected_filename = value.split("/")[-1]

        context["selected_filename"] = selected_filename
        return context


class HorillaAttachmentForm(forms.ModelForm):
    class Meta:
        model = HorillaAttachment
        fields = ["title", "file", "description"]
        labels = {
            "file": "",  # hide label
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                    "placeholder": "Enter title",
                }
            ),
            "file": CustomFileInput(
                attrs={
                    "class": "hidden",
                    "id": "attachmentUpload",
                }
            ),
            "description": SummernoteWidget(
                attrs={
                    "summernote": {
                        "width": "100%",
                        "height": "300px",
                        "styleTags": [
                            "p",
                            "blockquote",
                            "pre",
                            "h1",
                            "h2",
                            "h3",
                            "h4",
                            "h5",
                            "h6",
                            {
                                "title": "Bold",
                                "tag": "b",
                                "className": "font-bold",
                                "value": "b",
                            },
                            {
                                "title": "Italic",
                                "tag": "i",
                                "className": "italic",
                                "value": "i",
                            },
                        ],
                    }
                }
            ),
        }
