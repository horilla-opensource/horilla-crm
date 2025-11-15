"""
Models for managing contacts in the CRM system, including contact details,
"""

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from djmoney.settings import CURRENCY_CHOICES

from horilla.registry.feature import feature_enabled
from horilla.utils.choices import LANGUAGE_CHOICES
from horilla_core.models import HorillaCoreModel
from horilla_core.utils import compute_score
from horilla_utils.middlewares import _thread_local

CONTACT_SOURCE_CHOICES = [
    ("web", _("Web")),
    ("phone_inquiry", _("Phone Inquiry")),
    ("partner_referral", _("Partner Referral")),
    ("purchased_list", _("Purchased List")),
    ("other", _("Other")),
]


@feature_enabled(all=True)
class Contact(HorillaCoreModel):
    """Django model for Contact object."""

    contact_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        default="",
        verbose_name=_("Contact Owner"),
        related_name="owned_contacts",
    )
    title = models.CharField(
        verbose_name=_("Title"), max_length=100, blank=True, null=True
    )
    first_name = models.CharField(verbose_name=_("First Name"), max_length=80)
    last_name = models.CharField(verbose_name=_("Last Name"), max_length=80)
    email = models.EmailField(verbose_name=_("Email"), max_length=100)
    phone = models.CharField(
        verbose_name=_("Phone"), max_length=40, blank=True, null=True
    )
    secondary_phone = models.CharField(
        verbose_name=_("Secondary Phone"), max_length=40, blank=True, null=True
    )

    address_city = models.CharField(
        verbose_name=_("City"), max_length=50, blank=True, null=True
    )
    address_state = models.CharField(
        verbose_name=_("State"), max_length=50, blank=True, null=True
    )
    address_zip = models.CharField(
        verbose_name=_("Zip"), max_length=20, blank=True, null=True
    )
    address_country = models.CharField(
        verbose_name=_("Country"), max_length=50, blank=True, null=True
    )
    parent_contact = models.ForeignKey(
        "self",
        verbose_name=_("Parent Contact"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_contacts",
    )
    contact_source = models.CharField(
        verbose_name=_("Contact Source"),
        max_length=50,
        choices=CONTACT_SOURCE_CHOICES,
        blank=True,
        null=True,
    )
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    birth_date = models.DateField(verbose_name=_("Birth Date"), blank=True, null=True)
    assistant = models.CharField(
        verbose_name=_("Assistant"), max_length=100, blank=True, null=True
    )
    assistant_phone = models.CharField(
        verbose_name=_("Assistant Phone"), max_length=40, blank=True, null=True
    )
    languages = models.CharField(
        verbose_name=_("Languages"),
        max_length=100,
        choices=LANGUAGE_CHOICES,
        blank=True,
        null=True,
    )
    is_primary = models.BooleanField(verbose_name=_("Is Primary"), default=False)
    contact_score = models.IntegerField(default=0, verbose_name=_("Contact Score"))

    OWNER_FIELDS = ["contact_owner"]

    class Meta:
        """Meta options for the Contact model."""

        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")

    def __str__(self):
        return f"{self.first_name or ''} {self.last_name}".strip()

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("contacts:contact_update_form", kwargs={"pk": self.pk})

    def get_delete_related_contact_url(self):
        """
        this method is to get related account delete url
        """
        try:
            contact = None
            request = getattr(_thread_local, "request", None)
            if request and hasattr(request, "resolver_match"):
                object_id = request.resolver_match.kwargs.get("pk")
                if object_id:
                    model = apps.get_model("accounts", "Account")
                    account = model.objects.get(pk=object_id)
            ocr = None
            if account:
                ocr = self.account_relationships.get(account=account)

            return ocr.get_delete_url() if ocr else None
        except (Contact.DoesNotExist, AttributeError):
            return None

    def get_edit_account_contact_relation_url(self, account=None):
        """This method retrieves the edit URL for the account contact role."""
        try:
            request = getattr(_thread_local, "request", None)
            if request and hasattr(request, "resolver_match"):
                object_id = request.resolver_match.kwargs.get("pk")
                if object_id:
                    model = apps.get_model("accounts", "Account")
                    account = model.objects.get(pk=object_id)
            ocr = None
            if account:
                ocr = self.account_relationships.get(account=account)

            return ocr.get_edit_account_contact_relation() if ocr else None
        except Exception:
            return None

    def get_delete_url(self):
        """
        this method to get delete url for contact
        """
        return reverse_lazy("contacts:contact_delete", kwargs={"pk": self.pk})

    def get_child_contact_delete_url(self):
        """
        this method to get delete url for child contact
        """
        return reverse_lazy("contacts:delete_child_contacts", kwargs={"pk": self.pk})

    def get_change_owner_url(self):
        """
        This method to get change owner url
        """

        return reverse_lazy("contacts:contact_change_owner", kwargs={"pk": self.pk})

    def get_detail_url(self):
        """
        This method to get detail view url
        """

        return reverse_lazy("contacts:contact_detail_view", kwargs={"pk": self.pk})

    def get_opportunity_contact_role_edit_url(self, opportunity=None):
        """This method retrieves the edit URL for the opportunity contact role."""
        try:
            request = getattr(_thread_local, "request", None)
            if request and hasattr(request, "resolver_match"):
                object_id = request.resolver_match.kwargs.get("pk")
                if object_id:
                    model = apps.get_model("opportunities", "Opportunity")
                    opportunity = model.objects.get(pk=object_id)
            ocr = None
            if opportunity:
                ocr = self.opportunity_roles.get(opportunity=opportunity)

            return ocr.get_edit_url() if ocr else None
        except Exception:
            return None

    def get_opportunity_contact_role_delete_url(self, opportunity=None):
        """This method retrieves the delete URL for the opportunity contact role."""
        try:
            request = getattr(_thread_local, "request", None)
            if request and hasattr(request, "resolver_match"):
                object_id = request.resolver_match.kwargs.get("pk")
                if object_id:
                    model = apps.get_model("opportunities", "Opportunity")
                    opportunity = model.objects.get(pk=object_id)
            ocr = None
            if opportunity:
                ocr = self.opportunity_roles.get(opportunity=opportunity)

            return ocr.get_delete_url() if ocr else None
        except Exception:
            return None


@receiver(pre_save, sender=Contact)
def update_contact_score(sender, instance, **_kwargs):
    """
    Signal to update the contact's score before saving.
    Computes and assigns a score using `compute_score`.
    """
    instance.contact_score = compute_score(instance)


class ContactAccountRelationship(HorillaCoreModel):
    """
    Represents the relationship between a contact and an account.
    Stores the linked contact, associated account, and optional role.
    """

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="account_relationships",
        verbose_name=_("Contact"),
    )
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="contact_relationships",
        verbose_name=_("Account"),
    )
    role = models.ForeignKey(
        "horilla_core.CustomerRole",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Role"),
    )

    class Meta:
        """Ensure unique contact–account pairs and define verbose names."""

        unique_together = ("contact", "account")
        verbose_name = _("Contact Account Relationship")
        verbose_name_plural = _("Contact Account Relationships")

    def __str__(self):
        return f"{self.contact} - {self.account} ({self.role})"

    def get_edit_account_contact_relation(self):
        """
        This method is to get the update url for contact account relation
        """

        return reverse_lazy(
            "accounts:edit_account_contact_relation", kwargs={"pk": self.pk}
        )

    def get_edit_url_contact_account(self):
        """
        This method is to gte the update url for contact account relation
        """

        return reverse_lazy(
            "contacts:edit_contact_account_relation", kwargs={"pk": self.pk}
        )

    def get_detail_url(self):
        """
        This method to get detail view url of contact
        """
        url = self.contact.get_detail_url()
        return url

    def get_delete_url(self):
        """
        this methos is to get related account delete url
        """
        return reverse_lazy("contacts:delete_related_accounts", kwargs={"pk": self.pk})

    def get_detail_view_url(self):
        """
        This method to get detail view url
        """
        return self.account.get_detail_url()
