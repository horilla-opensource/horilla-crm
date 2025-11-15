import logging

import pycountry
from django import forms
from django.apps import apps
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla_generics.forms import (
    HorillaModelForm,
    HorillaMultiStepForm,
    PasswordInputWithEye,
)
from horilla_utils.middlewares import _thread_local

from .models import (
    BusinessHour,
    Company,
    DatedConversionRate,
    FiscalYear,
    Holiday,
    HorillaUser,
    MultipleCurrency,
    Role,
    ScoringCondition,
    ScoringCriterion,
)

logger = logging.getLogger(__name__)


class FiscalYearForm(HorillaModelForm):
    class Meta:
        model = FiscalYear
        fields = [
            "fiscal_year_type",
            "start_date_month",
            "display_year_based_on",
            "start_date_day",
            "format_type",
            "year_based_format",
            "quarter_based_format",
            "week_start_day",
            "number_weeks_by",
            "period_display_option",
            "company",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get fiscal_year_type from POST or instance
        fiscal_year_type = (
            self.data.get("fiscal_year_type")
            if self.data
            else getattr(self.instance, "fiscal_year_type", None)
        )

        if fiscal_year_type == "standard":
            self.fields["start_date_day"].required = False
            self.initial["start_date_day"] = None


class HolidayForm(HorillaModelForm):
    class Meta:
        model = Holiday
        fields = "__all__"
        exclude = [
            "is_active",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "additional_info",
            "company",
        ]
        widgets = {
            "all_users": forms.CheckboxInput(
                attrs={
                    "id": "id_all_users",
                    "hx-trigger": "change",
                    "hx-target": "#holiday-form-view-container",
                    "hx-swap": "outerHTML",
                    "hx-include": "#holiday-form-view",
                }
            ),
            "is_recurring": forms.CheckboxInput(
                attrs={
                    "id": "id_is_recurring",
                    "hx-trigger": "change",
                    "hx-target": "#holiday-form-view-container",
                    "hx-swap": "outerHTML",
                    "hx-include": "#holiday-form-view",
                }
            ),
            "frequency": forms.Select(
                attrs={
                    "id": "id_frequency",
                    "hx-trigger": "change",
                    "hx-target": "#holiday-form-view-container",
                    "hx-swap": "outerHTML",
                    "hx-include": "#holiday-form-view",
                }
            ),
            "monthly_repeat_type": forms.Select(
                attrs={
                    "id": "id_monthly_repeat_type",
                    "hx-trigger": "change",
                    "hx-target": "#holiday-form-view-container",
                    "hx-swap": "outerHTML",
                    "hx-include": "#holiday-form-view",
                }
            ),
            "yearly_repeat_type": forms.Select(
                attrs={
                    "id": "id_yearly_repeat_type",
                    "hx-trigger": "change",
                    "hx-target": "#holiday-form-view-container",
                    "hx-swap": "outerHTML",
                    "hx-include": "#holiday-form-view",
                }
            ),
            "weekly_days": forms.SelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = self.instance
        initial = self.data or self.initial

        base_url = (
            f"/holiday-update-form/{instance.pk}?toggle_all_users=true"
            if instance and instance.pk
            else "/holiday-create-form/?toggle_all_users=true"
        )
        for name in (
            "all_users",
            "is_recurring",
            "frequency",
            "monthly_repeat_type",
            "yearly_repeat_type",
        ):
            if name in self.fields:
                self.fields[name].widget.attrs["hx-get"] = base_url

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

        # All users logic
        if self.fields.get("specific_users") and initial.get("all_users"):
            hide_fields(["specific_users"], nullify=True)

        # Not recurring? Hide all recurrence-related fields
        is_recurring = bool(initial.get("is_recurring"))
        frequency = initial.get("frequency", "")
        if not is_recurring:
            hide_fields(
                [
                    "frequency",
                    "recurs_every_weeks",
                    "weekly_days",
                    "monthly_repeat_type",
                    "monthly_day_of_month",
                    "monthly_interval",
                    "monthly_day_of_week",
                    "monthly_week_of_month",
                    "yearly_repeat_type",
                    "yearly_month",
                    "yearly_day_of_month",
                    "yearly_day_of_week",
                    "yearly_week_of_month",
                ],
                nullify=True,
            )
        else:
            if frequency != "weekly":
                hide_fields(["recurs_every_weeks", "weekly_days"], nullify=True)

            if frequency != "monthly":
                hide_fields(
                    [
                        "monthly_repeat_type",
                        "monthly_day_of_month",
                        "monthly_interval",
                        "monthly_day_of_week",
                        "monthly_week_of_month",
                    ],
                    nullify=True,
                )

            elif frequency == "monthly":
                monthly_repeat_type = initial.get("monthly_repeat_type", "")

                if not monthly_repeat_type:
                    hide_fields(["monthly_day_of_month"], nullify=True)

                if monthly_repeat_type != "day_of_month":
                    hide_fields(["monthly_interval"], nullify=True)

                if monthly_repeat_type != "weekday_of_month":
                    hide_fields(
                        ["monthly_day_of_week", "monthly_week_of_month"], nullify=True
                    )

            if frequency != "yearly":
                hide_fields(
                    [
                        "yearly_repeat_type",
                        "yearly_month",
                        "yearly_day_of_month",
                        "yearly_day_of_week",
                        "yearly_week_of_month",
                    ],
                    nullify=True,
                )

            elif frequency == "yearly":
                yearly_repeat_type = initial.get("yearly_repeat_type", "")

                if not yearly_repeat_type:
                    hide_fields(["yearly_month"], nullify=True)

                if yearly_repeat_type != "day_of_month":
                    hide_fields(["yearly_day_of_month"], nullify=True)

                if yearly_repeat_type != "weekday_of_month":
                    hide_fields(
                        ["yearly_day_of_week", "yearly_week_of_month"], nullify=True
                    )

    def clean(self):
        cleaned_data = super().clean()

        def clear_fields(field_list):
            for field in field_list:
                if field in cleaned_data:
                    cleaned_data[field] = None

        is_recurring = cleaned_data.get("is_recurring")
        frequency = cleaned_data.get("frequency")
        repeat_type = cleaned_data.get("monthly_repeat_type")

        if not is_recurring:
            clear_fields(
                [
                    "frequency",
                    "recurs_every_weeks",
                    "weekly_days",
                    "monthly_repeat_type",
                    "monthly_day_of_month",
                    "monthly_interval",
                    "monthly_day_of_week",
                    "monthly_week_of_month",
                ]
            )
        else:
            if frequency != "weekly":
                clear_fields(["recurs_every_weeks", "weekly_days"])

            if frequency != "monthly":
                clear_fields(
                    [
                        "monthly_repeat_type",
                        "monthly_day_of_month",
                        "monthly_interval",
                        "monthly_day_of_week",
                        "monthly_week_of_month",
                    ]
                )
            else:
                if repeat_type != "day_of_month":
                    clear_fields(["monthly_interval"])
                if repeat_type != "weekday_of_month":
                    clear_fields(["monthly_day_of_week", "monthly_week_of_month"])
                if not repeat_type:
                    clear_fields(["monthly_day_of_month"])

        return cleaned_data


class CurrencyForm(forms.Form):
    currency = forms.ModelChoiceField(
        queryset=MultipleCurrency.objects.none(),
        empty_label="Select a currency",
        label="New Currency",
        required=True,
    )

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        request = getattr(_thread_local, "request", None)
        company = getattr(request, "active_company", None)
        if company:
            self.fields["currency"].queryset = MultipleCurrency.objects.filter(
                company=company
            ).exclude(is_default=True)


class ConversionRateForm(forms.Form):
    new_default_currency = forms.ModelChoiceField(
        queryset=MultipleCurrency.objects.none(),
        empty_label="Select a new default currency",
        label="Change Default Currency",
        required=False,
    )

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        request = getattr(_thread_local, "request", None)
        company = getattr(request, "active_company", None) if request else company
        if company:
            current_default = MultipleCurrency.objects.filter(
                company=company, is_default=True
            ).first()
            other_currencies = MultipleCurrency.objects.filter(company=company).exclude(
                is_default=True
            )
            self.fields["new_default_currency"].queryset = (
                MultipleCurrency.objects.filter(company=company)
            )
            for currency in other_currencies:
                self.fields[f"conversion_rate_{currency.currency}"] = (
                    forms.DecimalField(
                        label=f"1 {current_default.currency if current_default else ''} = (conversion rate to {currency.currency})",
                        max_digits=10,
                        decimal_places=6,
                        required=True,
                        initial=currency.conversion_rate,
                    )
                )


class DatedConversionRateForm(forms.Form):
    start_date = forms.DateField(
        label=_("Start Date"),
        help_text=_("Effective date for these conversion rates"),
        widget=forms.DateInput(attrs={"type": "date"}),
        required=True,
    )

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.company = company
        if company:
            current_default = MultipleCurrency.objects.filter(
                company=company, is_default=True
            ).first()
            other_currencies = MultipleCurrency.objects.filter(company=company).exclude(
                is_default=True
            )
            for currency in other_currencies:
                self.fields[f"conversion_rate_{currency.currency}"] = (
                    forms.DecimalField(
                        label=f"1 {current_default.currency if current_default else ''} = (conversion rate to {currency.currency})",
                        max_digits=10,
                        decimal_places=6,
                        required=True,
                        initial=currency.conversion_rate,  # Initialize with the static rate as a fallback
                    )
                )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        if start_date and self.company:
            for field_name in self.fields:
                if field_name.startswith("conversion_rate_"):
                    currency_code = field_name.replace("conversion_rate_", "")
                    # Get the MultipleCurrency object for the currency code
                    try:
                        currency_obj = MultipleCurrency.objects.get(
                            company=self.company, currency=currency_code
                        )
                    except MultipleCurrency.DoesNotExist:
                        self.add_error(
                            field_name,
                            f"Currency {currency_code} does not exist for this company.",
                        )
                        continue
                    # Check for existing DatedConversionRate with the same currency and start date
                    if DatedConversionRate.objects.filter(
                        company=self.company,
                        currency=currency_obj,  # Use the MultipleCurrency object
                        start_date=start_date,
                    ).exists():
                        self.add_error(
                            field_name,
                            f"A conversion rate for {currency_code} on {start_date} already exists.",
                        )
        return cleaned_data


class BusinessHourForm(HorillaModelForm):
    class Meta:
        model = BusinessHour
        fields = [
            "company",
            "name",
            "time_zone",
            "week_start_day",
            "business_hour_type",
            "timing_type",
            "week_days",
            "default_start_time",
            "default_end_time",
            "monday_start",
            "monday_end",
            "tuesday_start",
            "tuesday_end",
            "wednesday_start",
            "wednesday_end",
            "thursday_start",
            "thursday_end",
            "friday_start",
            "friday_end",
            "saturday_start",
            "saturday_end",
            "sunday_start",
            "sunday_end",
            "is_default",
            "is_active",
        ]
        exclude = [
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "additional_info",
        ]

        widgets = {
            "business_hour_type": forms.Select(
                attrs={
                    "id": "id_business_hour_type",
                    "hx-trigger": "change",
                    "hx-target": "#business-hour-form-view-container",
                    "hx-swap": "outerHTML",
                    "hx-include": "#business-hour-form-view",
                }
            ),
            "timing_type": forms.Select(
                attrs={
                    "id": "id_timing_type",
                    "hx-trigger": "change",
                    "hx-target": "#business-hour-form-view-container",
                    "hx-swap": "outerHTML",
                    "hx-include": "#business-hour-form-view",
                }
            ),
            "week_days": forms.SelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        initial = self.data or self.initial

        base_url = (
            f"/business-hour-update-form/{instance.pk}?toggle_data=true"
            if instance and instance.pk
            else "/business-hour-create-form/?toggle_data=true"
        )

        for name in ("business_hour_type", "timing_type"):
            if name in self.fields:
                self.fields[name].widget.attrs["hx-get"] = base_url

        has_existing_default = (
            BusinessHour.objects.filter(is_default=True)
            .exclude(pk=instance.pk if instance.pk else None)
            .exists()
        )

        # if "is_default" in self.fields and has_existing_default:
        self.fields["is_default"].widget.attrs.update(
            {
                "id": "id_is_default",
                "hx-on:click": "isElementChecked(this)",
                "hx-target": "#business-hour-form-view-container",
                "hx-swap": "outerHTML",
                "hx-include": "#business-hour-form-view",
                "data-message": _(
                    "Changing the default will update the current default business hour. Enable to set this as default; disable to allow another. Proceed?"
                ),
            }
        )

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

        DAY_FIELDS = [
            "monday_start",
            "monday_end",
            "tuesday_start",
            "tuesday_end",
            "wednesday_start",
            "wednesday_end",
            "thursday_start",
            "thursday_end",
            "friday_start",
            "friday_end",
            "saturday_start",
            "saturday_end",
            "sunday_start",
            "sunday_end",
        ]

        DEFAULT_FIELDS = ["default_start_time", "default_end_time"]
        TIMING_FIELDS = DEFAULT_FIELDS + ["timing_type"] + DAY_FIELDS

        business_hour_type = initial.get("business_hour_type", "")
        custom_timing_type = initial.get("timing_type", "")

        if business_hour_type != "24_5" and not (
            business_hour_type == "custom" and custom_timing_type == "same"
        ):
            hide_fields(["week_days"], nullify=True)

        if business_hour_type != "custom":
            hide_fields(TIMING_FIELDS, nullify=True)
        else:
            custom_timing_type = initial.get("timing_type", "")
            if custom_timing_type != "same":
                hide_fields(DEFAULT_FIELDS, nullify=True)
            if custom_timing_type != "different":
                hide_fields(DAY_FIELDS, nullify=True)

    def clean(self):
        cleaned_data = super().clean()

        def clear_fields(field_list):
            for field in field_list:
                cleaned_data[field] = None

        if cleaned_data.get("business_hour_type") != "custom":
            clear_fields(["timing_type"])

        if cleaned_data.get("business_hour_type") == "24_7":
            cleaned_data["week_days"] = [
                "sun",
                "mon",
                "tue",
                "wed",
                "thu",
                "fri",
                "sat",
            ]

        if cleaned_data.get("business_hour_type") == "24_5":
            if len(cleaned_data.get("week_days")) > 5:
                self.add_error(
                    "week_days",
                    _("You can select a maximum of 5 days for 24×5 business hours."),
                )

        if cleaned_data.get("business_hour_type") == "custom":
            if cleaned_data.get("timing_type") == "same":
                week_days = cleaned_data.get("week_days") or []
                default_start = cleaned_data.get("default_start_time")
                default_end = cleaned_data.get("default_end_time")

                # Map short codes to full field names
                day_map = {
                    "mon": "monday",
                    "tue": "tuesday",
                    "wed": "wednesday",
                    "thu": "thursday",
                    "fri": "friday",
                    "sat": "saturday",
                    "sun": "sunday",
                }

                for short_code in week_days:
                    day = day_map.get(short_code)
                    if day:
                        cleaned_data[f"{day}_start"] = default_start
                        cleaned_data[f"{day}_end"] = default_end

            if cleaned_data.get("timing_type") == "different":
                week_days_selected = []
                day_map = {
                    "mon": "monday",
                    "tue": "tuesday",
                    "wed": "wednesday",
                    "thu": "thursday",
                    "fri": "friday",
                    "sat": "saturday",
                    "sun": "sunday",
                }

                for short, full in day_map.items():
                    start = cleaned_data.get(f"{full}_start")
                    end = cleaned_data.get(f"{full}_end")
                    if start and end:
                        week_days_selected.append(short)

                cleaned_data["week_days"] = week_days_selected

        return cleaned_data


class UserFormClass(HorillaMultiStepForm):
    class Meta:
        model = HorillaUser
        fields = "__all__"
        # exclude = ['profile']

    step_fields = {
        1: [
            "profile",
            "email",
            "first_name",
            "last_name",
            "contact_number",
            "is_active",
        ],
        2: ["country", "state", "city", "zip_code"],
        3: ["department", "role"],
        4: [
            "language",
            "time_zone",
            "date_format",
            "time_format",
            "date_time_format",
            "currency",
        ],
    }

    def clean_email(self):
        """Validate that email is unique"""
        email = self.cleaned_data.get("email")

        if email:
            queryset = HorillaUser.objects.filter(email=email)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise forms.ValidationError("A user with this email already exists.")

        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in ["first_name", "last_name", "email", "contact_number"]:
            if field in self.fields:
                self.fields[field].required = True

        self.fields["country"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("horilla_core:get_country_subdivisions"),
                "hx-target": "#id_state",
                "hx-trigger": "change",
            }
        )

        self.fields["state"] = forms.ChoiceField(
            choices=[],
            required=False,
            widget=forms.Select(
                attrs={"id": "id_state", "class": "js-example-basic-single headselect"}
            ),
        )

        if "country" in self.data:
            country_code = self.data.get("country")
            self.fields["state"].choices = self.get_subdivision_choices(country_code)
        elif self.instance.pk and self.instance.country:
            self.fields["state"].choices = self.get_subdivision_choices(
                self.instance.country.code
            )

    def get_subdivision_choices(self, country_code):
        try:
            subdivisions = list(
                pycountry.subdivisions.get(country_code=country_code.upper())
            )
            return [(sub.code, sub.name) for sub in subdivisions]
        except:
            return []


class UserFormClassSingle(HorillaModelForm):
    # Add password fields that are not part of the model
    password = forms.CharField(
        widget=PasswordInputWithEye(),
        label=_("Password"),
        help_text=_("Enter a secure password"),
        required=True,
    )

    confirm_password = forms.CharField(
        widget=PasswordInputWithEye(),
        label=_("Confirm Password"),
        help_text=_("Enter the same password again for verification"),
        required=True,
    )

    class Meta:
        model = HorillaUser
        fields = [
            "profile",
            "email",
            "first_name",
            "last_name",
            "username",
            "contact_number",
            "password",
            "confirm_password",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Configure username field
        self.fields["username"].widget.attrs.update(
            {
                "class": "text-color-600 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600",
                "placeholder": "Enter username",
            }
        )
        self.fields["username"].required = True
        self.fields["username"].help_text = _(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        )

        # If this is an edit form (instance exists), don't require passwords
        if self.instance and self.instance.pk:
            self.fields["password"].required = False
            self.fields["confirm_password"].required = False
            self.fields["password"].help_text = _(
                "Leave blank to keep current password"
            )
            self.fields["confirm_password"].help_text = _(
                "Leave blank to keep current password"
            )

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if not username:
            raise ValidationError(_("Username is required."))

        existing_user = HorillaUser.objects.filter(username=username)
        if self.instance and self.instance.pk:
            existing_user = existing_user.exclude(pk=self.instance.pk)

        if existing_user.exists():
            raise ValidationError(_("A user with this username already exists."))

        return username

    def clean_confirm_password(self):
        password = self.cleaned_data.get("password")
        confirm_password = self.cleaned_data.get("confirm_password")

        if password or confirm_password:
            if password != confirm_password:
                raise ValidationError(_("The two password fields must match."))

        return confirm_password

    def clean_password(self):
        password = self.cleaned_data.get("password")

        if not self.instance or not self.instance.pk:
            if not password:
                raise ValidationError(_("Password is required for new users."))

        if password and len(password) < 8:
            raise ValidationError(_("Password must be at least 8 characters long."))

        return password

    def save(self, commit=True):
        user = super().save(commit=False)

        # Handle password
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)

        if commit:
            user.save()
            self.save_m2m()

        return user


class CompanyFormClass(HorillaModelForm):
    class Meta:
        model = Company
        fields = [
            "name",
            "icon",
            "email",
            "contact_number",
            "country",
            "no_of_employees",
            "annual_revenue",
            "currency",
            "activate_multiple_currencies",
        ]


class AddUsersToRoleForm(forms.Form):
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        label=_("Role"),
        help_text=_("Select the role to assign to users."),
        widget=forms.Select(
            attrs={
                "class": "select2-pagination w-full",
                "data-url": reverse_lazy(
                    f"horilla_generics:model_select2",
                    kwargs={"app_label": "horilla_core", "model_name": "Role"},
                ),
                "data-placeholder": f"Select role",
                "data-field-name": "role",
                "id": f"id_role",
            }
        ),
    )
    users = forms.ModelMultipleChoiceField(
        queryset=HorillaUser.objects.all(),
        label=_("Users"),
        help_text=_("Select one or more users to assign to the role."),
        widget=forms.SelectMultiple(
            attrs={
                "class": "select2-pagination w-full",
                "data-url": reverse_lazy(
                    f"horilla_generics:model_select2",
                    kwargs={"app_label": "horilla_core", "model_name": "HorillaUser"},
                ),
                "data-placeholder": f"Select user",
                "multiple": "multiple",
                "data-field-name": "users",
                "id": f"id_users",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.full_width_fields = kwargs.pop("full_width_fields", [])
        self.dynamic_create_fields = kwargs.pop("dynamic_create_fields", [])
        self.hidden_fields = kwargs.pop("hidden_fields", [])
        self.condition_fields = kwargs.pop("condition_fields", [])
        self.condition_model = kwargs.pop("condition_model", None)
        self.condition_field_choices = kwargs.pop("condition_field_choices", {})
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        for field_name in self.hidden_fields:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.HiddenInput()
                self.fields[field_name].widget.attrs.update({"class": "hidden-input"})

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        users = cleaned_data.get("users")

        if role and users:
            duplicates = users.filter(role=role)
            if duplicates.exists():
                raise forms.ValidationError(
                    _(f"The following user(s) are already assigned to this role")
                )

        return cleaned_data

    def save(self, commit=True):
        role = self.cleaned_data["role"]
        users = self.cleaned_data["users"]
        if commit:
            for user in users:
                user.role = role
                user.save()
        return users


class ScoringCriterionForm(HorillaModelForm):
    def __init__(self, *args, **kwargs):
        self.row_id = kwargs.pop("row_id", "0")
        kwargs["condition_model"] = ScoringCondition
        self.instance_obj = kwargs.get("instance")

        model_name = None
        request = kwargs.get("request")
        if request:
            model_name = request.GET.get("model_name") or request.POST.get("model_name")
        if self.instance_obj:
            model_name = self.instance_obj.rule.module

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
        self.model_name = model_name or ""
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
                            "hx-include": f'[name="field_{row_id}"],#id_value_{row_id}',
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
                    model_fields = [
                        (field.name, field.verbose_name or field.name)
                        for field in model._meta.get_fields()
                        if field.concrete and not field.is_relation
                    ]
                    field_choices.extend(model_fields)

            except Exception as e:
                logger.error(
                    f"Error fetching model {model_name}: {str(e)}", exc_info=True
                )

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
                                "hx-target": f"#id_value_0_container",
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
                                "data-container-id": f"value-field-container-0",
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
                logger.error(f"Error adding condition field {field_name}: {str(e)}")

        # Set initial values for edit mode
        self._set_initial_condition_values()

    def clean(self):
        """Process multiple condition rows from form data"""
        cleaned_data = super().clean()

        condition_rows = self._extract_condition_rows()

        if not condition_rows:
            raise forms.ValidationError("At least one condition must be provided.")

        cleaned_data["condition_rows"] = condition_rows

        return cleaned_data

    def _extract_condition_rows(self):
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
        model = ScoringCriterion
        fields = ["rule", "points", "operation_type"]
        widgets = {
            "points": forms.NumberInput(
                attrs={
                    "class": "text-color-600 p-2 w-full border border-dark-50 rounded-md mt-1"
                }
            ),
        }


class RegionalFormattingForm(HorillaModelForm):
    class Meta:
        model = HorillaUser
        fields = [
            "date_format",
            "time_format",
            "date_time_format",
            "language",
            "time_zone",
            "currency",
            "number_grouping",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        hx_post_url = reverse_lazy("horilla_core:regional_formating_view")

        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.update(
                    {
                        "hx-post": hx_post_url,
                        "hx-trigger": "change",
                        "hx-target": "#messages-container",
                        "hx-swap": "innerHTML",
                        "hx-select": "#messages-container",
                    }
                )


class ChangePasswordForm(forms.Form):
    """Form for changing user password"""

    current_password = forms.CharField(
        widget=PasswordInputWithEye(attrs={"placeholder": _("Enter current password")}),
        label=_("Current Password"),
    )
    new_password = forms.CharField(
        widget=PasswordInputWithEye(attrs={"placeholder": _("Enter new password")}),
        label=_("New Password"),
    )
    confirm_password = forms.CharField(
        widget=PasswordInputWithEye(attrs={"placeholder": _("Confirm your password")}),
        label=_("Confirm New Password"),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current_password = self.cleaned_data.get("current_password")
        if not self.user.check_password(current_password):
            self.add_error("current_password", _("Current password is incorrect."))
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        current_password = cleaned_data.get("current_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                self.add_error(
                    "confirm_password",
                    _("Confirm password and new password must be match"),
                )

            if current_password and new_password == current_password:
                self.add_error(
                    "new_password",
                    _("New password must be different from current password."),
                )

        return cleaned_data
