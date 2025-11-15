"""
Defines models for managing marketing campaigns and their members.
Includes campaign details, ownership, and member (lead/contact) associations.
Provides URL helpers and validation for campaign-related operations.
"""

import logging

from django.apps import apps
from django.conf import settings
from django.db import models
from django.forms import ValidationError
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla.registry.feature import feature_enabled
from horilla_core.models import HorillaCoreModel, MultipleCurrency
from horilla_utils.middlewares import _thread_local

logger = logging.getLogger(__name__)


class CampaignMember(HorillaCoreModel):
    """
    Model representing a member (Lead or Contact) associated with a campaign.
    """

    CAMPAIGN_MEMBER_STATUS = [
        ("planned", _("Planned")),
        ("sent", _("Sent")),
        ("recieved", _("Recieved")),
        ("responded", _("Responded")),
    ]
    MEMBER_TYPE_CHOICES = [
        ("lead", _("Lead")),
        ("contact", _("Contact")),
    ]
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name=_("Campaign"),
    )
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lead_campaign_members",
        verbose_name=_("Lead"),
    )
    member_status = models.CharField(
        max_length=20, choices=CAMPAIGN_MEMBER_STATUS, verbose_name=_("Member Status")
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_campaign_members",
        verbose_name=_("Contact"),
    )
    member_type = models.CharField(
        max_length=10,
        choices=MEMBER_TYPE_CHOICES,
        verbose_name=_("Type"),
        default="lead",
    )

    def get_detail_view(self):
        """
        Returns the detail view URL for the associated Lead or Contact based on member_type.
        """
        try:
            if self.member_type == "lead":
                model_instance = self.lead
                if model_instance and hasattr(model_instance, "get_detail_url"):
                    return model_instance.get_detail_url()
            elif self.member_type == "contact":
                model_instance = self.contact
                if model_instance and hasattr(model_instance, "get_detail_url"):
                    return model_instance.get_detail_url()

            return "#"
        except Exception as e:
            logger.error(e)
            return "#"

    def get_detail_view_of_contact_campaign(self):
        """
        Method to get the detail view url of the campaign for contact related campaigns
        """

        model_instance = self.campaign
        if model_instance and hasattr(model_instance, "get_detail_view_url"):
            return model_instance.get_detail_view_url()

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("campaigns:edit_campaign_member", kwargs={"pk": self.pk})

    def get_edit_campaign_member(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "campaigns:edit_added_campaign_members", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy("campaigns:delete_campaign_member", kwargs={"pk": self.pk})

    def get_edit_contact_to_campaign_url(self):
        """
        This method to get the edit url for add contact to camapign
        """

        return reverse_lazy(
            "campaigns:edit_contact_to_campaign", kwargs={"pk": self.pk}
        )

    def get_delete_contact_to_campaign_url(self):
        """
        This method is to get delete url for added contact to campaign
        """

        return reverse_lazy(
            "campaigns:delete_campaign_contact_member", kwargs={"pk": self.pk}
        )

    def get_title(self):
        """
        Return the appropriate title based on member_type.
        """
        if self.member_type == "lead" and self.lead:
            return self.lead.title
        if self.member_type == "contact" and self.contact:
            return str(self.contact)
        return None

    def __str__(self):
        if self.member_type == "lead" and self.lead:
            return f"{self.lead} in {self.campaign}"
        if self.member_type == "contact" and self.contact:
            return f"{self.contact} in {self.campaign}"
        return f"Unknown member in {self.campaign}"

    class Meta:
        """
        Meta class for CampaignMember model
        """

        verbose_name = _("Campaign Member")
        verbose_name_plural = _("Campaign Members")

    def clean(self):
        """
        Custom validation to check for duplicates
        """
        super().clean()

        # Check for duplicate lead in same campaign
        if self.member_type == "lead" and self.lead and self.campaign:
            existing = CampaignMember.objects.filter(
                campaign=self.campaign, lead=self.lead
            ).exclude(pk=self.pk if self.pk else None)

            if existing.exists():
                raise ValidationError("This lead already has this campaign.")

        # Check for duplicate contact in same campaign
        elif self.member_type == "contact" and self.contact and self.campaign:
            existing = CampaignMember.objects.filter(
                campaign=self.campaign, contact=self.contact
            ).exclude(pk=self.pk if self.pk else None)

            if existing.exists():
                raise ValidationError("This contact already has this campaign.")

    @property
    def campaign_type_display(self):
        """
        Function to return campaign type display
        """
        if self.campaign:
            return self.campaign.get_campaign_type_display()
        return ""

    def save(self, *args, **kwargs):
        """
        Override save method to update campaign's responses_in_campaign when member_status is 'responded'.
        """
        is_new = not self.pk
        old_status = None
        if not is_new:
            try:
                old_instance = CampaignMember.objects.get(pk=self.pk)
                old_status = old_instance.member_status
            except CampaignMember.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if self.campaign and (is_new or old_status != self.member_status):
            if self.member_status == "responded":
                self.campaign.responses_in_campaign = self.campaign.members.filter(
                    member_status="responded"
                ).count()
                self.campaign.save(update_fields=["responses_in_campaign"])


@feature_enabled(all=True)
class Campaign(HorillaCoreModel):
    """
    Model representing a marketing campaign.
    """

    CAMPAIGN_STATUS_CHOICES = [
        ("new", _("New")),
        ("planned", _("Planned")),
        ("in_progress", _("In Progress")),
        ("completed", _("Completed")),
        ("aborted", _("Aborted")),
    ]

    CAMPAIGN_TYPE_CHOICES = [
        ("email", _("Email")),
        ("event", _("Event")),
        ("social_media", _("Social Media")),
        ("other", _("Other")),
    ]

    campaign_name = models.CharField(max_length=255, verbose_name=_("Campaign Name"))
    campaign_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        default="",
        verbose_name=_("Campaign Owner"),
        related_name="campaign",
    )
    status = models.CharField(
        max_length=20,
        choices=CAMPAIGN_STATUS_CHOICES,
        default="planned",
        verbose_name=_("Status"),
    )
    campaign_type = models.CharField(
        max_length=20, choices=CAMPAIGN_TYPE_CHOICES, verbose_name=_("Type")
    )
    start_date = models.DateField(blank=True, null=True, verbose_name=_("Start Date"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("End Date"))
    expected_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Expected Revenue"),
    )
    budget_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Budget Cost"),
    )
    actual_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Actual Cost"),
    )
    expected_response = models.FloatField(
        null=True, blank=True, verbose_name=_("Expected Response (%)")
    )
    number_sent = models.PositiveIntegerField(
        default=0, verbose_name=_("Number Sent in Campaign")
    )
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    parent_campaign = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_campaigns",
        verbose_name=_("Parent Campaign"),
    )

    leads_in_campaign = models.PositiveIntegerField(
        default=0, verbose_name=_("Leads in Campaign")
    )
    converted_leads_in_campaign = models.PositiveIntegerField(
        default=0, verbose_name=_("Converted Leads in Campaign")
    )
    contacts_in_campaign = models.PositiveIntegerField(
        default=0, verbose_name=_("Contacts in Campaign")
    )
    opportunities_in_campaign = models.PositiveIntegerField(
        default=0, verbose_name=_("Opportunities in Campaign")
    )
    won_opportunities_in_campaign = models.PositiveIntegerField(
        default=0, verbose_name=_("Won Opportunities in Campaign")
    )
    value_opportunities = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Value Opportunities in Campaign"),
    )
    value_won_opportunities = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0.00,
        verbose_name=_("Value Won Opportunities in Campaign"),
    )
    responses_in_campaign = models.PositiveIntegerField(
        default=0, verbose_name=_("Responses in Campaign")
    )

    OWNER_FIELDS = ["campaign_owner"]

    CURRENCY_FIELDS = [
        "expected_revenue",
        "budget_cost",
        "actual_cost",
        "value_opportunities",
        "value_won_opportunities",
    ]

    def __str__(self):
        return f"{self.campaign_name}-{self.pk}"

    class Meta:
        """
        Meta class for Campaign model
        """

        verbose_name = _("Campaign")
        verbose_name_plural = _("Campaigns")

    def get_edit_campaign_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("campaigns:campaign_edit", kwargs={"pk": self.pk})

    def get_change_owner_url(self):
        """
        This method to get change owner url
        """
        return reverse_lazy("campaigns:campaign_change_owner", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy("campaigns:campaign_delete", kwargs={"pk": self.pk})

    def get_delete_child_campaign_url(self):
        """
        This method to get  delete child campaign url
        """
        return reverse_lazy("campaigns:delete_child_campaign", kwargs={"pk": self.pk})

    def get_detail_view_url(self):
        """
        This method to get detail view url
        """

        return reverse_lazy("campaigns:campaign_detail_view", kwargs={"pk": self.pk})

    def get_specific_member_edit_url(self, object_model=None, object_id=None):
        """
        Returns the edit URL for the CampaignMember linked to the given object_model and object_id.
        Falls back to request query parameters if not provided.
        """
        try:
            request = getattr(_thread_local, "request", None)
            if request:
                object_model = request.GET.get("model_name", "").lower()
                object_id = request.resolver_match.kwargs.get("pk")
            field_name = "lead"
            filter_kwargs = {
                "campaign": self,
                field_name: apps.get_model(
                    "leads", object_model.capitalize()
                ).objects.get(pk=object_id),
            }
            member = self.members.filter(**filter_kwargs).first()
            return member.get_edit_url()
        except (AttributeError, models.ObjectDoesNotExist, KeyError) as e:
            logger.error(e)
            return "#"

    def get_edit_contact_to_campaign_url_for_contact(self, contact=None):
        """
        Return the edit URL for the CampaignMember linking this campaign and a given contact.
        If contact is None, tries to retrieve from request context (pk).
        """
        ocr = None

        try:
            request = getattr(_thread_local, "request", None)
            if request and hasattr(request, "resolver_match"):
                object_id = request.resolver_match.kwargs.get("pk")
                if object_id:
                    model = apps.get_model("contacts", "Contact")
                    contact = model.objects.get(pk=object_id)
            if contact:
                ocr = self.members.get(contact=contact)

            return ocr.get_edit_contact_to_campaign_url() if ocr else None
        except (AttributeError, models.ObjectDoesNotExist, KeyError) as e:
            logger.error(e)
            return None

    def get_delete_contact_to_campaign_url_for_contact(self):
        """
        this method is to get related account delete url
        """

        contact = None
        ocr = None

        try:
            request = getattr(_thread_local, "request", None)
            if request and hasattr(request, "resolver_match"):
                object_id = request.resolver_match.kwargs.get("pk")
                if object_id:
                    model = apps.get_model("contacts", "Contact")
                    contact = model.objects.get(pk=object_id)
            if contact:
                ocr = self.members.get(contact=contact)

            return ocr.get_delete_contact_to_campaign_url() if ocr else None
        except (AttributeError, models.ObjectDoesNotExist, KeyError) as e:
            logger.error(e)
            return None

    def recalculate_metrics(self):
        """
        Recalculate all campaign metrics and update the fields.
        Useful for migrations or manual corrections.
        """
        from django.db.models import Sum

        # Leads and converted leads
        self.leads_in_campaign = self.members.filter(member_type="lead").count()
        self.converted_leads_in_campaign = self.members.filter(
            member_type="lead", lead__is_convert=True
        ).count()
        # Contacts
        self.contacts_in_campaign = self.members.filter(member_type="contact").count()
        # Opportunities
        opportunities = self.opportunities.all()
        self.opportunities_in_campaign = opportunities.count()
        won_opps_by_final = opportunities.filter(stage__is_final=True)
        self.won_opportunities_in_campaign = won_opps_by_final.count()
        # Opportunity values
        value_opps = opportunities.aggregate(total=Sum("amount"))["total"] or 0
        value_won_opps = (
            opportunities.filter(stage__is_final=True).aggregate(total=Sum("amount"))[
                "total"
            ]
            or 0
        )
        self.value_opportunities = value_opps
        self.value_won_opportunities = value_won_opps
        self.responses_in_campaign = self.members.filter(
            member_status="responded"
        ).count()
        self.save(
            update_fields=[
                "leads_in_campaign",
                "converted_leads_in_campaign",
                "contacts_in_campaign",
                "opportunities_in_campaign",
                "won_opportunities_in_campaign",
                "value_opportunities",
                "value_won_opportunities",
            ]
        )
