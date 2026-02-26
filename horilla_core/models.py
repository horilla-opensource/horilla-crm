"""
models for horilla core app
"""

# Standard library imports
import json
import logging
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from auditlog.models import AuditlogHistoryField, LogEntry

# Third-party imports
from dateutil.relativedelta import relativedelta

# Django imports
from django.apps import apps
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import (
    AbstractUser,
    AnonymousUser,
    Permission,
    UserManager,
)
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.formats import time_format
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from djmoney.settings import CURRENCY_CHOICES
from multiselectfield import MultiSelectField
from pytz import common_timezones

# First-party / Horilla imports
from horilla.menu.sub_section_menu import sub_section_menu
from horilla.registry.permission_registry import permission_exempt_model
from horilla.utils.choices import (
    CURRENCY_FORMAT_CHOICES,
    DATE_FORMAT_CHOICES,
    DATETIME_FORMAT_CHOICES,
    DAY_CHOICES,
    MONTH_CHOICES,
    NUMBER_GROUPING_CHOICES,
    TIME_FORMAT_CHOICES,
)
from horilla_utils.methods import render_template
from horilla_utils.middlewares import _thread_local

logger = logging.getLogger(__name__)


def upload_path(instance, filename):
    """
    Generates a unique file path for uploads in the format:
    app_label/model_name/field_name/originalfilename-uuid.ext
    """
    ext = filename.split(".")[-1]
    base_name = ".".join(filename.split(".")[:-1]) or "file"
    unique_name = f"{slugify(base_name)}-{uuid4().hex[:8]}.{ext}"

    # Try to find which field is uploading this file
    field_name = next(
        (
            k
            for k, v in instance.__dict__.items()
            if hasattr(v, "name") and v.name == filename
        ),
        None,
    )

    app_label = instance._meta.app_label
    model_name = instance._meta.model_name

    if field_name:
        return f"{app_label}/{model_name}/{field_name}/{unique_name}"
    return f"{app_label}/{model_name}/{unique_name}"


@permission_exempt_model
class HorillaContentType(ContentType):
    """Proxy model for Django's ContentType with custom verbose names."""

    class Meta:
        """Meta options for the HorillaContentType model."""

        proxy = True
        verbose_name = _("Model")
        verbose_name_plural = _("Models")

    def __str__(self):
        model_cls = self.model_class()
        if model_cls:
            return model_cls._meta.verbose_name.title()
        return self.model.replace("_", " ").title()


class Company(models.Model):
    """
    Company model representing business entities in the system.
    """

    name = models.CharField(max_length=255, verbose_name=_("Company Name"))
    email = models.EmailField(max_length=255, verbose_name=_("Email Address"))
    website = models.URLField(max_length=255, blank=True, verbose_name=_("Website"))
    icon = models.ImageField(
        upload_to=upload_path,
        null=True,
        blank=True,
        verbose_name=_("Company Icon"),
    )
    contact_number = models.CharField(max_length=20, verbose_name=_("Contact Number"))
    fax = models.CharField(
        max_length=20, blank=True, null=True, verbose_name=_("Fax Number")
    )
    annual_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Annual Revenue"),
    )
    no_of_employees = models.PositiveIntegerField(verbose_name=_("Number of Employees"))
    hq = models.BooleanField(default=False, verbose_name=_("Head quarter"))
    city = models.CharField(max_length=255, verbose_name=_("City"))
    state = models.CharField(max_length=255, verbose_name=_("State/Province"))
    country = CountryField(verbose_name=_("Country"))
    zip_code = models.CharField(max_length=20, verbose_name=_("ZIP/Postal Code"))
    language = models.CharField(
        max_length=50,
        choices=settings.LANGUAGES,
        blank=True,
        null=True,
        verbose_name=_(
            "Language",
        ),
    )
    time_zone = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=[(tz, tz) for tz in common_timezones],
        verbose_name=_("Time Zone"),
    )
    currency = models.CharField(
        max_length=20,
        choices=CURRENCY_CHOICES,
        blank=True,
        null=True,
        help_text=_("Select your preferred currency"),
        verbose_name=_("Currency"),
    )
    time_format = models.CharField(
        max_length=20,
        choices=TIME_FORMAT_CHOICES,
        default="%I:%M:%S %p",
        help_text=_("Select your preferred time format."),
        verbose_name=_("Time Format"),
    )
    date_format = models.CharField(
        max_length=20,
        choices=DATE_FORMAT_CHOICES,
        default="%Y-%m-%d",
        help_text=_("Select your preferred date format."),
        verbose_name=_("Date Format"),
    )
    date_time_format = models.CharField(
        max_length=100,
        choices=DATETIME_FORMAT_CHOICES,
        default="%Y-%m-%d %H:%M:%S",
        help_text=_("Select your preferred date time format."),
        verbose_name=_("Date Time Format"),
    )
    activate_multiple_currencies = models.BooleanField(
        default=False, verbose_name=_("Activate Multiple Currencies")
    )
    all_objects = models.Manager()
    objects = models.Manager()

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_created",
        verbose_name=_("Created By"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_updated",
        verbose_name=_("Updated By"),
    )

    class Meta:
        """
        Meta options for the Company model.
        """

        verbose_name = _("Branch")
        verbose_name_plural = _("Branches")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"

    def get_detail_view_url(self):
        """
        This method to get detail view url
        """
        return reverse_lazy("horilla_core:branch_detail_view", kwargs={"pk": self.pk})

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "horilla_core:edit_company_multi_step", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy("horilla_core:branch_delete", kwargs={"pk": self.pk})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_currency = self.currency

    def save(self, *args, **kwargs):
        """
        Fixed save method to prevent recursion and handle currency changes.
        """
        if hasattr(self, "_saving"):
            super().save(*args, **kwargs)
            return None

        self._saving = True
        try:
            if not Company.objects.exclude(pk=self.pk).filter(hq=True).exists():
                self.hq = True
            elif self.hq:
                Company.objects.exclude(pk=self.pk).filter(hq=True).update(hq=False)

            old_currency = getattr(self, "_original_currency", None)

            # Check for currency change
            currency_changed = (
                old_currency is not None
                and old_currency != self.currency
                and self.currency is not None
            )

            if currency_changed:
                self._handle_currency_change(old_currency)

            super().save(*args, **kwargs)

            self._original_currency = self.currency

            if self.activate_multiple_currencies:
                from horilla_core.models import MultipleCurrency

                default_currency = MultipleCurrency.objects.filter(
                    company=self, is_default=True
                ).first()
                if default_currency and default_currency.currency != self.currency:
                    self._handle_currency_change(self.currency)
                    self.currency = default_currency.currency
                    super().save(*args, **kwargs)

            return None

        except Exception as e:
            logger.error("Error saving company %s: %s", self.pk, e)
            raise
        finally:
            del self._saving

    def _handle_currency_change(self, old_currency):
        """
        Handle currency change with optimized bulk updates and correct conversion logic.

        Conversion logic:
        - Get the conversion rate between old and new currency
        - Apply the rate directly to all amounts
        """
        from horilla_core.models import MultipleCurrency
        from horilla_core.signals import company_currency_changed

        request = getattr(_thread_local, "request", None)

        try:
            with transaction.atomic():
                old_default = MultipleCurrency.objects.filter(
                    company=self, currency=old_currency
                ).first()

                new_default_currency = MultipleCurrency.objects.filter(
                    company=self, currency=self.currency
                ).first()

                # Create new default currency if it doesn't exist
                if not new_default_currency:
                    new_default_currency = MultipleCurrency.objects.create(
                        company=self,
                        currency=self.currency,
                        is_default=True,
                        conversion_rate=Decimal("1.00"),
                        decimal_places=2,
                        format="western_format",
                        created_at=timezone.now(),
                        updated_at=timezone.now(),
                        created_by=request.user if request else None,
                        updated_by=request.user if request else None,
                    )

                old_rate = (
                    old_default.conversion_rate if old_default else Decimal("1.0")
                )
                new_rate = Decimal("1.0")
                conversion_rate = new_rate / old_rate
                MultipleCurrency.objects.filter(company=self).update(is_default=False)
                new_default_currency.is_default = True
                new_default_currency.conversion_rate = Decimal("1.00")
                new_default_currency.save()
                company_currency_changed.send(
                    sender=self.__class__, company=self, conversion_rate=conversion_rate
                )

        except Exception as e:
            logger.error(
                "Error handling currency change for company %s: %s",
                self.id,
                e,
            )
            raise

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.name}&background=random"
        return url

    def get_avatar_with_name(self):
        """
        Returns HTML to render profile image and full name (first + last name).
        """
        image_url = self.icon.url if self.icon else self.get_avatar()
        name = self.name
        return format_html(
            """
            <div class="flex items-center space-x-2">
                <img src="{}" alt="{}" class="w-8 h-8 rounded-full object-cover" />
                <span class="text-sm font-medium text-gray-900 hover:text-primary-600">{}</span>
            </div>
            """,
            image_url,
            name,
            name,
        )


class CompanyFilteredManager(models.Manager):
    """Manager that filters queryset by active company in request."""

    def get_queryset(self):
        """Get queryset filtered by active company."""
        queryset = super().get_queryset()
        try:
            request = getattr(_thread_local, "request", None)
            if request is None:
                return queryset
            # Check if request has session attribute before accessing it
            if hasattr(request, "session") and request.session.get(
                "show_all_companies", False
            ):
                return queryset

            company = getattr(request, "active_company", None)
            if company:
                queryset = queryset.filter(company=company)
            else:
                queryset = queryset
        except Exception as e:
            logger.error("Error in CompanyFilteredManager.get_queryset: %s", e)
        return queryset


class HorillaCoreModel(models.Model):
    """
    Core Base model
    """

    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    additional_info = models.JSONField(
        blank=True, null=True, verbose_name=_("Additional info")
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Company"),
    )
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name=_("Created At")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_created",
        verbose_name=_("Created By"),
    )
    updated_at = models.DateTimeField(
        default=timezone.now, verbose_name=_("Updated At")
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_updated",
        verbose_name=_("Updated By"),
    )
    history = AuditlogHistoryField()
    objects = CompanyFilteredManager()
    all_objects = models.Manager()

    field_permissions_exclude = [
        "is_active",
        "additional_info",
        "company",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]

    class Meta:
        """
        Meta options for the HorillaCoreModel."""

        abstract = True

    def save(self, *args, **kwargs):
        """
        Override save to automatically set created_by, updated_by, created_at,
        updated_at, and company fields.
        """
        user = None

        request = getattr(_thread_local, "request", None)
        if request:
            user = getattr(request, "user", None)
        now = timezone.now()
        if not self.pk:
            if user and not isinstance(user, AnonymousUser):
                self.created_by = user
                self.updated_by = user
            self.created_at = now
            self.updated_at = now

        else:
            if user and not isinstance(user, AnonymousUser):
                self.updated_by = user
            self.updated_at = now
        super().save(*args, **kwargs)

    @property
    def histories(self):
        """
        Returns sorted auditlog history entries for this object.
        Usage: instance.histories
        """
        return self.history.all().order_by("-timestamp")

    @property
    def full_histories(self):
        """
        Returns auditlog history for this object + any related models (FK or GFK) with
        optimized status field retrieval.
        """
        own_history = list(self.history.all())

        current_model = self.__class__
        content_type = ContentType.objects.get_for_model(current_model)
        related_history = []

        model_ct_map = {
            model: ContentType.objects.get_for_model(model)
            for model in apps.get_models()
        }

        for model, model_ct in model_ct_map.items():
            opts = model._meta
            related_pks = set()

            fk_fields = [
                f
                for f in opts.get_fields()
                if isinstance(f, models.ForeignKey) and f.related_model == current_model
            ]

            if fk_fields:
                or_conditions = models.Q()
                for field in fk_fields:
                    or_conditions |= models.Q(**{field.name: self})

                related_pks.update(
                    model.objects.filter(or_conditions).values_list("pk", flat=True)
                )

            gfk_fields = [
                f
                for f in model._meta.private_fields
                if isinstance(f, GenericForeignKey)
            ]

            for gfk in gfk_fields:
                ct_field = gfk.ct_field
                id_field = gfk.fk_field

                gfk_pks = model.objects.filter(
                    **{ct_field: content_type, id_field: self.pk}
                ).values_list("pk", flat=True)

                related_pks.update(gfk_pks)

            if related_pks:
                if hasattr(model, "status"):
                    status_map = {
                        str(obj.pk): obj.status
                        for obj in model.objects.filter(pk__in=related_pks).only(
                            "pk", "status"
                        )
                    }

                    entries = LogEntry.objects.filter(
                        content_type=model_ct,
                        object_pk__in=[str(pk) for pk in related_pks],
                    )

                    for entry in entries:
                        entry.status = status_map.get(entry.object_pk)
                    related_history.extend(entries)
                else:
                    related_history.extend(
                        LogEntry.objects.filter(
                            content_type=model_ct,
                            object_pk__in=[str(pk) for pk in related_pks],
                        )
                    )
        return sorted(
            own_history + related_history, key=lambda x: x.timestamp, reverse=True
        )


class Department(HorillaCoreModel):
    """
    Department model
    """

    department_name = models.CharField(
        max_length=50, blank=False, verbose_name=_("Department Name")
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    class Meta:
        """
        Meta options for the Department model.
        """

        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        unique_together = (("department_name", "company"),)

    def __str__(self):
        return str(self.department_name)

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "horilla_core:department_update_form", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """

        return reverse_lazy(
            "horilla_core:department_delete_view", kwargs={"pk": self.pk}
        )


class Role(HorillaCoreModel):
    """
    Role model
    """

    role_name = models.CharField(max_length=255, verbose_name=_("Role"))
    parent_role = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subroles",
        verbose_name="Parent Role",
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    permissions = models.ManyToManyField(
        Permission, blank=True, related_name="roles", verbose_name=_("Permissions")
    )

    class Meta:
        """
        Meta options for the Role model.
        """

        verbose_name = _("Role")
        verbose_name_plural = _("Roles")

    def __str__(self):
        return str(self.role_name)

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy("horilla_core:delete_role", kwargs={"pk": self.pk})

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("horilla_core:edit_roles_view", kwargs={"pk": self.pk})


class MultipleCurrency(HorillaCoreModel):
    """
    Multiple Currency model
    """

    currency = models.CharField(
        max_length=20,
        choices=CURRENCY_CHOICES,
        blank=True,
        null=True,
        help_text=_("Select your preferred currency"),
        verbose_name=_("Currency"),
    )
    conversion_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text=_("conversion rate from default currency"),
        verbose_name=_("Conversion Rate"),
    )
    decimal_places = models.IntegerField(default=2, verbose_name=_("Decimal places"))
    format = models.CharField(
        choices=CURRENCY_FORMAT_CHOICES,
        max_length=20,
        default="western_format",
        verbose_name=_("Number grouping format"),
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Default Currency"),
        help_text=_("Mark this currency as the default for the system"),
    )

    class Meta:
        """
        Meta options for the MultipleCurrency model.
        """

        verbose_name = _("Multiple Currency")
        verbose_name_plural = _("Multiple Currencies")

    def __str__(self):
        return str(self.currency)

    def get_currency_code(self):
        """
        Return currency code
        """
        return self.currency

    def save(self, *args, **kwargs):
        """
        Fixed save method to prevent recursion
        """

        # Prevent infinite recursion
        if hasattr(self, "_saving"):
            return super().save(*args, **kwargs)

        self._saving = True
        try:
            if self.is_default:
                MultipleCurrency.objects.filter(
                    company=self.company, is_default=True
                ).exclude(pk=self.pk).update(is_default=False)
                if self.company and self.company.currency != self.currency:
                    Company.objects.filter(pk=self.company.pk).update(
                        currency=self.currency
                    )
                    self.company.currency = self.currency

            super().save(*args, **kwargs)
            return None

        finally:
            del self._saving

    def get_conversion_rate_for_date(self, conversion_date=None):
        """
        Get the conversion rate for a specific date.
        If no date provided, use today's date.
        First checks DatedConversionRate, falls back to static conversion_rate.

        Args:
            conversion_date: The date to get the conversion rate for

        Returns:
            Decimal: The conversion rate
        """
        if conversion_date is None:
            conversion_date = date.today()

        # Try to get dated conversion rate
        dated_rate = (
            DatedConversionRate.objects.filter(
                company=self.company, currency=self, start_date__lte=conversion_date
            )
            .order_by("-start_date")
            .first()
        )

        if dated_rate:
            # Check if this rate is still valid (no newer rate exists before conversion_date)
            return dated_rate.conversion_rate

        # Fall back to static conversion rate
        return self.conversion_rate

    def format_amount(self, amount):
        """
        Format amount according to currency's decimal places and format.

        Supported formats:
        - western_format: 1,234,567.00 (comma thousand separator, dot decimal)
        - european_format: 1.234.567,00 (dot thousand separator, comma decimal)
        - scientific_format: 1 234 567,00 (space thousand separator, comma decimal)
        - indian_format: 12,34,567.00 (Indian grouping style)
        """
        if amount is None:
            # Return zero with correct decimal places
            zero_str = "0." + "0" * self.decimal_places
            return zero_str

        amount = Decimal(str(amount))
        quantize_string = "0." + "0" * self.decimal_places
        formatted_amount = amount.quantize(
            Decimal(quantize_string), rounding=ROUND_HALF_UP
        )

        if self.format == "western_format":
            # 1,234,567.00
            return f"{formatted_amount:,.{self.decimal_places}f}"

        if self.format == "european_format":
            # 1.234.567,00 (dot as thousand separator, comma as decimal)
            western = f"{formatted_amount:,.{self.decimal_places}f}"
            # Swap: comma -> temp, dot -> comma, temp -> dot
            return western.replace(",", "X").replace(".", ",").replace("X", ".")

        if self.format == "scientific_format":
            # 1 234 567,00 (space as thousand separator, comma as decimal)
            western = f"{formatted_amount:,.{self.decimal_places}f}"
            # Replace comma with space, dot with comma
            return western.replace(",", " ").replace(".", ",")

        if self.format == "indian_format":
            # 12,34,567.00 (Indian grouping: last 3 digits, then groups of 2)
            amount_str = str(formatted_amount)
            parts = amount_str.split(".")
            integer_part = parts[0]
            decimal_part = parts[1] if len(parts) > 1 else "0" * self.decimal_places

            # Handle negative numbers
            is_negative = integer_part.startswith("-")
            if is_negative:
                integer_part = integer_part[1:]

            if len(integer_part) > 3:
                last_three = integer_part[-3:]
                remaining = integer_part[:-3]
                # Group remaining digits in pairs from right to left
                groups = []
                while remaining:
                    groups.append(remaining[-2:])
                    remaining = remaining[:-2]
                grouped = ",".join(reversed(groups))
                integer_part = grouped + "," + last_three

            result = f"{integer_part}.{decimal_part}"
            return f"-{result}" if is_negative else result

        # Fallback: format with correct decimal places
        return f"{formatted_amount:.{self.decimal_places}f}"

    def display_with_symbol(self, amount):
        """Display amount with currency symbol - Example: USD 100.00"""
        formatted = self.format_amount(amount)
        return f"{self.currency} {formatted}"

    def convert_from_default(self, amount, conversion_date=None):
        """
        Convert amount from default currency to this currency.
        Uses dated conversion rate if available.

        Args:
            amount: Amount to convert
            conversion_date: Date for conversion rate lookup
        """
        if amount is None:
            return Decimal("0")

        rate = self.get_conversion_rate_for_date(conversion_date)
        return Decimal(str(amount)) * rate

    def convert_to_default(self, amount, conversion_date=None):
        """
        Convert amount from this currency to default currency.
        Uses dated conversion rate if available.

        Args:
            amount: Amount to convert
            conversion_date: Date for conversion rate lookup
        """
        if amount is None:
            return Decimal("0")

        rate = self.get_conversion_rate_for_date(conversion_date)
        if rate == 0:
            return Decimal("0")

        return Decimal(str(amount)) / rate

    @staticmethod
    def get_default_currency(company):
        """Get the default currency for a company"""
        if not company:
            return None
        try:
            return MultipleCurrency.objects.filter(
                company=company, is_default=True
            ).first()
        except Exception:
            return None

    @staticmethod
    def get_user_currency(user):
        """Get user's preferred currency - falls back to company default"""
        if not user or not user.is_authenticated:
            return None

        if hasattr(user, "currency") and user.currency:
            return user.currency

        if hasattr(user, "company") and user.company:
            return MultipleCurrency.get_default_currency(user.company)

        return None

    def is_default_col(self):
        """Returns the rendered HTML for the is_default column in the list view."""
        total_currencies = MultipleCurrency.objects.count()
        html = render_template(
            "multiple_currency/is_default_col.html",
            {"instance": self, "total_currencies": total_currencies},
        )
        return mark_safe(html)

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("horilla_core:edit_currency", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("horilla_core:delete_currency", kwargs={"pk": self.pk})


class HorillaUser(AbstractUser):
    """
    Represents a custom user profile for the Horilla application, extending Django's AbstractUser.

    This model serves as a replacement for Django's default User model, providing additional fields,
    such as profile image, contact details, and organizational settings.
    Users can set their language, time zone, currency, and formatting preferences to personalize their experience.
    """

    profile = models.ImageField(
        upload_to=upload_path,
        blank=True,
        null=True,
        verbose_name=_("Profile Image"),
    )
    enable_ai = models.BooleanField(
        default=False,
        verbose_name=_("Enable CRM AI"),
        help_text=_("Toggle the AI assistant feature across the system"),
    )
    contact_number = models.CharField(
        max_length=15, blank=True, null=True, verbose_name=_("Contact Number")
    )
    city = models.CharField(max_length=255, verbose_name=_("City"))
    state = models.CharField(max_length=255, verbose_name=_("State/Province"))
    country = CountryField(verbose_name=_("Country"))
    zip_code = models.CharField(max_length=20, verbose_name=_("ZIP/Postal Code"))
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Company"),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_department",
        verbose_name=_("Department"),
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_("Role"),
    )
    language = models.CharField(
        max_length=50,
        choices=settings.LANGUAGES,
        blank=True,
        null=True,
        verbose_name=_(
            "Language",
        ),
    )
    time_zone = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=[(tz, tz) for tz in common_timezones],
        verbose_name=_("Time Zone"),
    )
    currency = models.ForeignKey(
        MultipleCurrency,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_("User's preferred currency for display"),
        verbose_name=_("Preferred Currency"),
        related_name="user_currency",
    )

    time_format = models.CharField(
        max_length=20,
        choices=TIME_FORMAT_CHOICES,
        default="%I:%M:%S %p",
        help_text=_("Select your preferred time format."),
        verbose_name=_("Time Format"),
    )
    date_format = models.CharField(
        max_length=20,
        choices=DATE_FORMAT_CHOICES,
        default="%Y-%m-%d",
        help_text=_("Select your preferred date format."),
        verbose_name=_("Date Format"),
    )
    date_time_format = models.CharField(
        max_length=100,
        choices=DATETIME_FORMAT_CHOICES,
        default="%Y-%m-%d %H:%M:%S",
        help_text=_("Select your preferred date time format."),
        verbose_name=_("Date Time Format"),
    )
    number_grouping = models.CharField(
        max_length=20,
        choices=NUMBER_GROUPING_CHOICES,
        default="0",
        help_text=_("Select your preferred number grouping format."),
        verbose_name=_("Number Grouping"),
    )
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name=_("Created At")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_created",
        verbose_name=_("Created By"),
    )
    updated_at = models.DateTimeField(
        default=timezone.now, verbose_name=_("Updated At")
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_updated",
        verbose_name=_("Updated By"),
    )
    all_objects = UserManager()
    objects = UserManager()

    default_field_permissions = {
        "role": "readonly",
        "department": "readonly",
    }

    class Meta:
        """
        Meta options for the HorillaUser model.
        """

        swappable = "AUTH_USER_MODEL"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        abstract = False
        unique_together = ["company", "username", "role"]

    AbstractUser._meta.get_field("username").verbose_name = _("Username")
    AbstractUser._meta.get_field("first_name").verbose_name = _("First Name")
    AbstractUser._meta.get_field("last_name").verbose_name = _("Last Name")
    AbstractUser._meta.get_field("email").verbose_name = _("Email")
    AbstractUser._meta.get_field("is_superuser").verbose_name = _("Administrator")
    AbstractUser._meta.get_field("is_active").verbose_name = _("Active")

    PROPERTY_LABELS = {"get_avatar_with_name": "Name"}

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_edit_url(self):
        """
        This method to get edit url for user
        """
        return reverse_lazy("horilla_core:user_edit_form", kwargs={"pk": self.pk})

    def get_detail_view_url(self):
        """
        This method to get detail view url for user
        """
        return reverse_lazy("horilla_core:user_detail_view", kwargs={"pk": self.pk})

    def get_change_company_url(self):
        """
        This method to get change company url for user
        """
        return reverse_lazy(
            "horilla_core:user_change_company_form", kwargs={"pk": self.pk}
        )

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.first_name}&background=random"
        return url

    def get_avatar_with_name(self):
        """
        Returns HTML to render profile image and full name (first + last name).
        Safe for export: no file on profile ImageField will not raise.
        """
        try:
            image_url = (
                self.profile.url
                if self.profile and getattr(self.profile, "name", None)
                else self.get_avatar()
            )
        except (ValueError, OSError):
            image_url = self.get_avatar()
        full_name = (f"{self.first_name} {self.last_name}").strip() or getattr(
            self, "username", ""
        )

        return format_html(
            """
            <div class="flex items-center space-x-2">
                <img src="{}" alt="{}" class="w-8 h-8 rounded-full object-cover" />
                <span class="truncate text-sm font-medium text-gray-900 hover:text-primary-600">{}</span>
            </div>
            """,
            image_url,
            full_name,
            full_name,
        )

    def get_full_name(self):
        """
        Returns the user's full name.
        """
        return f"{self.first_name} {self.last_name}".strip()

    def get_delete_url(self):
        """
        This method to get delete url for user
        """
        return reverse_lazy("horilla_core:user_delete_view", kwargs={"pk": self.pk})

    def get_delete_user_from_role(self):
        """
        This method to get delete user from role url for user
        """
        return reverse_lazy(
            "horilla_core:delete_user_from_role", kwargs={"pk": self.pk}
        )

    def has_any_perms(self, perm_list, obj=None):
        """
        Check if user has any permission from the given list.
        If perm_list is empty, return True (no restrictions).
        """

        if self.is_superuser:
            return True

        if not perm_list:
            return True

        if not isinstance(perm_list, Iterable) or isinstance(perm_list, str):
            raise ValueError("perm_list must be an iterable of permissions.")

        return any(self.has_perm(perm, obj) for perm in perm_list)

    def save(self, *args, **kwargs):
        if not self.username and self.email:
            self.username = self.email

        if not self.password and self.contact_number:
            self.password = make_password(self.contact_number)

        super().save(*args, **kwargs)

    def super_user_action_col(self):
        """Returns the HTML for the super_user_action column in the list view with remove icon."""
        superuser_count = self.__class__.objects.filter(is_superuser=True).count()
        html = render_template(
            path="permissions/super_user_action_col.html",
            context={"instance": self, "superuser_count": superuser_count},
        )
        return mark_safe(html)


class HorillaImport(models.Model):
    """
    Horilla Import model for permission management
    """

    class Meta:
        """
        Meta options for the HorillaImport model.
        """

        managed = False
        default_permissions = ()
        permissions = (("can_view_horilla_import", _("Can View Global Import")),)
        verbose_name = _("Global Import")


class HorillaSettings(models.Model):
    """
    Horilla Settings model for permission management
    """

    class Meta:
        """
        Meta options for the HorillaSettings model.
        """

        managed = False
        default_permissions = ()
        permissions = (("can_view_horilla_settings", _("Can View Global Settings")),)
        verbose_name = _("Global Settings")


class HorillaExport(models.Model):
    """
    Horilla Export model for permission management
    """

    class Meta:
        """
        Meta options for the HorillaExport model.
        """

        managed = False
        default_permissions = ()
        permissions = (("can_view_horilla_export", _("Can View Global Export")),)
        verbose_name = _("Global Export")


class HorillaSwitchCompany(models.Model):
    """
    Horilla Switch Company model for permission management
    """

    class Meta:
        """
        Meta options for the HorillaSwitchCompany model.
        """

        managed = False
        default_permissions = ()
        permissions = (("can_switch_company", _("Can Switch Company")),)
        verbose_name = _("Switch Company")


class HorillaAboutSystem(models.Model):
    """
    Horilla About System model for permission management
    """

    class Meta:
        """
        Meta options for the HorillaAboutSystem model.
        """

        managed = False
        default_permissions = ()
        permissions = (("can_view_horilla_about_system", _("Can View About System")),)
        verbose_name = _("About System")


class HorillaUserProfile(models.Model):
    """
    Horilla User Profile model for permission management
    """

    class Meta:
        """
        Meta options for the HorillaUserProfile model.
        """

        managed = False
        default_permissions = ()
        permissions = (
            ("can_view_profile", _("Can View Profile")),
            ("can_change_profile", _("Can Change Profile")),
        )
        verbose_name = _("User Profile")


@permission_exempt_model
class KanbanGroupBy(models.Model):
    """
    Model to store user preferences for grouping in Kanban and Group By views.
    view_type separates settings: 'kanban' for kanban board, 'group_by' for group-by list.
    """

    VIEW_TYPE_CHOICES = [
        ("kanban", _("Kanban")),
        ("group_by", _("Group By")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name=_("Column User"),
        related_name="kanban_column",
    )
    model_name = models.CharField(
        max_length=100,
        help_text=_("Name of the model (e.g., 'User') to group by."),
    )
    app_label = models.CharField(max_length=100)
    view_type = models.CharField(
        max_length=20,
        choices=VIEW_TYPE_CHOICES,
        default="kanban",
        help_text=_("Whether this setting is for Kanban view or Group By view."),
    )
    field_name = models.CharField(
        max_length=100,
        help_text=_(
            "Name of the field that can be used for grouping (ChoiceField or ForeignKey)."
        ),
    )
    all_objects = models.Manager()

    def get_model_groupby_fields(
        self, exclude_fields=None, include_fields=None, user=None
    ):
        """
        Retrieve valid fields for grouping in the selected model.
        When user is provided, excludes fields with 'hidden' (don't show) permission.
        """
        if exclude_fields is None:
            exclude_fields = []
        # Always exclude country from kanban/group_by choices across all models
        exclude_fields = list(exclude_fields) + ["country"]

        try:
            model = apps.get_model(app_label=self.app_label, model_name=self.model_name)
            choices = []

            for field in model._meta.get_fields():
                if field.name in exclude_fields:
                    continue

                if include_fields is not None and field.name not in include_fields:
                    continue

                if isinstance(field, models.CharField) and field.choices:
                    choices.append((field.name, field.verbose_name or field.name))
                elif isinstance(field, models.ForeignKey) and field.name not in (
                    "created_by",
                    "updated_by",
                ):
                    choices.append((field.name, field.verbose_name or field.name))

            if user and choices:
                from horilla_core.utils import filter_hidden_fields

                field_names = [c[0] for c in choices]
                allowed = filter_hidden_fields(user, model, field_names)
                choices = [c for c in choices if c[0] in allowed]

            return choices
        except (LookupError, ValueError) as e:
            logger.error(
                "Error retrieving model groupby fields for %s.%s: %s",
                self.app_label,
                self.model_name,
                e,
            )
            return []

    def clean(self):
        """
        Validate that the field_name is a valid ChoiceField or ForeignKey in the selected model.
        Respects field-level permissions when user is available from request.
        """
        request = getattr(_thread_local, "request", None)
        user = getattr(request, "user", None) if request else None
        choices = self.get_model_groupby_fields(user=user)
        if not self.field_name:
            return

        if not any(self.field_name == choice[0] for choice in choices):
            raise ValidationError(
                f"'{self.field_name}' is not a valid ChoiceField or ForeignKey in model '{self.model_name}'."
            )

    def save(self, *args, **kwargs):
        """
        Run validation before saving.
        Override the unique constraint by deleting existing entries.
        """
        self.clean()
        request = getattr(_thread_local, "request")
        existing = KanbanGroupBy.all_objects.filter(
            model_name=self.model_name,
            app_label=self.app_label,
            user=request.user,
            view_type=self.view_type,
        )

        # Delete them before saving this one
        if existing.exists():
            existing.delete()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.model_name} by {self.field_name}"

    class Meta:
        """
        Meta options for the KanbanGroupBy model.
        """

        unique_together = ("model_name", "app_label", "user", "view_type")


@permission_exempt_model
class ListColumnVisibility(models.Model):
    """
    List Column Visibility model to store user preferences for visible columns in list views.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        default="",
        verbose_name=_("Column User"),
        related_name="list_column",
    )
    model_name = models.CharField(max_length=100)
    app_label = models.CharField(max_length=100)
    url_name = models.CharField(max_length=100)
    visible_fields = models.JSONField(default=list)
    context = models.CharField(max_length=200, blank=True)
    removed_custom_fields = models.JSONField(default=list, blank=True)
    all_objects = models.Manager()

    class Meta:
        """
        Meta options for the ListColumnVisibility model.
        """

        unique_together = ("user", "app_label", "model_name", "context", "url_name")

    @property
    def translated_visible_fields(self):
        """
        Returns the list of visible fields with translations.
        """
        return [_(field) for field in self.visible_fields]

    @property
    def translated_removed_fields(self):
        """
        Returns the list of removed fields with translations.
        """
        return [_(field) for field in self.removed_custom_fields]

    def __str__(self):
        return f"{self.user.username} - {self.app_label}.{self.model_name}"


@permission_exempt_model
class DetailFieldVisibility(models.Model):
    """
    Model to store user preferences for detail view fields.
    Supports two sections: header_fields (summary) and details_fields (Details tab).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name=_("User"),
        related_name="detail_field_visibility",
    )
    model_name = models.CharField(max_length=100)
    app_label = models.CharField(max_length=100)
    url_name = models.CharField(max_length=100, default="")
    header_fields = models.JSONField(default=list)  # [[verbose_name, field_name], ...]
    details_fields = models.JSONField(default=list)  # [[verbose_name, field_name], ...]
    all_objects = models.Manager()

    class Meta:
        unique_together = ("user", "app_label", "model_name", "url_name")

    def __str__(self):
        return f"{self.user.username} - {self.app_label}.{self.model_name} detail"


class RecentlyViewedManager(models.Manager):
    """
    Manager for RecentlyViewed model to handle recently viewed items.
    """

    def add_viewed_item(self, user, obj):
        """Add or update a recently viewed item for a user."""
        content_type = ContentType.objects.get_for_model(obj)
        self.filter(user=user, content_type=content_type, object_id=obj.pk).delete()
        self.create(user=user, content_type=content_type, object_id=obj.pk)
        if self.filter(user=user).count() > 25:
            recent_ids = (
                self.filter(user=user)
                .order_by("-viewed_at")
                .values_list("id", flat=True)[:20]
            )
            self.filter(user=user).exclude(id__in=recent_ids).delete()

    def get_recently_viewed(self, user, model_class=None, limit=20):
        """Get recently viewed items for a user, optionally filtered by model class."""
        queryset = self.filter(user=user).order_by("-viewed_at")
        if model_class:
            content_type = ContentType.objects.get_for_model(model_class)
            queryset = queryset.filter(content_type=content_type)
        return [item.content_object for item in queryset if item.content_object][:limit]


@permission_exempt_model
class RecentlyViewed(models.Model):
    """
    Model to track recently viewed items by users.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recently_viewed_items",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    viewed_at = models.DateTimeField(default=timezone.now)
    all_objects = models.Manager()
    objects = RecentlyViewedManager()

    class Meta:
        """
        Meta options for the RecentlyViewed model.
        """

        indexes = [
            models.Index(fields=["user", "content_type", "object_id"]),
            models.Index(fields=["user", "viewed_at"]),
        ]
        ordering = ["-viewed_at"]

    def __str__(self):
        return f"{self.user} viewed {self.content_object} at {self.viewed_at}"

    def get_app_section_mapping(self):
        """
        Build a mapping of app_label -> section from registered sub_section_menu items.
        """

        app_to_section = {}
        for cls in sub_section_menu:
            obj = cls()
            app_label = getattr(obj, "app_label", None)
            section = getattr(obj, "section", None)
            if app_label and section:
                app_to_section[app_label] = section
        return app_to_section

    def get_detail_url(self):
        """
        Tries to call any method on the related object that starts with 'get_detail_'.
        Appends section query parameter based on the app_label.
        Falls back to '#' if not found.
        """
        if not self.content_object:
            return "#"

        base_url = None
        for attr in dir(self.content_object):
            if attr.startswith("get_detail_"):
                method = getattr(self.content_object, attr)
                if callable(method):
                    try:
                        base_url = method()
                        break
                    except Exception:
                        continue

        if not base_url or base_url == "#":
            return "#"

        app_label = self.content_type.app_label

        app_to_section = self.get_app_section_mapping()
        section = app_to_section.get(app_label)

        if section:
            separator = "&" if "?" in base_url else "?"
            return f"{base_url}{separator}section={section}"

        return base_url


@permission_exempt_model
class SavedFilterList(models.Model):
    """
    Model to store saved filter lists for users.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_filter_lists",
    )
    name = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    filter_params = models.JSONField()
    is_public = models.BooleanField(
        default=False,
        help_text="When set, this filter is available to all users in this list/position.",
    )
    created_at = models.DateTimeField(default=timezone.now)
    all_objects = models.Manager()

    class Meta:
        """
        Meta options for the SavedFilterList model.
        """

        unique_together = ["user", "name", "model_name"]
        indexes = [
            models.Index(fields=["user", "model_name"]),
            models.Index(fields=["model_name", "is_public"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username} - {self.model_name})"

    def get_filter_params(self):
        """
        Returns the filter parameters as a dictionary.
        """
        return self.filter_params


@permission_exempt_model
class PinnedView(models.Model):
    """
    Model to store pinned views for users.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pinned_views"
    )
    model_name = models.CharField(max_length=100)
    view_type = models.CharField(max_length=100)
    pinned_at = models.DateTimeField(auto_now=True)
    all_objects = models.Manager()

    class Meta:
        """
        Meta options for the PinnedView model.
        """

        unique_together = ["user", "model_name"]
        indexes = [models.Index(fields=["user", "model_name"])]


@permission_exempt_model
class ActiveTab(HorillaCoreModel):
    """
    ActiveTab
    """

    path = models.CharField(max_length=256)
    tab_target = models.CharField(max_length=256)


class FiscalYear(HorillaCoreModel):
    """
    Model for managing fiscal year configurations
    """

    fiscal_year_type = models.CharField(
        max_length=20,
        choices=[
            ("standard", _("Standard Fiscal Year")),
            ("custom", _("Custom Fiscal Year")),
        ],
        verbose_name=_("Fiscal Year Type"),
    )
    format_type = models.CharField(
        max_length=20,
        choices=[
            ("year_based", _("Year Based")),
            ("quarter_based", _("Quarter Based")),
        ],
        verbose_name=_("Format"),
        null=True,
        blank=True,
    )
    quarter_based_format = models.CharField(
        max_length=50,
        choices=[
            (
                "4-4-5",
                _(
                    "4-4-5 In each quarter, Period 1 has 4 weeks, Period 2 has 4 weeks, Period 3 has 5 weeks"
                ),
            ),
            (
                "4-5-4",
                _(
                    "4-5-4 In each quarter, Period 1 has 4 weeks, Period 2 has 5 weeks, Period 3 has 4 weeks"
                ),
            ),
            (
                "5-4-4",
                _(
                    "5-4-4 In each quarter, Period 1 has 5 weeks, Period 2 has 4 weeks, Period 3 has 4 weeks"
                ),
            ),
        ],
        blank=True,
        null=True,
        verbose_name=_("Quarter Based Format"),
    )
    year_based_format = models.CharField(
        max_length=50,
        choices=[
            (
                "3-3-3-4",
                _(
                    "3-3-3-4 Quarter 1 has 3 Periods, Quarter 2 has 3 Periods, Quarter 3 has 3 Periods, Quarter 4 has 4 Periods"
                ),
            ),
            (
                "3-3-4-3",
                _(
                    "3-3-4-3 Quarter 1 has 3 Periods, Quarter 2 has 3 Periods, Quarter 3 has 4 Periods, Quarter 4 has 3 Periods"
                ),
            ),
            (
                "3-4-3-3",
                _(
                    "3-4-3-3 Quarter 1 has 3 Periods, Quarter 2 has 4 Periods, Quarter 3 has 3 Periods, Quarter 4 has 3 Periods"
                ),
            ),
            (
                "4-3-3-3",
                _(
                    "4-3-3-3 Quarter 1 has 4 Periods, Quarter 2 has 3 Periods, Quarter 3 has 3 Periods, Quarter 4 has 3 Periods"
                ),
            ),
        ],
        blank=True,
        null=True,
        verbose_name=_("Year Based Format"),
    )

    start_date_month = models.CharField(
        max_length=20,
        choices=MONTH_CHOICES,
        verbose_name=_("Start Date Month"),
    )
    start_date_day = models.PositiveIntegerField(
        default=1, verbose_name=_("Start Date Day")
    )
    week_start_day = models.CharField(
        max_length=20,
        choices=DAY_CHOICES,
        verbose_name=_("Week Start Day"),
        blank=True,
        null=True,
    )
    display_year_based_on = models.CharField(
        max_length=20,
        choices=[
            ("starting_year", _("Starting Year")),
            ("ending_year", _("Ending Year")),
        ],
        verbose_name=_("Display Fiscal Year Based On"),
        default="starting_year",
    )
    number_weeks_by = models.CharField(
        max_length=20,
        choices=[
            ("year", _("Year")),
            ("quarter", _("Quarter")),
            ("period", _("Period")),
        ],
        verbose_name=_("Number Weeks By"),
        blank=True,
        null=True,
    )
    period_display_option = models.CharField(
        max_length=20,
        choices=[
            ("number_by_year", _("Number by Year")),
            ("number_by_quarter", _("Number by Quarter")),
        ],
        verbose_name=_("Period Display Option"),
        blank=True,
        null=True,
    )

    def get_month_ranges(self):
        """Calculate month ranges for quarters based on start_date_month"""
        if not self.start_date_month:
            return []

        months = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]
        start_index = months.index(self.start_date_month)
        quarter_ranges = []

        for _i in range(4):
            quarter_start = months[start_index % 12]
            quarter_end = months[(start_index + 2) % 12]
            quarter_ranges.append(
                f"{quarter_start.capitalize()} - {quarter_end.capitalize()}"
            )
            start_index = (start_index + 3) % 12

        return quarter_ranges

    def get_periods_by_format(self):
        """
        Return periods per year and per quarter based on the selected format.
        This is now the single source of truth for all period calculations.
        """
        base_config = {
            "number_weeks_by": self.number_weeks_by,
            "period_display_option": self.period_display_option,
            "month_ranges": self.get_month_ranges() if self.start_date_month else [],
        }

        if self.fiscal_year_type == "standard":
            return {
                "periods_per_year": 12,
                "quarter_1_periods": 3,
                "quarter_2_periods": 3,
                "quarter_3_periods": 3,
                "quarter_4_periods": 3,
                "weeks_per_period": 4,
                **base_config,
            }
        if (
            self.fiscal_year_type == "custom"
            and self.format_type == "year_based"
            and self.year_based_format
        ):
            periods = self.year_based_format.split("-")
            periods = [int(p) for p in periods]
            total_periods = sum(periods)

            return {
                "periods_per_year": total_periods,
                "quarter_1_periods": periods[0],
                "quarter_2_periods": periods[1],
                "quarter_3_periods": periods[2],
                "quarter_4_periods": periods[3],
                "weeks_per_period": 4,
                **base_config,
            }
        if (
            self.fiscal_year_type == "custom"
            and self.format_type == "quarter_based"
            and self.quarter_based_format
        ):
            weeks = self.quarter_based_format.split("-")
            weeks = [int(w) for w in weeks]

            return {
                # Always 12 for quarter-based (3 per quarter)
                "periods_per_year": 12,
                "quarter_1_periods": 3,
                "quarter_2_periods": 3,
                "quarter_3_periods": 3,
                "quarter_4_periods": 3,
                "weeks_per_period_pattern": weeks,
                "total_weeks_per_quarter": sum(weeks),
                **base_config,
            }

        # Fallback to standard if no specific format
        return {
            "periods_per_year": 12,
            "quarter_1_periods": 3,
            "quarter_2_periods": 3,
            "quarter_3_periods": 3,
            "quarter_4_periods": 3,
            "weeks_per_period": 4,
            **base_config,
        }

    def save(self, *args, **kwargs):
        """Override save to handle format-specific logic"""
        if self.fiscal_year_type == "standard":
            # Clear custom format fields for standard type
            self.format_type = None
            self.year_based_format = None
            self.quarter_based_format = None
            self.week_start_day = None
            self.number_weeks_by = None
            self.period_display_option = None
            if not self.start_date_day:
                self.start_date_day = 1

        super().save(*args, **kwargs)

    def __str__(self):
        current_year = datetime.now().year
        return f"{self.get_start_date_month_display()} {self.start_date_day} - {current_year}"

    class Meta:
        """
        Meta options for the FiscalYear model.
        """

        verbose_name = _("Fiscal Year")
        verbose_name_plural = _("Fiscal Years")
        constraints = [
            models.UniqueConstraint(
                fields=["company"], name="unique_fiscal_year_per_company"
            )
        ]


class FiscalYearInstance(HorillaCoreModel):
    """
    Represents an actual fiscal year instance based on configuration
    """

    fiscal_year_config = models.ForeignKey(
        FiscalYear,
        on_delete=models.CASCADE,
        related_name="year_instances",
        verbose_name=_("Fiscal Year Configuration"),
    )
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))
    name = models.CharField(max_length=100, verbose_name=_("Fiscal Year Name"))
    is_current = models.BooleanField(default=False, verbose_name=_("Is Current"))

    def __str__(self):
        return str(self.name)

    class Meta:
        """
        Meta options for the FiscalYearInstance model.
        """

        verbose_name = _("Fiscal Year Instance")
        verbose_name_plural = _("Fiscal Year Instances")


class Quarter(HorillaCoreModel):
    """
    Represents a quarter within a fiscal year
    """

    fiscal_year = models.ForeignKey(
        FiscalYearInstance,
        on_delete=models.CASCADE,
        related_name="quarters",
        verbose_name=_("Fiscal Year"),
    )
    name = models.CharField(max_length=100, verbose_name=_("Quarter Name"))
    quarter_number = models.PositiveIntegerField(verbose_name=_("Quarter Number"))
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))
    is_current = models.BooleanField(default=False, verbose_name=_("Is Current"))

    def __str__(self):
        return f"{self.fiscal_year.name} - {self.name}"

    class Meta:
        """
        Meta options for the Quarter model.
        """

        verbose_name = _("Quarter")
        verbose_name_plural = _("Quarters")


class Period(HorillaCoreModel):
    """
    Represents a period within a quarter
    """

    quarter = models.ForeignKey(
        Quarter,
        on_delete=models.CASCADE,
        related_name="periods",
        verbose_name=_("Quarter"),
    )
    name = models.CharField(max_length=100, verbose_name=_("Period Name"))
    period_number = models.PositiveIntegerField(verbose_name=_("Period Number"))
    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))
    is_current = models.BooleanField(default=False, verbose_name=_("Is Current"))

    def get_period_number_in_quarter(self):
        """
        Calculate the period number within the quarter dynamically
        """
        periods_in_quarter = Period.objects.filter(quarter=self.quarter).order_by(
            "period_number"
        )

        for index, period in enumerate(periods_in_quarter, 1):
            if period.id == self.id:
                return index
        return 1  # Fallback

    def get_display_period_number(self):
        """
        Get the period number based on the fiscal year's period_display_option
        """
        fiscal_config = self.quarter.fiscal_year.fiscal_year_config

        if fiscal_config.period_display_option == "number_by_quarter":
            return self.get_period_number_in_quarter()

        return self.period_number

    def save(self, *args, **kwargs):
        """
        Override save to set period number and dates based on fiscal year type.
        Period numbers start from 1 for each fiscal year.
        """
        # Skip auto-calculation if period_number is already set (e.g., from service)
        skip_auto_calculation = kwargs.pop("skip_auto_calculation", False)

        if (
            not self.pk and not skip_auto_calculation
        ):  # Only for new instances without explicit number
            fiscal_config = self.quarter.fiscal_year.fiscal_year_config

            if fiscal_config.fiscal_year_type == "standard":
                # For standard type, create periods based on calendar months
                self._create_standard_period()
            else:
                # For custom type, use the existing logic
                self._create_custom_period()

        super().save(*args, **kwargs)

        # Update name after saving (when we have an ID)
        if not hasattr(self, "_name_updated"):
            self._update_period_name()

    def _create_standard_period(self):
        """
        Create period for standard fiscal year type based on calendar months.
        Period numbers start from 1 for each fiscal year.
        """

        fiscal_config = self.quarter.fiscal_year.fiscal_year_config
        fiscal_year = self.quarter.fiscal_year

        # Calculate period number within THIS fiscal year only
        existing_periods_in_year = Period.objects.filter(
            quarter__fiscal_year=fiscal_year
        ).count()

        self.period_number = existing_periods_in_year + 1

        # Get the start month index
        months = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ]
        start_month_index = months.index(fiscal_config.start_date_month.lower())

        # Calculate the month for this period
        period_month_index = (start_month_index + self.period_number - 1) % 12

        # Determine the year for this period
        if period_month_index < start_month_index:
            # We've crossed into the next calendar year
            period_year = fiscal_year.start_date.year + 1
        else:
            period_year = fiscal_year.start_date.year

        # Set start date to first day of the month
        self.start_date = datetime(
            year=period_year,
            month=period_month_index + 1,
            day=fiscal_config.start_date_day,
        ).date()

        # Set end date to last day of the month
        next_month = self.start_date + relativedelta(months=1)
        self.end_date = next_month - timedelta(days=1)

        # Set period name as month name
        self.name = f"{months[period_month_index].capitalize()} {period_year}"

    def _create_custom_period(self):
        """
        Create period for custom fiscal year type.
        Period numbers start from 1 for each fiscal year.
        """
        _fiscal_config = self.quarter.fiscal_year.fiscal_year_config

        # Only count periods in previous quarters within THIS fiscal year
        previous_quarters = Quarter.objects.filter(
            fiscal_year=self.quarter.fiscal_year,
            quarter_number__lt=self.quarter.quarter_number,
        )

        periods_before_this_quarter = Period.objects.filter(
            quarter__in=previous_quarters
        ).count()

        # Count existing periods in current quarter
        existing_periods_in_current_quarter = Period.objects.filter(
            quarter=self.quarter
        ).count()

        # Period number within the fiscal year (starts from 1)
        self.period_number = (
            periods_before_this_quarter + existing_periods_in_current_quarter + 1
        )

    def _update_period_name(self):
        """
        Update period name based on fiscal year type and display option
        """
        fiscal_config = self.quarter.fiscal_year.fiscal_year_config

        if fiscal_config.fiscal_year_type == "standard":
            # For standard type, name is already set in _create_standard_period
            return

        # For custom type, use period numbering
        if fiscal_config.period_display_option == "number_by_quarter":
            new_name = f"Period {self.get_period_number_in_quarter()}"
        else:  # 'number_by_year' or default
            new_name = f"Period {self.period_number}"

        if self.name != new_name:
            self.name = new_name
            self._name_updated = True
            super().save(update_fields=["name"])

    def __str__(self):
        fiscal_config = self.quarter.fiscal_year.fiscal_year_config
        display_number = self.get_display_period_number()

        if fiscal_config.period_display_option == "number_by_quarter":
            return f"{self.quarter.fiscal_year.name} - {self.quarter.name} - Period {display_number}"

        return f"{self.quarter.fiscal_year.name} - Period {display_number}"

    class Meta:
        """
        Meta options for the Period model.
        """

        verbose_name = _("Period")
        verbose_name_plural = _("Periods")


class Holiday(HorillaCoreModel):
    """
    Holiday model for managing company holidays
    """

    FREQUENCY_CHOICES = [
        ("weekly", _("Weekly")),
        ("monthly", _("Monthly")),
        ("yearly", _("Yearly")),
    ]

    MONTHLY_REPEAT_CHOICES = [
        ("day_of_month", _("On Day")),
        ("weekday_of_month", _("On the")),
    ]

    YEARLY_REPEAT_CHOICES = [
        ("day_of_month", _("On every")),  # e.g., July 14th
        ("weekday_of_month", _("On the")),  # e.g., 2nd Monday of July
    ]

    name = models.CharField(max_length=255, verbose_name=_("Holiday Name"))
    start_date = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Start Date")
    )
    end_date = models.DateTimeField(null=True, blank=True, verbose_name=_("End Date"))

    all_users = models.BooleanField(default=False, verbose_name=_("All Users"))
    specific_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="holidays",
        verbose_name=_("Specific Users"),
    )

    is_recurring = models.BooleanField(default=False, verbose_name=_("Recurring"))
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("Holiday Frequency"),
    )

    recurs_every_weeks = models.PositiveIntegerField(
        default=1, blank=True, null=True, verbose_name=_("Recurs Every (weeks)")
    )
    weekly_days = MultiSelectField(
        choices=DAY_CHOICES, blank=True, verbose_name=_("Weekly Days")
    )

    monthly_repeat_type = models.CharField(
        max_length=20,
        choices=MONTHLY_REPEAT_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("Monthly Repeat Type"),
    )
    monthly_day_of_month = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Day of Month")
    )
    monthly_interval = models.PositiveIntegerField(
        default=1, blank=True, null=True, verbose_name=_("Monthly Interval")
    )
    monthly_day_of_week = models.CharField(
        max_length=10,
        choices=DAY_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("Day of Week"),
    )
    monthly_week_of_month = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Week of Month")
    )

    yearly_repeat_type = models.CharField(
        max_length=20,
        choices=YEARLY_REPEAT_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("Yearly Repeat Type"),
    )
    yearly_week_of_month = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Week of Month")
    )
    yearly_day_of_month = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Day of Month")
    )
    yearly_day_of_week = models.CharField(
        max_length=10,
        choices=DAY_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("Day of Week"),
    )
    yearly_month = models.CharField(
        max_length=15,
        choices=MONTH_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("Month"),
    )

    OWNER_FIELDS = ["specific_users"]

    class Meta:
        """
        Meta options for the Holiday model.
        """

        verbose_name = _("Holiday")
        verbose_name_plural = _("Holidays")
        ordering = ["-start_date"]

    def __str__(self):
        return str(self.name)

    def clean(self):
        """
        Validate holiday data
        """

        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError(_("Start date cannot be after end date"))

        if self.is_recurring and not self.frequency:
            raise ValidationError(_("Frequency is required for recurring holidays"))

        if self.frequency == "weekly":
            if not self.weekly_days:
                raise ValidationError(
                    _("Weekly days must be specified for weekly recurrence")
                )
            if self.recurs_every_weeks < 1:
                raise ValidationError(_("Recurs every weeks must be at least 1"))

        if self.frequency == "monthly":
            if self.monthly_repeat_type == "day_of_month":
                if not self.monthly_day_of_month:
                    raise ValidationError(
                        _("Day of month is required for monthly recurrence")
                    )
            elif self.monthly_repeat_type == "weekday_of_month":
                if not (self.monthly_day_of_week and self.monthly_week_of_month):
                    raise ValidationError(
                        _(
                            "Both day of week and week of month are required for monthly recurrence"
                        )
                    )
            else:
                raise ValidationError(_("Please select a valid monthly repeat type"))

        if self.frequency == "yearly":
            if not self.yearly_month:
                raise ValidationError(_("Month is required for yearly recurrence"))

            if self.yearly_repeat_type == "day_of_month":
                if not self.yearly_day_of_month:
                    raise ValidationError(
                        _("Day of month is required for yearly recurrence")
                    )
            elif self.yearly_repeat_type == "weekday_of_month":
                if not (self.yearly_day_of_week and self.yearly_week_of_month):
                    raise ValidationError(
                        _(
                            "Both week of month and day of week are required for yearly recurrence"
                        )
                    )
            else:
                raise ValidationError(_("Please select a valid yearly repeat type"))

    def save(self, *args, **kwargs):
        """
        Override save to perform validation
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.name}&background=random"
        return url

    def get_edit_url(self):
        """
        Get the URL for editing the holiday
        """
        return reverse_lazy("horilla_core:holiday_update_form", kwargs={"pk": self.pk})

    def get_detail_url(self):
        """
        Get the URL for holiday detail view
        """
        return reverse_lazy("horilla_core:holiday_detail_view", kwargs={"pk": self.pk})

    def get_user_detail_url(self):
        """
        Get the URL for holiday detail view for users
        """
        return reverse_lazy("horilla_core:user_holiday_detail", kwargs={"pk": self.pk})

    def detail_view_actions(self):
        """
        method for rendering detail view action
        """

        return render_template(
            path="holidays/detail_view_actions.html",
            context={"instance": self},
        )

    def get_delete_url(self):
        """
        Get the URL for deleting the holiday
        """
        return reverse_lazy("horilla_core:holiday_delete_view", kwargs={"pk": self.pk})

    def specific_users_enable(self):
        """
        Return comma-separated employee names if specific users are enabled,
        otherwise return 'All users are enabled'
        """
        if self.all_users:
            return "All users are included"
        specific_users_qs = self.specific_users.all()
        if specific_users_qs is not None and specific_users_qs.exists():
            # Ensure each user has a valid string representation
            user_names = [str(user) for user in specific_users_qs if str(user).strip()]
            if user_names:
                return ", ".join(user_names)
            return "No valid user names found"
        return "No Users specified"

    def holiday_type(self):
        """
        Return comma-separated employee names if specific users are enabled,
        otherwise return 'All users are enabled'
        """
        if self.all_users:
            return "Company Holiday"
        specific_users_qs = self.specific_users.all()
        if specific_users_qs is not None and specific_users_qs.exists():
            # Ensure each user has a valid string representation
            user_names = [str(user) for user in specific_users_qs if str(user).strip()]
            if user_names:
                return "Personal Holiday"
            return "No valid user names found"
        return "No Users specified"

    def get_ordinal_number(self, number):
        """
        Convert number to ordinal (1st, 2nd, 3rd, etc.)
        """
        ordinals = {
            1: _("1st"),
            2: _("2nd"),
            3: _("3rd"),
            4: _("4th"),
            5: _("5th"),
        }
        return ordinals.get(number, f"{number}th")

    def is_recurring_holiday(self):
        """
        Return a human-readable string describing the recurring holiday pattern.
        """
        if not self.is_recurring or not self.frequency:
            return "Not a recurring holiday"

        # WEEKLY
        if self.frequency == "weekly" and self.weekly_days:
            day_map = dict(DAY_CHOICES)
            days = ", ".join(day_map[day] for day in self.weekly_days)

            return f"Recur every {self.recurs_every_weeks or 1} week on {days}"

        # MONTHLY
        if self.frequency == "monthly" and self.monthly_repeat_type:
            if self.monthly_repeat_type == "day_of_month":
                return (
                    f"Recur on {self.get_ordinal_number(self.monthly_day_of_month)} day "
                    f"of every {self.monthly_interval or 1} month"
                )
            if self.monthly_repeat_type == "weekday_of_month":
                return (
                    f"Recur on the {self.get_ordinal_number(self.monthly_week_of_month)} "
                    f"{self.monthly_day_of_week.capitalize()} of every {self.monthly_interval or 1} month"
                )

        # YEARLY
        if self.frequency == "yearly" and self.yearly_repeat_type:
            if self.yearly_repeat_type == "day_of_month":
                return (
                    f"Recur on every {self.yearly_month.capitalize()} "
                    f"{self.get_ordinal_number(self.yearly_day_of_month)}"
                )
            if self.yearly_repeat_type == "weekday_of_month":
                return (
                    f"Recur on the {self.get_ordinal_number(self.yearly_week_of_month)} "
                    f"{self.yearly_day_of_week.capitalize()} of {self.yearly_month.capitalize()}"
                )

        return "Not a recurring holiday"

    def get_eligible_users(self):
        """
        Get all users eligible for this holiday
        """
        from horilla.auth.models import User

        if self.all_users:
            return User.objects.filter(is_active=True)
        return self.specific_users.all()

    def is_user_eligible(self, user):
        """
        Check if a specific user is eligible for this holiday
        """
        if self.all_users:
            return user.is_active
        return self.specific_users.filter(pk=user.pk).exists()

    def get_recurrence_description(self):
        """
        Get human-readable description of recurrence pattern
        """
        if not self.is_recurring:
            return _("One-time holiday")

        if self.frequency == "weekly":
            days = ", ".join([dict(DAY_CHOICES)[day] for day in self.weekly_days])
            if self.recurs_every_weeks == 1:
                return _("Weekly on {}").format(days)

            return _("Every {} weeks on {}").format(self.recurs_every_weeks, days)

        if self.frequency == "monthly":
            if self.monthly_day_of_month:
                if self.monthly_interval == 1:
                    return _("Monthly on day {}").format(self.monthly_day_of_month)
                return _("Every {} months on day {}").format(
                    self.monthly_interval, self.monthly_day_of_month
                )

            day_name = dict(DAY_CHOICES)[self.monthly_day_of_week]
            ordinal = self.get_ordinal_number(self.monthly_week_of_month)
            if self.monthly_interval == 1:
                return _("Monthly on {} {} of month").format(ordinal, day_name)

            return _("Every {} months on {} {} of month").format(
                self.monthly_interval, ordinal, day_name
            )

        if self.frequency == "yearly":
            month_name = dict(self.MONTH_CHOICES)[self.yearly_month]
            if self.yearly_day_of_month:
                return _("Yearly on {} {}").format(month_name, self.yearly_day_of_month)

            day_name = dict(DAY_CHOICES)[self.yearly_day_of_week]
            ordinal = self.get_ordinal_number(self.yearly_week_of_month)
            return _("Yearly on {} {} of {}").format(ordinal, day_name, month_name)

        return _("Custom recurrence")

    @property
    def duration_days(self):
        """
        Calculate the duration of the holiday in days
        """
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0


class DatedConversionRate(HorillaCoreModel):
    """
    Model to store dated conversion rates for a currency and company.
    """

    currency = models.ForeignKey(
        MultipleCurrency,
        on_delete=models.CASCADE,
        related_name="dated_conversion_rates",
        verbose_name=_("Currency"),
    )
    conversion_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text=_("Conversion rate from default currency"),
        verbose_name=_("Conversion Rate"),
    )
    start_date = models.DateField(
        verbose_name=_("Start Date"),
        help_text=_("The date from which this conversion rate is effective"),
    )

    class Meta:
        """
        Meta options for the DatedConversionRate model.
        """

        verbose_name = _("Dated Conversion Rate")
        verbose_name_plural = _("Dated Conversion Rates")
        unique_together = (
            "company",
            "currency",
            "start_date",
        )  # Prevent duplicate rates for same currency and date
        ordering = ["currency", "start_date"]

    def __str__(self):
        return f"{self.currency} - {self.conversion_rate} from {self.start_date}"

    def get_end_date(self):
        """
        Returns the end date for this rate, which is the start date of the next rate for the same currency and company,
        or None if this is the latest rate.
        """
        next_rate = (
            DatedConversionRate.objects.filter(
                company=self.company,
                currency=self.currency,
                start_date__gt=self.start_date,
            )
            .order_by("start_date")
            .first()
        )
        return next_rate.start_date if next_rate else None

    def save(self, *args, **kwargs):
        """
        Validate that the start_date doesn't overlap inappropriately.
        """
        # Check for existing rates with same currency and company
        existing_rates = DatedConversionRate.objects.filter(
            company=self.company, currency=self.currency
        ).exclude(pk=self.pk)

        for rate in existing_rates:
            if rate.start_date == self.start_date:
                raise ValueError(
                    f"A conversion rate for {self.currency} already exists on {self.start_date}."
                )

        super().save(*args, **kwargs)


class BusinessHourDayMixin(models.Model):
    """
    Model to add start and end time fields for each day of the week.
    """

    monday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Monday Start Time")
    )
    monday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Monday End Time")
    )

    tuesday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Tuesday Start Time")
    )
    tuesday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Tuesday End Time")
    )

    wednesday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Wednesday Start Time")
    )
    wednesday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Wednesday End Time")
    )

    thursday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Thursday Start Time")
    )
    thursday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Thursday End Time")
    )

    friday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Friday Start Time")
    )
    friday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Friday End Time")
    )

    saturday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Saturday Start Time")
    )
    saturday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Saturday End Time")
    )

    sunday_start = models.TimeField(
        null=True, blank=True, verbose_name=_("Sunday Start Time")
    )
    sunday_end = models.TimeField(
        null=True, blank=True, verbose_name=_("Sunday End Time")
    )

    class Meta:
        """
        Abstract model for business hour day model.
        """

        abstract = True


class BusinessHour(BusinessHourDayMixin, HorillaCoreModel):
    """
    Model to handle business hours with support for:
    - 24/7 operations
    - Weekdays only (Mon-Fri)
    - Custom hours with different times per day
    """

    BUSINESS_HOUR_TYPES = [
        ("24_7", _("24 Hours x 7 days")),
        ("24_5", _("24 Hours x 5 days")),
        ("custom", _("Custom Hours")),
    ]

    TIMING_CHOICES = [
        ("same", _("Same Hour Every Day")),
        ("different", _("Different Hour Per Day")),
    ]

    DAY_LABELS = {
        "mon": _("Monday"),
        "tue": _("Tuesday"),
        "wed": _("Wednesday"),
        "thu": _("Thursday"),
        "fri": _("Friday"),
        "sat": _("Saturday"),
        "sun": _("Sunday"),
    }

    WEEK_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    # Basic Information
    name = models.CharField(
        max_length=255, help_text=_("Business Hour Name"), verbose_name=_("Name")
    )
    time_zone = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=[(tz, tz) for tz in common_timezones],
        verbose_name=_("Time Zone"),
    )

    # Business Hour Type
    business_hour_type = models.CharField(
        max_length=10,
        choices=BUSINESS_HOUR_TYPES,
        default="24_7",
        help_text=_("Type of business hours"),
        verbose_name=_("Business Hour Type"),
    )

    # Week Configuration
    week_start_day = models.CharField(
        max_length=10,
        choices=DAY_CHOICES,
        default="monday",
        help_text=_("Week Start Day"),
        verbose_name=_("Week Start Day"),
    )
    week_days = MultiSelectField(choices=DAY_CHOICES, blank=True)

    # Timing Configuration (for custom hours)
    timing_type = models.CharField(
        max_length=10,
        choices=TIMING_CHOICES,
        default="same",
        blank=True,
        null=True,
        help_text=_("Same hours every day or different hours per day"),
        verbose_name=_("Timing Type"),
    )

    # For "Same Hour Every Day"
    default_start_time = models.TimeField(
        null=True,
        blank=True,
        help_text=_("Default start time"),
        verbose_name=_("Default Start Time"),
    )
    default_end_time = models.TimeField(
        null=True,
        blank=True,
        help_text=_("Default end time"),
        verbose_name=_("Default End Time"),
    )

    # Status
    is_default = models.BooleanField(
        default=False,
        help_text=_("Default Business Hour"),
        verbose_name=_("Is Default"),
    )

    class Meta:
        """
        Meta options for the BusinessHour model.
        """

        verbose_name = _("Business Hour")
        verbose_name_plural = _("Business Hours")
        ordering = ["-is_default", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_business_hour_type_display()})"

    def save(self, *args, **kwargs):
        if self.is_default:
            BusinessHour.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)

    def get_active_days(self):
        """
        Returns a list of days with defined business hours.
        """
        days = []
        for day in [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]:
            if getattr(self, f"{day}_start") or getattr(self, f"{day}_24hr"):
                days.append(day.capitalize())
        return days

    def get_avatar(self):
        """
        Method will retun the api to the avatar or path to the profile image
        """
        url = f"https://ui-avatars.com/api/?name={self.name}&background=random"
        return url

    def get_edit_url(self):
        """
        Get the URL for editing the business hour
        """
        return reverse_lazy(
            "horilla_core:business_hour_update_form", kwargs={"pk": self.pk}
        )

    def is_default_hour(self):
        """
        Return Yes/No for default business hour
        """
        return "Yes" if self.is_default else "No"

    def get_delete_url(self):
        """
        Get the URL for deleting the business hour
        """
        return reverse_lazy(
            "horilla_core:business_hour_delete_view", kwargs={"pk": self.pk}
        )

    def get_detail_url(self):
        """
        Get the URL for business hour detail view
        """
        return reverse_lazy(
            "horilla_core:business_hour_detail_view", kwargs={"pk": self.pk}
        )

    def get_formatted_week_days(self):
        """
        Returns a formatted HTML representation of the business hours.
        """

        def format_time(value):
            if not value:
                return "--:--"
            return time_format(value, "P")

        raw_week_days = self.week_days
        if isinstance(raw_week_days, (list, tuple)):
            selected = list(raw_week_days)
        elif isinstance(raw_week_days, str) and raw_week_days.strip():
            selected = [
                p.strip() for p in raw_week_days.replace(",", " ").split() if p.strip()
            ]
        else:
            selected = []

        # 24/7
        if self.business_hour_type == "24_7":
            return mark_safe("Monday - Sunday<br><strong>(24 Hours)</strong>")

        # 24/5
        if self.business_hour_type == "24_5":
            selected_set = set(selected) if selected else set(self.WEEK_ORDER[:5])

            if selected_set == set(self.WEEK_ORDER[:5]):
                return mark_safe(
                    "<span style='white-space: nowrap;'>"
                    "Monday – Friday"
                    "<span style='font-weight:bold;'> (24 Hours)</span>"
                    "</span>"
                )

            if selected_set == set(self.WEEK_ORDER):
                return mark_safe(
                    "<span style='white-space: nowrap;'>"
                    "Monday – Sunday"
                    "<span style='font-weight:bold;'> (24 Hours)</span>"
                    "</span>"
                )

            selected_labels = [
                self.DAY_LABELS[d] for d in self.WEEK_ORDER if d in selected_set
            ]

            return mark_safe(
                "<span style='white-space: nowrap;'>"
                f"{', '.join(selected_labels)}"
                "<span style='font-weight:bold;'> (24 Hours)</span>"
                "</span>"
            )

        # CUSTOM
        if self.business_hour_type == "custom":
            if self.timing_type == "same":
                start = format_time(self.default_start_time)
                end = format_time(self.default_end_time)
                labels = [self.DAY_LABELS[d] for d in self.WEEK_ORDER if d in selected]

                if labels:
                    if labels == [self.DAY_LABELS[d] for d in self.WEEK_ORDER[:5]]:
                        return mark_safe(
                            f"Monday - Friday<br><strong>({start} – {end})</strong>"
                        )
                    if labels == [self.DAY_LABELS[d] for d in self.WEEK_ORDER]:
                        return mark_safe(
                            f"Monday - Sunday<br><strong>({start} – {end})</strong>"
                        )
                    days = ", ".join(labels)
                    return mark_safe(f"{days}<br><strong>({start} – {end})</strong>")

                return mark_safe(f"{start} – {end}")

            if self.timing_type == "different":
                rows = []
                for day_code in self.WEEK_ORDER:
                    day_label = self.DAY_LABELS[day_code]
                    is_open = day_code in selected
                    prefix = day_label.lower()

                    if is_open:
                        start_val = getattr(self, f"{prefix}_start", None)
                        end_val = getattr(self, f"{prefix}_end", None)

                        from datetime import time

                        is_midnight = lambda t: t is None or t == time(0, 0)

                        if is_midnight(start_val) and is_midnight(end_val):
                            time_range = "Closed"
                        else:
                            time_range = (
                                f"{format_time(start_val)} – {format_time(end_val)}"
                            )
                    else:
                        time_range = "Closed"

                    row = (
                        f'<tr class="text-sm">'
                        f'<td class="pr-4 text-gray-600 whitespace-nowrap w-24 mb-5">{day_label}</td>'
                        f'<td class="font-semibold text-black whitespace-nowrap">{time_range}</td>'
                        f"</tr>"
                    )
                    rows.append(row)

                return mark_safe(
                    f'<table class="text-left align-top space-y-1">{"".join(rows)}</table>'
                )

        return mark_safe("—")


class RecycleBin(models.Model):
    """
    Model to store soft-deleted records with their serialized data.
    """

    model_name = models.CharField(max_length=255)
    record_id = models.CharField(max_length=255)
    data = models.TextField()
    deleted_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Deleted At"))
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recycle_delete",
    )
    company = models.ForeignKey(
        "Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Company"),
    )
    objects = CompanyFilteredManager()

    class Meta:
        """
        Meta options for the RecycleBin model.
        """

        verbose_name = _("Recycle Bin")
        verbose_name_plural = _("Recycle Bin")

    def __str__(self):
        return f"{self.model_name} ({self.record_id}) - Deleted at {self.deleted_at}"

    def get_model_display_name(self):
        """
        Returns just the model name in a human-readable format
        """
        model_part = self.model_name.split(".")[-1]

        return "".join(word.title() for word in model_part.split("_"))

    def record_name(self):
        """
        Returns a display-friendly name for the deleted object,
        extracted from the serialized JSON data.
        """

        data = json.loads(self.data)

        if "__str__" in data and data["__str__"]:
            return data["__str__"]
        return None

    def get_delete_url(self):
        """
        this method to get delete url
        """
        return reverse_lazy("horilla_core:recycle_bin_delete", kwargs={"pk": self.pk})

    def get_restore_url(self):
        """
        this method to get delete url
        """
        return reverse_lazy("horilla_core:recycle_bin_restore", kwargs={"pk": self.pk})

    def serialize_data(self, obj):
        """
        Serialize the object data to JSON, handling non-serializable types.
        """

        data = {}
        try:
            data["__str__"] = str(obj)
        except Exception:
            data["__str__"] = None

        for field in obj._meta.fields:
            if field.name in ["id"]:
                continue
            value = getattr(obj, field.name, None)

            if value is not None:
                if isinstance(value, (datetime, date)):
                    value = value.isoformat()
                elif field.is_relation:
                    value = value.pk if value else None
                elif isinstance(value, (bytes, bytearray)):
                    value = value.decode("utf-8", errors="ignore")
                elif not isinstance(value, (str, int, float, bool, type(None))):
                    value = str(value)
                data[field.name] = value
            else:
                data[field.name] = None
        self.data = json.dumps(data)

    @classmethod
    def create_from_instance(cls, instance, user=None):
        """
        Create a soft-deleted record from a model instance.
        """
        soft_record = cls(
            model_name=f"{instance._meta.app_label}.{instance._meta.model_name}",
            record_id=str(instance.pk),
            deleted_by=user,
        )
        soft_record.serialize_data(instance)
        request = getattr(_thread_local, "request", None)
        soft_record.company = getattr(request, "active_company", None)

        soft_record.save()
        return soft_record


class RecycleBinPolicy(models.Model):
    """
    Model to store retention policy for RecycleBin records per company.
    """

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="recycle_bin_policy",
        verbose_name=_("Company"),
    )
    retention_days = models.PositiveIntegerField(
        default=30, verbose_name=_("Retention Period (Days)")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    objects = CompanyFilteredManager()

    class Meta:
        """
        Meta options for the RecycleBinPolicy model.
        """

        verbose_name = _("Recycle Bin Policy")
        verbose_name_plural = _("Recycle Bin Policies")

    def save(self, *args, **kwargs):
        request = getattr(_thread_local, "request", None)
        self.company = getattr(request, "active_company", None)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company.name} - {self.retention_days} days"

    def is_expired(self, deleted_at):
        """
        Check if a deleted_at timestamp exceeds the retention period.
        """

        retention_period = timezone.now() - timezone.timedelta(days=self.retention_days)
        return deleted_at < retention_period


class TeamRole(HorillaCoreModel):
    """
    Team Role model
    """

    team_role_name = models.CharField(
        max_length=50, blank=False, verbose_name=_("Team Role Name")
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    class Meta:
        """
        Meta options for the Team Role model.
        """

        verbose_name = _("Team Role")
        verbose_name_plural = _("Team Roles")

    def __str__(self):
        return str(self.team_role_name)

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "horilla_core:team_role_update_form", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """

        return reverse_lazy(
            "horilla_core:team_role_delete_view", kwargs={"pk": self.pk}
        )


class CustomerRole(HorillaCoreModel):
    """
    Customer Role model
    """

    customer_role_name = models.CharField(
        max_length=50, blank=False, verbose_name=_("Customer Role Name")
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    class Meta:
        """
        Meta options for the Customer Role model.
        """

        verbose_name = _("Customer Role")
        verbose_name_plural = _("Customer Roles")

    def __str__(self):
        return str(self.customer_role_name)

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "horilla_core:customer_role_update_form", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """

        return reverse_lazy(
            "horilla_core:customer_role_delete_view", kwargs={"pk": self.pk}
        )


class PartnerRole(HorillaCoreModel):
    """
    Partner Role model
    """

    partner_role_name = models.CharField(
        max_length=50, blank=False, verbose_name=_("Partner Role Name")
    )
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    class Meta:
        """
        Meta options for the Partner Role model.
        """

        verbose_name = _("Partner Role")
        verbose_name_plural = _("Partner Roles")

    def __str__(self):
        return str(self.partner_role_name)

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "horilla_core:partner_role_update_form", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """

        return reverse_lazy(
            "horilla_core:partner_role_delete_view", kwargs={"pk": self.pk}
        )


class ImportHistory(HorillaCoreModel):
    """
    Model to track the history of data imports.
    """

    STATUS_CHOICES = [
        ("processing", _("Processing")),
        ("success", _("Success")),
        ("partial", _("Partial Success")),
        ("failed", _("Failed")),
    ]

    import_name = models.CharField(max_length=255, verbose_name=_("Import Name"))
    module_name = models.CharField(max_length=100, verbose_name=_("Module Name"))
    app_label = models.CharField(max_length=100, verbose_name=_("App Label"))
    original_filename = models.CharField(max_length=255, verbose_name=_("Filename"))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="processing",
        verbose_name=_("Status"),
    )
    total_rows = models.IntegerField(default=0, verbose_name=_("Total Counts"))
    created_count = models.IntegerField(default=0)
    updated_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    success_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name=_("Success Rate (%)")
    )
    imported_file_path = models.CharField(
        max_length=500, blank=True, null=True, verbose_name=_("Imported File")
    )
    error_file_path = models.CharField(
        max_length=500, blank=True, null=True, verbose_name=_("Error File")
    )
    import_option = models.CharField(
        max_length=10, help_text=_("1=create, 2=update, 3=both")
    )
    match_fields = models.JSONField(default=list, blank=True)
    field_mappings = models.JSONField(default=dict, blank=True)
    error_summary = models.JSONField(default=list, blank=True)
    duration_seconds = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        verbose_name=_("Duration (seconds)"),
    )

    class Meta:
        """
        Meta options for the ImportHistory model.
        """

        ordering = ["-created_at"]
        verbose_name = _("Import History")
        verbose_name_plural = _("Import Histories")

    def __str__(self):
        return f"{self.import_name} - {self.module_name} ({self.status})"

    @property
    def successful_rows(self):
        """Returns the count of successful rows."""
        return self.created_count + self.updated_count

    def error_list(self):
        """Returns the HTML for the is_default column in the list view."""
        html = render_template(
            path="import/error_list_col.html",
            context={"instance": self},
        )
        return mark_safe(html)

    def imported_file(self):
        """Returns the HTML for the is_default column in the list view."""
        html = render_template(
            path="import/import_file_col.html",
            context={"instance": self},
        )
        return mark_safe(html)

    @property
    def has_errors(self):
        """Returns True if there are any errors."""
        return self.error_count > 0

    @property
    def is_complete(self):
        """Returns True if the import process is complete."""
        return self.status in ["success", "partial", "failed"]

    @property
    def status_color_class(self):
        """Returns the CSS class for the status badge."""
        colors = {
            "processing": "bg-blue-100 text-blue-800",
            "success": "bg-green-100 text-green-800",
            "partial": "bg-yellow-100 text-yellow-800",
            "failed": "bg-red-100 text-red-800",
        }
        return colors.get(self.status, "bg-gray-100 text-gray-800")

    @property
    def formatted_duration(self):
        """Returns the duration in a human-readable format."""
        if self.duration_seconds is None:
            return "N/A"

        seconds = float(self.duration_seconds)
        if seconds < 60:
            return f"{seconds:.1f}s"
        if seconds < 3600:
            return f"{seconds/60:.1f}m"

        return f"{seconds/3600:.1f}h"

    @property
    def module_verbose_name(self):
        """Returns the verbose name of the model based on module_name and app_label."""
        if not self.module_name or not self.app_label:
            return self.module_name or ""

        try:
            model = apps.get_model(self.app_label, self.module_name)
            return model._meta.verbose_name
        except (LookupError, AttributeError):
            # If model not found, return the module_name as fallback
            return self.module_name


class HorillaAttachment(HorillaCoreModel):
    """
    Model representing a generic attachment in the Horilla system.

    This model allows attaching files or notes to any model instance using
    Django's GenericForeignKey mechanism.
    """

    title = models.CharField(
        max_length=255,
        verbose_name=_("Title"),
        help_text=_("The title or name of the attachment."),
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Related Object Type"),
        help_text=_("The type of object this attachment is related to."),
    )
    object_id = models.PositiveIntegerField(
        verbose_name=_("Related Object ID"),
        help_text=_("The ID of the object this attachment is related to."),
    )
    related_object = GenericForeignKey("content_type", "object_id")
    file = models.FileField(
        _("File"),
        upload_to=upload_path,
        null=True,
        blank=True,
        help_text=_("Optional file attached to this record."),
    )
    description = models.TextField(
        _("Notes"),
        blank=True,
        null=True,
        help_text=_("Optional description or notes about the attachment."),
    )

    class Meta:
        """
        Metadata for HorillaAttachment model.
        """

        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")

    def __str__(self):
        """
        Returns a human-readable string representation of the attachment.
        """
        return str(self.title)

    def get_detail_view_url(self):
        """
        Returns the URL for viewing the details of this attachment.

        Returns:
            str: URL for the detail view of the attachment.
        """
        return reverse_lazy(
            "horilla_generics:notes_attachment_view", kwargs={"pk": self.pk}
        )

    def get_edit_url(self):
        """
        Returns the URL for editing this attachment.

        Returns:
            str: URL for the edit view of the attachment.
        """
        return reverse_lazy(
            "horilla_generics:notes_attachment_edit", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        Returns the URL for deleting this attachment.

        Returns:
            str: URL for the delete view of the attachment.
        """
        return reverse_lazy(
            "horilla_generics:notes_attachment_delete", kwargs={"pk": self.pk}
        )


class ExportSchedule(HorillaCoreModel):
    """
    Model to store export schedules for users.
    """

    FREQUENCY_CHOICES = (
        ("daily", _("Daily")),
        ("weekly", _("Weekly")),
        ("monthly", _("Monthly")),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="export_schedules",
    )
    modules = models.JSONField(
        help_text=_("List of model names, e.g. ['Employee', 'Department']"),
        verbose_name=_("Modules"),
    )
    export_format = models.CharField(
        max_length=5,
        choices=[("csv", _("CSV")), ("xlsx", _("Excel")), ("pdf", _("PDF"))],
        verbose_name=_("Export Format"),
    )
    frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES, verbose_name=_("Frequency")
    )

    # ---- monthly / weekly specifics ----
    day_of_month = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text=_("1-31 for monthly")
    )
    weekday = models.CharField(
        max_length=9,
        null=True,
        blank=True,
        choices=DAY_CHOICES,
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    # Yearly
    yearly_day_of_month = models.PositiveSmallIntegerField(null=True, blank=True)
    yearly_month = models.PositiveSmallIntegerField(
        null=True, blank=True, choices=[(i, i) for i in range(1, 13)]
    )

    last_run = models.DateField(
        null=True, blank=True, verbose_name=_("Last Executed On")
    )

    class Meta:
        """
        Meta options for the ExportSchedule model.
        """

        verbose_name = _("Export Schedule")
        verbose_name_plural = _("Export Schedules")

    PROPERTY_LABELS = {
        "module_names_display": "Modules",
        "last_executed": "Last Executed On",
        "frequency_display": "Schedule Details",
    }

    def __str__(self):
        return f"{self.user} – {self.frequency} – {self.export_format}"

    def module_names_display(self):
        """Return the module names as a comma-separated string."""
        return ", ".join(self.modules)

    def last_executed(self):
        """Return formatted last run date"""
        if self.last_run:
            return self.last_run
        return _("Not run yet")

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("horilla_core:schedule_modal")

    def get_delete_url(self):
        """
        This method to get delete url
        """

        return reverse_lazy(
            "horilla_core:schedule_export_delete", kwargs={"pk": self.pk}
        )

    def frequency_display(self):
        """Return formatted frequency and date."""

        if self.frequency == "daily":
            text = _("Every day")

        elif self.frequency == "weekly":
            weekday = self.get_weekday_display() if self.weekday else ""
            text = _("Every") + " " + weekday.capitalize()

        elif self.frequency == "monthly" and self.day_of_month:
            text = _("Day") + f" {self.day_of_month} " + _("of every month")

        elif self.frequency == "yearly":
            if self.yearly_day_of_month and self.yearly_month:
                text = f"{self.yearly_day_of_month}/{self.yearly_month}"
            else:
                text = _("Yearly")
        else:
            text = ""

        if self.start_date:
            if self.end_date:
                return format_html(
                    "{}<br><span class='text-xs text-gray-500'>From: {} to {}</span>",
                    text,
                    self.start_date.strftime("%d %b %Y"),
                    self.end_date.strftime("%d %b %Y"),
                )
            return format_html(
                "{}<br><span class='text-xs text-gray-500'>From: {}</span>",
                text,
                self.start_date.strftime("%d %b %Y"),
            )
        return format_html("{}", text)


class FieldPermission(models.Model):
    """
    Model to store field-level permissions for users and roles
    """

    PERMISSION_CHOICES = [
        ("readonly", "Read Only"),
        ("readwrite", "Read and Write"),
        ("hidden", "Don't Show"),
    ]

    # Link to either user or role (one must be set)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="field_permissions",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="field_permissions",
    )

    # Model and field information
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=255)

    # Permission type
    permission_type = models.CharField(
        max_length=20, choices=PERMISSION_CHOICES, default="readwrite"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """
        Meta options for the FieldPermission model.
        """

        unique_together = [
            ["user", "content_type", "field_name"],
            ["role", "content_type", "field_name"],
        ]
        verbose_name = _("Field Permission")
        verbose_name_plural = _("Field Permissions")

    def __str__(self):
        target = self.user.get_full_name() if self.user else self.role.role_name
        return f"{target} - {self.content_type.model}.{self.field_name}: {self.permission_type}"

    def clean(self):

        # Ensure either user or role is set, but not both
        if not self.user and not self.role:
            raise ValidationError("Either user or role must be set")
        if self.user and self.role:
            raise ValidationError("Cannot set both user and role")


class QuickFilter(models.Model):
    """Store user's quick filter preferences for list views"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quick_filters"
    )
    app_label = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    field_name = models.CharField(max_length=100)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "app_label", "model_name", "field_name")
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.model_name} - {self.field_name}"
