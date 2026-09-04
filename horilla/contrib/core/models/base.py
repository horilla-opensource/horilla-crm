"""
This module defines the core models for the Horilla platform
"""

# Third-party imports
# Standard library imports
import logging

from auditlog.models import AuditlogHistoryField, LogEntry

# Django imports
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# Third-party imports (Django)
from django_countries.fields import CountryField
from djmoney.settings import CURRENCY_CHOICES

from horilla.apps import apps
from horilla.contrib.utils.middlewares import _thread_local
from horilla.db import models
from horilla.extension import ExtensionModelBase
from horilla.registry.permission_registry import permission_exempt_model
from horilla.urls import reverse_lazy

# First party imports (Horilla)
from horilla.utils import timezone
from horilla.utils.choices import (
    DATE_FORMAT_CHOICES,
    DATETIME_FORMAT_CHOICES,
    TIME_FORMAT_CHOICES,
    TIMEZONE_CHOICES,
)
from horilla.utils.html import format_html
from horilla.utils.translation import gettext_lazy as _
from horilla.utils.upload import upload_path

logger = logging.getLogger(__name__)


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
            return str(model_cls._meta.verbose_name)
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
    contact_number = models.CharField(
        max_length=20, blank=True, null=True, verbose_name=_("Contact Number")
    )
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
    no_of_employees = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Number of Employees")
    )
    hq = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Head Quarter")
    )
    country = CountryField(verbose_name=_("Country"))
    state = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("State/Province")
    )
    city = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("City")
    )
    zip_code = models.CharField(
        max_length=20, blank=True, null=True, verbose_name=_("ZIP/Postal Code")
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
        choices=TIMEZONE_CHOICES,
        default="UTC",
        verbose_name=_("Time Zone"),
    )
    currency = models.CharField(
        max_length=20,
        choices=CURRENCY_CHOICES,
        default="USD",
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

    SORT_FIELD_MAPPING = {"get_avatar_with_name": "name"}

    def __str__(self):
        return f"{self.name}"

    def get_detail_view_url(self):
        """
        This method to get detail view url
        """
        return reverse_lazy("core:branch_detail_view", kwargs={"pk": self.pk})

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("core:edit_company_multi_step", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy("core:branch_delete", kwargs={"pk": self.pk})

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

            super().save(*args, **kwargs)

            self._original_currency = self.currency

            return None

        except Exception as e:
            logger.error("Error saving company %s: %s", self.pk, e)
            raise
        finally:
            del self._saving

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
            if not company:
                # ActiveCompanyMiddleware runs before DRF resolves request.user
                # for non-session auth (JWT/Basic), so active_company can still
                # be unset here even though the request is now authenticated.
                user = getattr(request, "user", None)
                if user is not None and user.is_authenticated:
                    company = getattr(user, "company", None)
            if company:
                queryset = queryset.filter(company=company)
        except Exception as e:
            logger.error("Error in CompanyFilteredManager.get_queryset: %s", e)
        return queryset


class HorillaCoreModel(models.Model, metaclass=ExtensionModelBase):
    """
    Core Base model.

    Supports _inherit_model extensions: subclass with
    _inherit_model = "app_label.ModelName" to inject fields onto an existing
    model without creating a new table.
    """

    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name=_("Is Active")
    )
    additional_info = models.JSONField(
        blank=True, null=True, verbose_name=_("Additional Info")
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Company"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, verbose_name=_("Created At")
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(class)s_created",
        verbose_name=_("Created By"),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
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
        content_type = HorillaContentType.objects.get_for_model(current_model)
        related_history = []

        model_ct_map = {
            model: HorillaContentType.objects.get_for_model(model)
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

            # Also handle models that use a custom string-based GFK pattern:
            # `related_model_name` (CharField) + `related_object_id` (IntegerField).
            # Standard Django GFK detection above misses these (e.g. CallLog).
            field_names = {f.name for f in opts.get_fields() if hasattr(f, "name")}
            if (
                "related_model_name" in field_names
                and "related_object_id" in field_names
            ):
                manager = getattr(model, "all_objects", model.objects)
                string_gfk_pks = manager.filter(
                    related_model_name__iexact=current_model._meta.model_name,
                    related_object_id=self.pk,
                ).values_list("pk", flat=True)
                related_pks.update(string_gfk_pks)

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
