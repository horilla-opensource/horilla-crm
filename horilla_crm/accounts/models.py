"""
Models for managing accounts in the CRM system, including account details,
"""

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.registry.feature import feature_enabled
from horilla_core.models import HorillaCoreModel
from horilla_core.utils import compute_score
from horilla_utils.middlewares import _thread_local


@feature_enabled(all=True)
class Account(HorillaCoreModel):
    """Model representing a business account."""

    ACCOUNT_SOURCE_CHOICES = [
        ("website", _("Website")),
        ("referral", _("Referral")),
        ("event", _("Event")),
        ("campaign", _("Campaign")),
        ("phone", _("Phone")),
        ("email", _("Email")),
        ("social media", _("Social Media")),
        ("partner", _("Partner")),
        ("other", _("Other")),
    ]

    ACCOUNT_TYPE_CHOICES = [
        ("prospect", _("Prospect")),
        ("customer_direct", _("Customer - Direct")),
        ("customer_channel", _("Customer - Channel")),
        ("channel_partner_reseller", _("Channel Partner / Reseller")),
        ("installation_partner", _("Installation Partner")),
        ("technology_partner", _("Technology Partner")),
        ("other", _("Other")),
    ]

    INDUSTRY_CHOICES = [
        ("finance", _("Finance")),
        ("healthcare", _("Healthcare")),
        ("manufacturing", _("Manufacturing")),
        ("agriculture", _("Agriculture")),
        ("construction", _("Construction")),
        ("banking", _("Banking")),
        ("education", _("Education")),
        ("insurance", _("Insurance")),
        ("other", _("Other")),
    ]

    OWNERSHIP_CHOICES = [
        ("public", _("Public")),
        ("private", _("Private")),
        ("subsidiary", _("Subsidiary")),
        ("other", _("Other")),
    ]

    name = models.CharField(max_length=255, verbose_name=_("Account Name"))
    account_number = models.CharField(
        max_length=40, blank=True, verbose_name=_("Account Number")
    )
    account_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name="owned_accounts",
        verbose_name=_("Account Owner"),
    )
    account_type = models.CharField(
        max_length=80,
        choices=ACCOUNT_TYPE_CHOICES,
        blank=True,
        verbose_name=_("Account Type"),
    )
    site = models.CharField(max_length=80, blank=True, verbose_name=_("Account Site"))
    account_source = models.CharField(
        max_length=255,
        choices=ACCOUNT_SOURCE_CHOICES,
        blank=True,
        verbose_name=_("Account Source"),
    )
    annual_revenue = models.DecimalField(
        max_digits=18,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name=_("Annual Revenue"),
    )
    billing_city = models.CharField(
        max_length=100, blank=True, verbose_name=_("Billing City")
    )
    billing_state = models.CharField(
        max_length=100, blank=True, verbose_name=_("Billing State")
    )
    billing_district = models.CharField(
        max_length=100, blank=True, verbose_name=_("Billing District")
    )
    billing_zip = models.CharField(
        max_length=20, blank=True, verbose_name=_("Billing Zip")
    )
    shipping_city = models.CharField(
        max_length=100, blank=True, verbose_name=_("Shipping City")
    )
    shipping_state = models.CharField(
        max_length=100, blank=True, verbose_name=_("Shipping State")
    )
    shipping_district = models.CharField(
        max_length=100, blank=True, verbose_name=_("Shipping District")
    )
    shipping_zip = models.CharField(
        max_length=20, blank=True, verbose_name=_("Shipping Zip")
    )
    is_customer_portal = models.BooleanField(
        default=False, verbose_name=_("Is Customer Portal")
    )
    customer_priority = models.CharField(
        max_length=255, blank=True, verbose_name=_("Customer Priority")
    )
    parent_account = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_accounts",
        verbose_name=_("Parent Account"),
    )
    is_partner = models.BooleanField(default=False, verbose_name=_("Is Partner"))
    description = models.TextField(
        max_length=32000, blank=True, verbose_name=_("Description")
    )
    industry = models.CharField(
        max_length=255, choices=INDUSTRY_CHOICES, verbose_name=_("Industry")
    )
    number_of_employees = models.IntegerField(
        null=True, blank=True, verbose_name=_("Number of Employees")
    )
    phone = models.CharField(max_length=40, blank=True, verbose_name=_("Phone"))
    fax = models.CharField(max_length=40, blank=True, verbose_name=_("Fax"))
    website = models.URLField(max_length=255, blank=True, verbose_name=_("Website"))
    operating_hours = models.CharField(
        max_length=255, blank=True, verbose_name=_("Operating Hours")
    )
    ownership = models.CharField(
        max_length=255,
        choices=OWNERSHIP_CHOICES,
        blank=True,
        verbose_name=_("Ownership"),
    )
    rating = models.CharField(max_length=255, blank=True, verbose_name=_("Rating"))
    account_score = models.IntegerField(default=0, verbose_name=_("Account Score"))

    OWNER_FIELDS = ["account_owner"]

    CURRENCY_FIELDS = ["annual_revenue"]

    class Meta:
        """Meta options for the Account model."""

        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("accounts:account_edit_form_view", kwargs={"pk": self.pk})

    def get_change_owner_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("accounts:account_change_owner", kwargs={"pk": self.pk})

    def get_detail_url(self):
        """
        This method to get detail view url
        """

        return reverse_lazy("accounts:account_detail_view", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy("accounts:account_delete_view", kwargs={"pk": self.pk})

    def get_child_account_url(self):
        """
        This method to get delete url of child account
        """
        return reverse_lazy("accounts:child_account_delete", kwargs={"pk": self.pk})

    def get_account_partner_url(self, account=None):
        """This method retrieves the edit URL for the account contact role."""
        try:
            request = getattr(_thread_local, "request", None)
            if request and hasattr(request, "resolver_match"):
                object_id = request.resolver_match.kwargs.get("pk")
                if object_id:
                    account = self.__class__.objects.filter(pk=object_id).first()
            ocr = None
            if account:
                ocr = self.partner.get(account=account)

            return ocr.get_account_partner() if ocr else None
        except Exception:
            return None

    def get_account_partner_delete_url(self, account=None):
        """This method retrieves the delete URL for the account contact role."""
        try:
            request = getattr(_thread_local, "request", None)
            if request and hasattr(request, "resolver_match"):
                object_id = request.resolver_match.kwargs.get("pk")
                if object_id:
                    account = self.__class__.objects.filter(pk=object_id).first()
            ocr = None
            if account:
                ocr = self.partner.get(account=account)

            return ocr.get_account_partner_delete() if ocr else None
        except Exception:
            return None

    def get_edit_contact_account_relation_url(self, contact=None):
        """
        This method is to gte the update url for contact account relation
        """
        try:
            request = getattr(_thread_local, "request", None)
            if request and hasattr(request, "resolver_match"):
                object_id = request.resolver_match.kwargs.get("pk")
                if object_id:
                    model = apps.get_model("contacts", "Contact")
                    contact = model.objects.get(pk=object_id)
            ocr = None
            if contact:
                ocr = self.contact_relationships.get(contact=contact)

            return ocr.get_edit_url_contact_account() if ocr else None
        except (Account.DoesNotExist, model.DoesNotExist, AttributeError, KeyError):
            return None

    def get_delete_related_accounts_url(self):
        """
        this methos is to get related account delete url
        """
        try:
            contact = None
            request = getattr(_thread_local, "request", None)
            if request and hasattr(request, "resolver_match"):
                object_id = request.resolver_match.kwargs.get("pk")
                if object_id:
                    model = apps.get_model("contacts", "Contact")
                    contact = model.objects.get(pk=object_id)
            ocr = None
            if contact:
                ocr = self.contact_relationships.get(contact=contact)

            return ocr.get_delete_url() if ocr else None
        except (Account.DoesNotExist, AttributeError):
            return None

    def __str__(self):
        return f"{self.name} - {self.pk}"


@receiver(pre_save, sender=Account)
def update_account_score(sender, instance, **_kwargs):
    """Update the account score before saving the account instance."""
    instance.account_score = compute_score(instance)


class PartnerAccountRelationship(HorillaCoreModel):
    """Model to represent the relationship between partner accounts."""

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="partner_account",
        verbose_name=_("Account"),
    )
    role = models.ForeignKey(
        "horilla_core.PartnerRole",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Partner Role"),
    )
    partner = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="partner",
        verbose_name=_("Partner Account"),
    )

    class Meta:
        """Meta options for the PartnerAccountRelationship model."""

        verbose_name = _("Partner Account Role")
        verbose_name_plural = _("Partner Account Roles")

    def __str__(self):
        return f"{self.account} ({self.role})"

    def get_account_partner(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "accounts:account_partner_update_form", kwargs={"pk": self.pk}
        )

    def get_account_partner_delete(self):
        """
        This method to get delete url
        """
        return reverse_lazy("accounts:partner_account_delete", kwargs={"pk": self.pk})

    def get_detail_url(self):
        """
        This method to get detail view url
        """
        url = self.partner.get_detail_url()
        return url
