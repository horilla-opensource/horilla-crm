"""
Forms for Horilla Core application.

This module contains Django form classes used across the Horilla Core app
"""

# Standard library imports
import logging

# Third-party imports
import pycountry
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

# First-party / Horilla imports
from horilla.auth.models import User
from horilla_core.mixins import OwnerQuerysetMixin
from horilla_generics.forms import (
    HorillaModelForm,
    HorillaMultiStepForm,
    PasswordInputWithEye,
)
from horilla_utils.middlewares import _thread_local

# Local / relative imports
from .models import (
    BusinessHour,
    Company,
    DatedConversionRate,
    Department,
    FiscalYear,
    Holiday,
    MultipleCurrency,
    Role,
)

logger = logging.getLogger(__name__)


class FiscalYearForm(HorillaModelForm):
    """Form class for FiscalYear model."""

    class Meta:
        """Meta options for FiscalYearForm."""

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

        # Get fiscal_year_type and format_type from POST or instance
        fiscal_year_type = (
            self.data.get("fiscal_year_type")
            if self.data
            else getattr(self.instance, "fiscal_year_type", None)
        )

        format_type = (
            self.data.get("format_type")
            if self.data
            else getattr(self.instance, "format_type", None)
        )

        if fiscal_year_type == "standard":
            # For standard type, start_date_day is optional
            self.fields["start_date_day"].required = False
            self.initial["start_date_day"] = None

        elif fiscal_year_type == "custom":
            self.fields["format_type"].required = True
            self.fields["start_date_month"].required = True
            self.fields["display_year_based_on"].required = True
            self.fields["start_date_day"].required = True
            self.fields["week_start_day"].required = True
            self.fields["number_weeks_by"].required = True
            self.fields["period_display_option"].required = True

            # Based on format_type, require specific format fields
            if format_type == "year_based":
                self.fields["year_based_format"].required = True
                self.fields["quarter_based_format"].required = False
            elif format_type == "quarter_based":
                self.fields["quarter_based_format"].required = True
                self.fields["year_based_format"].required = False


class HolidayForm(HorillaModelForm):
    """Form class for Holiday model."""

    class Meta:
        """Meta options for HolidayForm."""

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

        if "weekly_days" in self.errors:
            choices = self.fields["weekly_days"].choices
            valid = [c[0] for c in choices]
            label_to_value = {str(c[1]): c[0] for c in choices}
            values = cleaned_data.get("weekly_days")
            if not isinstance(values, list):
                values = self.data.getlist("weekly_days") if self.data else []

            values = [label_to_value.get(v, v) for v in values]
            if values and all(v in valid for v in values):
                del self.errors["weekly_days"]
                cleaned_data["weekly_days"] = values

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
    """Form to add a new currency for the company."""

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
    """Form to update conversion rates and change default currency."""

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
    """Form to add dated conversion rates for multiple currencies."""

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
    """Form class for BusinessHour model."""

    class Meta:
        """Meta options for BusinessHourForm."""

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

        _has_existing_default = (
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

        if "week_days" in self.errors:
            choices = self.fields["week_days"].choices
            valid = [c[0] for c in choices]
            label_to_value = {str(c[1]): c[0] for c in choices}
            values = cleaned_data.get("week_days")
            if not isinstance(values, list):
                values = self.data.getlist("week_days") if self.data else []

            values = [label_to_value.get(v, v) for v in values]
            if values and all(v in valid for v in values):
                del self.errors["week_days"]
                cleaned_data["week_days"] = values

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
            week_days = cleaned_data.get("week_days") or []
            if len(week_days) > 5:
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
    """Form class for User model with password fields."""

    class Meta:
        """Meta options for UserFormClass."""

        model = User
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
        3: ["department", "role", "company"],
        4: [
            "language",
            "time_zone",
            "date_format",
            "time_format",
            "date_time_format",
            "currency",
            "enable_ai",
        ],
    }

    def clean_email(self):
        """Validate that email is unique"""
        email = self.cleaned_data.get("email")

        if email:
            queryset = User.objects.filter(email=email)
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
                "hx-swap": "innerHTML",
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
        """Get subdivisions for a given country code."""
        try:
            subdivisions = list(
                pycountry.subdivisions.get(country_code=country_code.upper())
            )
            return [(sub.code, sub.name) for sub in subdivisions]
        except Exception:
            return []


class UserFormSingle(HorillaModelForm):
    """Form class for User model."""

    class Meta:
        """Meta options for UserFormSingle."""

        model = User
        fields = [
            "profile",
            "email",
            "first_name",
            "last_name",
            "contact_number",
            "is_active",
            "country",
            "state",
            "city",
            "zip_code",
            "department",
            "role",
            "company",
            "language",
            "time_zone",
            "date_format",
            "time_format",
            "date_time_format",
            "currency",
            "enable_ai",
        ]

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
                "hx-swap": "innerHTML",
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
        """Get subdivisions for a given country code."""
        try:
            subdivisions = list(
                pycountry.subdivisions.get(country_code=country_code.upper())
            )
            return [(sub.code, sub.name) for sub in subdivisions]
        except Exception:
            return []


class UserFormClassSingle(HorillaModelForm):
    """Form class for User model with password fields."""

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
        """Meta options for UserFormClassSingle."""

        model = User
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
        """Validate that username is unique & required."""
        username = self.cleaned_data.get("username")
        if not username:
            raise ValidationError(_("Username is required."))

        existing_user = User.objects.filter(username=username)
        if self.instance and self.instance.pk:
            existing_user = existing_user.exclude(pk=self.instance.pk)

        if existing_user.exists():
            raise ValidationError(_("A user with this username already exists."))

        return username

    def clean_confirm_password(self):
        """Validate that password and confirm_password match."""
        password = self.cleaned_data.get("password")
        confirm_password = self.cleaned_data.get("confirm_password")

        if password or confirm_password:
            if password != confirm_password:
                raise ValidationError(_("The two password fields must match."))

        return confirm_password

    def clean_password(self):
        """Validate password strength."""
        password = self.cleaned_data.get("password")

        if not self.instance or not self.instance.pk:
            if not password:
                raise ValidationError(_("Password is required for new users."))

        if password and len(password) < 8:
            raise ValidationError(_("Password must be at least 8 characters long."))

        return password

    def save(self, commit=True):
        """Override save method to handle password setting."""
        user = super().save(commit=False)

        # Handle password
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)

        if commit:
            user.save()
            self.save_m2m()

        return user


class CompanyMultistepFormClass(OwnerQuerysetMixin, HorillaMultiStepForm):
    """Form class for company model"""

    class Meta:
        """Meta options for CompanyMultistepFormClass."""

        model = Company
        fields = "__all__"

    step_fields = {
        1: [
            "name",
            "icon",
            "email",
            "website",
            "contact_number",
            "fax",
        ],
        2: [
            "annual_revenue",
            "no_of_employees",
            "hq",
        ],
        3: [
            "country",
            "state",
            "city",
            "zip_code",
            "language",
            "time_zone",
        ],
        4: [
            "currency",
            "time_format",
            "date_format",
            "date_time_format",
            "activate_multiple_currencies",
        ],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.current_step < len(self.step_fields):
            self.fields["created_by"].required = False
            self.fields["updated_by"].required = False

        self.fields["country"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("horilla_core:get_country_subdivisions"),
                "hx-target": "#id_state",
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
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
        """Get subdivisions for a given country code."""
        try:
            subdivisions = list(
                pycountry.subdivisions.get(country_code=country_code.upper())
            )
            return [(sub.code, sub.name) for sub in subdivisions]
        except Exception:
            return []


class CompanyFormClass(HorillaModelForm):
    """Form class for Company model."""

    class Meta:
        """Meta options for CompanyFormClass."""

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


class CompanyFormClassSingle(HorillaModelForm):
    """Form class for Company model with all fields."""

    class Meta:
        """Meta options for CompanyFormClassSingle."""

        model = Company
        fields = [
            "name",
            "email",
            "website",
            "icon",
            "contact_number",
            "fax",
            "annual_revenue",
            "no_of_employees",
            "country",
            "state",
            "city",
            "zip_code",
            "language",
            "time_zone",
            "currency",
            "time_format",
            "date_format",
            "date_time_format",
            "hq",
            "activate_multiple_currencies",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["country"].widget.attrs.update(
            {
                "hx-get": reverse_lazy("horilla_core:get_country_subdivisions"),
                "hx-target": "#id_state",
                "hx-trigger": "change",
                "hx-swap": "innerHTML",
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
        """Get subdivisions for a given country code."""
        try:
            subdivisions = list(
                pycountry.subdivisions.get(country_code=country_code.upper())
            )
            return [(sub.code, sub.name) for sub in subdivisions]
        except Exception:
            return []


class AddUsersToRoleForm(forms.Form):
    """Form to add users to a specific role."""

    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        label=_("Users"),
        help_text=_("Select one or more users to assign to the role."),
        widget=forms.SelectMultiple(
            attrs={
                "class": "select2-pagination w-full",
                "data-url": reverse_lazy(
                    "horilla_generics:model_select2",
                    kwargs={
                        "app_label": "horilla_core",
                        "model_name": str(User.__name__),
                    },
                ),
                "data-placeholder": "Select user",
                "multiple": "multiple",
                "data-field-name": "users",
                "id": "id_users",
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
        self.condition_hx_include = kwargs.pop("condition_hx_include", "")
        self.field_permissions = kwargs.pop("field_permissions", {})
        self.save_and_new = kwargs.pop("save_and_new", "")
        self.duplicate_mode = kwargs.pop("duplicate_mode", False)
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
                    _("The following user(s) are already assigned to this role")
                )

        return cleaned_data

    def save(self, commit=True):
        """Assign the selected role to the selected users."""
        role = self.cleaned_data["role"]
        users = self.cleaned_data["users"]
        if commit:
            for user in users:
                user.role = role
                user.save()
        return users


class AddSuperUsersForm(forms.Form):
    """Form to add users as superusers."""

    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        label=_("Users"),
        help_text=_("Select one or more users to grant superuser privileges."),
        widget=forms.SelectMultiple(
            attrs={
                "class": "select2-pagination w-full",
                "data-url": reverse_lazy(
                    "horilla_generics:model_select2",
                    kwargs={
                        "app_label": "horilla_core",
                        "model_name": str(User.__name__),
                    },
                ),
                "data-placeholder": "Select users",
                "multiple": "multiple",
                "data-field-name": "users",
                "id": "id_users",
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
        self.condition_hx_include = kwargs.pop("condition_hx_include", "")
        self.field_permissions = kwargs.pop("field_permissions", {})
        self.save_and_new = kwargs.pop("save_and_new", "")
        self.duplicate_mode = kwargs.pop("duplicate_mode", False)
        super().__init__(*args, **kwargs)

        # Filter users to only show non-superusers from the same company
        company = (
            getattr(self.request, "active_company", None) if self.request else None
        ) or (
            self.request.user.company
            if self.request and self.request.user.is_authenticated
            else None
        )

        if company:
            self.fields["users"].queryset = User.objects.filter(
                is_superuser=False, company=company
            )
        else:
            self.fields["users"].queryset = User.objects.filter(is_superuser=False)

        # Update the select2 URL to include is_superuser=false parameter
        base_url = str(
            reverse_lazy(
                "horilla_generics:model_select2",
                kwargs={
                    "app_label": "horilla_core",
                    "model_name": str(User.__name__),
                },
            )
        )
        self.fields["users"].widget.attrs["data-url"] = f"{base_url}?is_superuser=false"

        for field_name in self.hidden_fields:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.HiddenInput()
                self.fields[field_name].widget.attrs.update({"class": "hidden-input"})

    def clean(self):
        cleaned_data = super().clean()
        users = cleaned_data.get("users")

        if users:
            # Check if any selected users are already superusers
            already_superusers = users.filter(is_superuser=True)
            if already_superusers.exists():
                user_names = ", ".join(
                    [
                        user.get_full_name() or user.username
                        for user in already_superusers
                    ]
                )
                raise forms.ValidationError(
                    _("The following user(s) are already superusers: {users}").format(
                        users=user_names
                    )
                )

        return cleaned_data

    def save(self, commit=True):
        """Add superuser status to the selected users."""
        users = self.cleaned_data["users"]
        if commit:
            for user in users:
                user.is_superuser = True
                user.save()
        return users


class RegionalFormattingForm(HorillaModelForm):
    """Form class for updating user's regional formatting settings."""

    class Meta:
        """Meta options for RegionalFormattingForm."""

        model = User
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
        """Validate that the current password is correct."""
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


class ChangeUserCompanyForm(HorillaModelForm):
    """Form for changing user's company with dynamic role, department, and currency filtering"""

    class Meta:
        model = User
        fields = ["company", "role", "department", "currency"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "company" in self.fields:
            self.fields["company"].queryset = Company.objects.all().order_by("name")
            if hasattr(self, "field_permissions") and self.field_permissions:
                self.field_permissions["company"] = "readwrite"

        if "company" in self.fields:
            hx_vals = {}
            if self.instance and self.instance.pk:
                hx_vals["user_pk"] = str(self.instance.pk)

            attrs = {
                "hx-get": reverse_lazy("horilla_core:get_company_related_fields"),
                "hx-target": "#company-related-fields",
                "hx-swap": "innerHTML",
                "hx-trigger": "change",
                "hx-include": "#id_company",  # Only include the select element by ID
            }

            if hx_vals:
                import json

                attrs["hx-vals"] = json.dumps(hx_vals)

            self.fields["company"].widget.attrs.update(attrs)

        company = None
        if self.data and self.data.get("company"):
            try:
                company = Company.objects.get(pk=self.data.get("company"))
            except (Company.DoesNotExist, ValueError, TypeError):
                pass

        if not company and self.instance and self.instance.pk and self.instance.company:
            company = self.instance.company

        if company:
            self._filter_fields_by_company(company)

    def _filter_fields_by_company(self, company):
        """Filter role, department, and currency fields by company"""

        if "role" in self.fields:
            self.fields["role"].queryset = Role.all_objects.filter(
                company=company, is_active=True
            )

        if "department" in self.fields:
            self.fields["department"].queryset = Department.all_objects.filter(
                company=company, is_active=True
            )

        if "currency" in self.fields:
            self.fields["currency"].queryset = MultipleCurrency.all_objects.filter(
                company=company, is_active=True
            )

    def _get_fresh_queryset(self, field_name, related_model):
        """
        Override to bypass permission filtering for role, department, and currency fields.
        These fields are filtered by company, not by user permissions.
        """
        if field_name in ["role", "department", "currency"]:
            company = None
            if self.data and self.data.get("company"):
                try:
                    from horilla_core.models import Company

                    company_id = self.data.get("company")
                    if isinstance(company_id, list):
                        company_id = company_id[-1] if company_id else None
                    if company_id:
                        company = Company.objects.get(pk=company_id)
                except (Company.DoesNotExist, ValueError, TypeError):
                    pass
            elif self.instance and self.instance.pk and self.instance.company:
                company = self.instance.company

            if company:
                return related_model.all_objects.filter(company=company, is_active=True)
            else:
                return related_model.all_objects.none()

        return super()._get_fresh_queryset(field_name, related_model)

    def clean(self):
        cleaned_data = super().clean()
        company = cleaned_data.get("company")
        role = cleaned_data.get("role")
        department = cleaned_data.get("department")
        currency = cleaned_data.get("currency")

        if company and role:
            if role.company != company:
                self.add_error(
                    "role", f"Selected role does not belong to {company.name}"
                )

        if company and department:
            if department.company != company:
                self.add_error(
                    "department",
                    f"Selected department does not belong to {company.name}",
                )

        if company and currency:
            if currency.company != company:
                self.add_error(
                    "currency", f"Selected currency does not belong to {company.name}"
                )

        if self.instance and self.instance.pk and role:
            current_role = getattr(self.instance, "role", None)

            if current_role != role:
                username = self.instance.username
                existing_user = User.all_objects.filter(
                    username=username, role=role
                ).exclude(pk=self.instance.pk)
                if existing_user.exists():
                    self.add_error(
                        "role",
                        f'Another user with username "{username}" already has this role. Please select a different role.',
                    )

        return cleaned_data
