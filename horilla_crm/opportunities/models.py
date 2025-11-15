"""
Opportunities module models.
"""

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from horilla import settings
from horilla.registry.feature import feature_enabled
from horilla.registry.permission_registry import permission_exempt_model
from horilla_core.models import (
    Company,
    CustomerRole,
    HorillaCoreModel,
    HorillaUser,
    MultipleCurrency,
)
from horilla_core.utils import compute_score
from horilla_crm.accounts.models import Account
from horilla_crm.campaigns.models import Campaign
from horilla_crm.contacts.models import Contact
from horilla_utils.methods import render_template
from horilla_utils.middlewares import _thread_local


@feature_enabled(import_data=True, export_data=True, global_search=True)
class OpportunityStage(HorillaCoreModel):
    """Opportunity Stage model for flexible stage management"""

    STAGE_TYPE_CHOICES = [
        ("open", _("Open")),
        ("won", _("Closed Won")),
        ("lost", _("Closed Lost")),
    ]

    name = models.CharField(max_length=100, verbose_name=_("Stage Name"))
    order = models.PositiveIntegerField(
        verbose_name=_("Order"), help_text="Order in which stages appear"
    )
    probability = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name=_("Probability"),
        help_text="Default probability percentage for this stage",
    )
    is_final = models.BooleanField(default=False, verbose_name=_("Is Final Stage"))
    stage_type = models.CharField(
        max_length=10,
        choices=STAGE_TYPE_CHOICES,
        default="open",
        verbose_name=_("Stage Type"),
        help_text=_("Type of stage - Open, Closed Won, or Closed Lost"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._desired_position = None

    def is_final_col(self):
        """Returns the HTML for the is_final column in the list view."""
        html = render_template(
            path="opportunity_stage/is_final_col.html",
            context={"instance": self},
        )
        return mark_safe(html)

    def clean(self):
        if self.order < 0:
            raise ValidationError(_("Order must be a non-negative integer."))

    @property
    def is_won(self):
        """Helper property to check if this is a won stage"""
        return self.stage_type == "won"

    @property
    def is_lost(self):
        """Helper property to check if this is a lost stage"""
        return self.stage_type == "lost"

    @property
    def is_closed(self):
        """Helper property to check if this is any closed stage"""
        return self.stage_type in ["won", "lost"]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            previous_final = None
            if self.is_final:
                previous_final = (
                    OpportunityStage.objects.filter(is_final=True, company=self.company)
                    .exclude(pk=self.pk)
                    .first()
                )
                if previous_final:
                    OpportunityStage.objects.filter(pk=previous_final.pk).update(
                        is_final=False
                    )

            if self.pk is None:
                # For new stages, use provided order or next available order
                if not self.order:
                    self.order = self.get_next_order_for_company(self.company)
                self._desired_position = self.order if not self.is_final else None
            else:
                original = OpportunityStage.objects.get(pk=self.pk)
                is_final_changed = self.is_final != original.is_final

                if is_final_changed or self.order != original.order:
                    self._desired_position = self.order if not self.is_final else None

            super().save(*args, **kwargs)
            self._reorder_all_statuses(previous_final=previous_final)

    def _reorder_all_statuses(self, previous_final=None):
        """
        Reorder all statuses for the company to ensure sequential ordering with final stage last.
        Uses temporary order numbers to avoid unique constraint violations.
        """
        company_statuses = list(
            OpportunityStage.objects.filter(company=self.company)
            .select_for_update()
            .order_by("order", "pk")
        )

        final_statuses = [s for s in company_statuses if s.is_final]
        non_final_statuses = [s for s in company_statuses if not s.is_final]

        if len(final_statuses) > 1:
            if self.is_final and self in final_statuses:
                final_statuses = [self]
            else:
                final_statuses = final_statuses[:1]
            for status in [
                s for s in company_statuses if s.is_final and s not in final_statuses
            ]:
                OpportunityStage.objects.filter(pk=status.pk).update(is_final=False)

        if hasattr(self, "_desired_position") and self._desired_position is not None:
            desired_order = self._desired_position
            non_final_statuses = [s for s in non_final_statuses if s != self]
            non_final_statuses.sort(key=lambda x: x.order)

            max_order = max([s.order for s in non_final_statuses], default=0)

            if desired_order > max_order:
                non_final_statuses.append(self)
            else:
                non_final_statuses.insert(max(0, desired_order - 1), self)
        else:
            non_final_statuses.sort(key=lambda x: x.order)

        if previous_final and previous_final in non_final_statuses:
            non_final_statuses.remove(previous_final)
            reordered_statuses = non_final_statuses + [previous_final] + final_statuses
        else:
            reordered_statuses = non_final_statuses + final_statuses

        temp_order_start = 10000
        for idx, status in enumerate(reordered_statuses):
            OpportunityStage.objects.filter(pk=status.pk).update(
                order=temp_order_start + idx
            )

        for i, status in enumerate(reordered_statuses, 1):
            OpportunityStage.objects.filter(pk=status.pk).update(order=i)

        if hasattr(self, "_desired_position"):
            delattr(self, "_desired_position")

    @staticmethod
    @receiver(post_delete, sender="opportunities.OpportunityStage")
    def handle_bulk_delete(sender, instance, **kwargs):
        """
        Handle bulk deletions or queryset deletions by reordering remaining statuses
        and setting the last stage as final if no final stage exists.
        """
        with transaction.atomic():
            try:
                company = instance.company  # Attempt to access the company
                # Ensure the company exists in the database
                if not Company.objects.filter(pk=company.pk).exists():
                    return
                was_final = instance.is_final
                remaining_statuses = list(
                    OpportunityStage.objects.filter(company=company).order_by("order")
                )
                for i, status in enumerate(remaining_statuses, 1):
                    OpportunityStage.objects.filter(pk=status.pk).update(order=i)
                if (
                    was_final
                    and remaining_statuses
                    and not any(s.is_final for s in remaining_statuses)
                ):
                    last_stage = remaining_statuses[-1]
                    OpportunityStage.objects.filter(pk=last_stage.pk).update(
                        is_final=True
                    )
            except Company.DoesNotExist:
                return

    @classmethod
    def get_next_order_for_company(cls, company):
        """
        Get the next available order number for a company, just before final stage
        """
        max_order = cls.objects.filter(company=company, is_final=False).aggregate(
            max_order=models.Max("order")
        )["max_order"]
        return (max_order or 0) + 1

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "opportunities:edit_opportunity_stage", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy(
            "opportunities:delete_opportunity_stage", kwargs={"pk": self.pk}
        )

    class Meta:
        """Meta options for OpportunityStage model."""

        verbose_name = _("Opportunity Stage")
        verbose_name_plural = _("Opportunity Stages")
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "company"], name="unique_stage_name_per_company"
            ),
            models.UniqueConstraint(
                fields=["order", "company"], name="unique_stage_order_per_company"
            ),
        ]

    def __str__(self):
        return str(self.name)


@feature_enabled(all=True)
class Opportunity(HorillaCoreModel):
    """Django model based on Salesforce Opportunity object"""

    TYPE_CHOICES = [
        ("existing_customer_upgrade", "Existing Customer - Upgrade"),
        ("existing_customer_replacement", "Existing Customer - Replacement"),
        ("existing_customer_downgrade", "Existing Customer - Downgrade"),
        ("new_customer", "New Customer"),
    ]

    LEAD_SOURCES = [
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

    FORECAST_CATEGORY_CHOICES = [
        ("omitted", "Omitted"),
        ("pipeline", "Pipeline"),
        ("best_case", "Best Case"),
        ("commit", "Commit"),
        ("closed", "Closed"),
    ]

    DELIVERY_STATUS_CHOICES = [
        ("yet_to_fulfill", "Yet to Fulfill"),
        ("partially_delivered", "Partially Delivered"),
        ("completely_delivered", "Completely Delivered"),
    ]

    name = models.CharField(
        max_length=120, verbose_name=_("Opportunity Name"), help_text="Opportunity Name"
    )
    email = models.EmailField(
        validators=[EmailValidator()], verbose_name=_("Email"), null=True, blank=True
    )

    amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True, verbose_name=_("Amount")
    )
    expected_revenue = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Expected Revenue"),
    )
    quantity = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Quantity"),
        help_text="Total Opportunity Quantity",
    )
    close_date = models.DateField(null=True, blank=True, verbose_name=_("Close Date"))
    stage = models.ForeignKey(
        OpportunityStage,
        on_delete=models.PROTECT,
        verbose_name=_("Stage"),
        help_text="Current opportunity stage",
    )
    probability = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Probability"),
        help_text="Probability percentage (0-100)",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    description = models.TextField(
        max_length=32000, blank=True, verbose_name=_("Description")
    )
    next_step = models.CharField(
        max_length=255, blank=True, verbose_name=_("Next Step")
    )
    opportunity_score = models.IntegerField(
        default=0, verbose_name=_("Opportunity Score")
    )
    primary_campaign_source = models.ForeignKey(
        Campaign,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Primary Campaign Source"),
        related_name="opportunities",
    )
    owner = models.ForeignKey(
        HorillaUser,
        on_delete=models.PROTECT,
        verbose_name=_("Owner"),
        help_text="Opportunity Owner",
    )
    opportunity_type = models.CharField(
        max_length=50, choices=TYPE_CHOICES, blank=True, verbose_name=_("Type")
    )
    lead_source = models.CharField(
        max_length=50, choices=LEAD_SOURCES, blank=True, verbose_name=_("Lead Source")
    )
    forecast_category = models.CharField(
        max_length=50,
        choices=FORECAST_CATEGORY_CHOICES,
        blank=True,
        verbose_name=_("Forecast Category"),
    )
    delivery_installation_status = models.CharField(
        max_length=50,
        choices=DELIVERY_STATUS_CHOICES,
        blank=True,
        verbose_name=_("Delivery Installation Status"),
    )
    main_competitors = models.CharField(
        max_length=100, blank=True, verbose_name=_("Main Competitors")
    )
    order_number = models.CharField(
        max_length=8, blank=True, verbose_name=_("Order Number")
    )
    tracking_number = models.CharField(
        max_length=12, blank=True, verbose_name=_("Tracking Number")
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        default="",
        null=True,
        blank=True,
        verbose_name=_("Account"),
        related_name="opportunity_account",
    )

    OWNER_FIELDS = ["owner"]
    CURRENCY_FIELDS = ["amount", "expected_revenue"]

    class Meta:
        """Meta options for Opportunity model."""

        verbose_name = _("Opportunity")
        verbose_name_plural = _("Opportunities")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}"

    DYNAMIC_METHODS = ["get_change_owner_url", "get_edit_url", "get_detail_url"]

    def get_change_owner_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "opportunities:opportunity_change_owner", kwargs={"pk": self.pk}
        )

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy("opportunities:opportunity_edit", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy("opportunities:opportunity_delete", kwargs={"pk": self.pk})

    def get_detail_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy(
            "opportunities:opportunity_detail_view", kwargs={"pk": self.pk}
        )

    def set_forecast_category(self):
        """
        Set forecast_category based on the stage's probability and status.
        """
        if not self.stage:
            self.forecast_category = "pipeline"
            return

        # If stage is lost, set to omitted
        if self.stage.is_lost:
            self.forecast_category = "omitted"

        # If stage is won, set to closed
        elif self.stage.is_won:
            self.forecast_category = "closed"

        # Otherwise, map probability to forecast category
        else:
            probability = self.probability or self.stage.probability or 0
            if probability < 10:
                self.forecast_category = "pipeline"
            elif 10 <= probability <= 40:

                self.forecast_category = "pipeline"
            elif 41 <= probability <= 70:
                self.forecast_category = "best_case"
            elif 71 <= probability <= 99:
                self.forecast_category = "commit"
            elif probability == 100:
                self.forecast_category = "closed"

    def save(self, *args, **kwargs):
        if self.stage:
            self.probability = self.stage.probability
        if self.amount is not None and self.probability is not None:
            self.expected_revenue = self.amount * (self.probability / 100)
        self.set_forecast_category()

        super().save(*args, **kwargs)


@receiver(pre_save, sender=Opportunity)
def update_opportunity_score(sender, instance, **kwargs):
    """
    Computes and updates the opportunity score before saving the Opportunity instance.
    """
    instance.opportunity_score = compute_score(instance)


class OpportunityContactRole(HorillaCoreModel):
    """Links a contact to an opportunity with a specific role."""

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="opportunity_roles",
        verbose_name="Contact",
        null=False,
        blank=False,
    )

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name="contact_roles",
        verbose_name="Opportunity",
        null=False,
        blank=False,
    )

    is_primary = models.BooleanField(default=False, verbose_name="Primary")

    role = models.ForeignKey(
        CustomerRole,
        on_delete=models.SET_NULL,
        related_name="opportunity_contact_roles",
        verbose_name=_("Role"),
        null=True,
        blank=True,
    )

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "opportunities:edit_opportunity_contact_role", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy(
            "opportunities:opportunity_contact_role_delete", kwargs={"pk": self.pk}
        )

    class Meta:
        """Meta options for OpportunityContactRole model."""

        verbose_name = "Opportunity Contact Role"
        verbose_name_plural = "Opportunity Contact Roles"
        unique_together = ("contact", "opportunity")

    def __str__(self):
        return f"{self.contact} - {self.opportunity} ({self.role})"


TEAM_ROLE_CHOICES = [
    ("account_manager", _("Account Manager")),
    ("channel_manager", _("Channel Manager")),
    ("executive_sponsor", _("Executive Sponsor")),
    ("lead_qualifier", _("Lead Qualifier")),
    ("pre_sales_consultant", _("Pre-Sales Consultant")),
    ("sales_manager", _("Sales Manager")),
    ("sales_rep", _("Sales Rep")),
    ("opportunity_owner", _("Opportunity Owner")),
    ("other", _("Other")),
]

ACCESS_LEVEL_CHOICES = [
    ("read", _("Read Only")),
    ("edit", _("Read/Write")),
    ("owner", _("Owner")),
]


@feature_enabled(global_search=True)
class OpportunityTeam(HorillaCoreModel):
    """Represents a team assigned to manage opportunities."""

    team_name = models.CharField(max_length=255, verbose_name=_("Team Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    owner = models.ForeignKey(
        HorillaUser,
        on_delete=models.PROTECT,
        related_name="owner",
        verbose_name=_("Owner"),
    )

    OWNER_FIELDS = ["owner"]

    class Meta:
        """Meta options for OpportunityTeam model."""

        verbose_name = _("Opportunity Team")
        verbose_name_plural = _("Opportunity Teams")

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "opportunities:edit_opportunity_team", kwargs={"pk": self.pk}
        )

    def get_detail_view_url(self):
        """
        This method to get detail view url
        """
        return reverse_lazy(
            "opportunities:opportunity_team_detail_view", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy(
            "opportunities:delete_opportunity_team", kwargs={"pk": self.pk}
        )

    def __str__(self):
        return str(self.team_name)


class OpportunityTeamMember(HorillaCoreModel):
    """Represents a member of an opportunity team with a specific role and access level."""

    opportunity = models.ForeignKey(
        "Opportunity",
        on_delete=models.CASCADE,
        related_name="opportunity_team_members",
        verbose_name=_("Opportunity"),
    )
    opportunity_access = models.CharField(
        max_length=255,
        choices=ACCESS_LEVEL_CHOICES,
        default="Read",
        verbose_name=_("Opportunity Access"),
    )
    team_role = models.CharField(
        max_length=255, choices=TEAM_ROLE_CHOICES, verbose_name=_("Member Role")
    )
    user = models.ForeignKey(
        HorillaUser,
        on_delete=models.PROTECT,
        related_name="opportunty_team_users",
        verbose_name=_("Team Members"),
    )

    class Meta:
        """Meta options for OpportunityTeamMember model."""

        verbose_name = _("Opportunity team member")
        verbose_name_plural = _("Opportunity team members")

    def __str__(self):
        return f"{self.user} - {self.team_role}"

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "opportunities:edit_opportunity_member", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy(
            "opportunities:delete_opportunity_member", kwargs={"pk": self.pk}
        )


@permission_exempt_model
class DefaultOpportunityMember(HorillaCoreModel):
    """
    Default team members that get automatically added to new opportunities
    """

    team = models.ForeignKey(
        "OpportunityTeam",
        on_delete=models.CASCADE,
        related_name="team_members",
        verbose_name=_("Team Name"),
    )

    user = models.ForeignKey(
        HorillaUser,
        on_delete=models.CASCADE,
        related_name="default_opportunity_memberships",
        verbose_name=_("Team Member"),
    )

    team_role = models.CharField(
        max_length=255, choices=TEAM_ROLE_CHOICES, verbose_name=_("Member Role")
    )

    opportunity_access_level = models.CharField(
        choices=ACCESS_LEVEL_CHOICES, max_length=20, verbose_name=_("Access Level")
    )

    class Meta:
        """Meta options for DefaultOpportunityMember model."""

        verbose_name = _("Default Opportunity Member")
        verbose_name_plural = _("Default Opportunity Members")
        unique_together = ("user", "team")

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "opportunities:edit_opportunity_team_member", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy(
            "opportunities:delete_opportunity_team_member", kwargs={"pk": self.pk}
        )

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class OpportunitySettings(HorillaCoreModel):
    """
    Global settings for Opportunity module features
    """

    team_selling_enabled = models.BooleanField(
        default=False,
        verbose_name=_("Enable Team Selling"),
        help_text=_(
            "Enable Opportunity Teams to help multiple users collaborate on opportunities. "
            "When enabled, you can define roles for team members, set record-level access, "
            "and view teams in list views and reports."
        ),
    )

    split_enabled = models.BooleanField(
        default=False,
        verbose_name=_("Enable Opportunity Splits"),
        help_text=_(
            "Allow multiple users to share credit for an opportunity. "
            "Splits can be based on revenue, overlay, or custom metrics."
        ),
    )

    allow_all_users_in_splits = models.BooleanField(
        default=False,
        verbose_name=_(
            "Let users add members to opportunity teams while editing splits"
        ),
        help_text=_(
            "When enabled, users can assign splits to any active user in the company, "
            "not just opportunity team members. This allows adding new members while editing splits."
        ),
    )

    class Meta:
        verbose_name = _("Opportunity Setting")
        verbose_name_plural = _("Opportunity Settings")
        unique_together = ("company",)

    def __str__(self):
        return "Opportunity Settings"

    @classmethod
    def get_settings(cls, company):
        """Get or create settings for the given company"""
        settings, created = cls.objects.get_or_create(
            company=company, defaults={"team_selling_enabled": False}
        )
        return settings

    @classmethod
    def is_team_selling_enabled(cls, company=None):
        """Quick check if team selling is enabled for a company"""
        request = getattr(_thread_local, "request", None)
        company = getattr(request, "active_company", None)
        settings = cls.objects.filter(company=company).first()
        return settings.team_selling_enabled if settings else False

    @classmethod
    def is_split_enabled(cls, company=None):
        """Quick check if splits are enabled for a company"""
        request = getattr(_thread_local, "request", None)
        company = getattr(request, "active_company", None)
        settings = cls.objects.filter(company=company).first()
        return settings.split_enabled if settings else False

    @classmethod
    def allow_all_users_in_splits_enabled(cls, company=None):
        """Quick check if all users can be added in splits for a company"""
        request = getattr(_thread_local, "request", None)
        company = getattr(request, "active_company", None)
        settings = cls.objects.filter(company=company).first()
        return settings.allow_all_users_in_splits if settings else False

    def save(self, *args, **kwargs):
        """Override save to create default split types when splits are enabled"""
        is_new = self.pk is None
        old_split_enabled = None

        if not is_new:
            try:
                old_instance = OpportunitySettings.objects.get(pk=self.pk)
                old_split_enabled = old_instance.split_enabled
            except OpportunitySettings.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Create default split types when splits are enabled for the first time
        if self.split_enabled and (is_new or old_split_enabled is False):
            self._create_default_split_types()

    def _create_default_split_types(self):
        """Create Revenue and Overlay split types"""
        OpportunitySplitType.objects.get_or_create(
            company=self.company,
            split_label=_("Expected Revenue Overlay"),
            defaults={
                "split_field": "expected_revenue",
                "totals_100_percent": False,
                "is_active": False,
            },
        )
        OpportunitySplitType.objects.get_or_create(
            company=self.company,
            split_label=_("Expected Revenue"),
            defaults={
                "split_field": "expected_revenue",
                "totals_100_percent": True,
                "is_active": False,
            },
        )

        OpportunitySplitType.objects.get_or_create(
            company=self.company,
            split_label=_("Overlay"),
            defaults={
                "split_field": "amount",
                "totals_100_percent": False,
            },
        )
        OpportunitySplitType.objects.get_or_create(
            company=self.company,
            split_label=_("Revenue"),
            defaults={
                "split_field": "amount",
                "totals_100_percent": True,
            },
        )


class OpportunitySplitType(HorillaCoreModel):
    """
    Defines split types (Revenue, Overlay, etc.) - Similar to Salesforce Split Types Setup.
    Each split type can be configured to total 100% or allow overlays.
    """

    split_label = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("Split Label"),
        help_text=_("Name of the split type (e.g., Revenue, Overlay)"),
    )

    split_field = models.CharField(
        max_length=100,
        default="amount",
        verbose_name=_("Split Field"),
        help_text=_("Field to split: amount, expected_revenue, etc."),
        choices=[
            ("amount", _("Opportunity - Amount")),
            ("expected_revenue", _("Opportunity - Expected Revenue")),
        ],
    )

    totals_100_percent = models.BooleanField(
        default=True,
        verbose_name=_("Totals 100%"),
        help_text=_("Require splits of this type to total exactly 100%"),
    )

    class Meta:
        verbose_name = _("Opportunity Split Type")
        verbose_name_plural = _("Opportunity Split Types")
        unique_together = ("company", "split_field", "totals_100_percent")

    def __str__(self):
        return str(self.split_label)

    def is_active_col(self):

        html = render_template(
            path="opportunity_split/is_active_col.html", context={"instance": self}
        )

        return mark_safe(html)

    @property
    def is_overlay(self):
        """Overlay splits don't require 100% total."""
        return not self.totals_100_percent


class OpportunitySplit(HorillaCoreModel):
    """
    Represents credit splits for each Opportunity.
    Each record indicates how much credit (percentage or amount)
    a user receives for an opportunity under a given split type.
    """

    opportunity = models.ForeignKey(
        "opportunities.Opportunity",
        on_delete=models.CASCADE,
        related_name="splits",
        verbose_name=_("Opportunity"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="opportunity_splits",
        verbose_name=_("Team Member"),
        help_text=_("User receiving credit for this split."),
    )

    split_type = models.ForeignKey(
        "opportunities.OpportunitySplitType",
        on_delete=models.CASCADE,
        related_name="splits",
        verbose_name=_("Split Type"),
        help_text=_("Type of split, such as Revenue or Overlay."),
    )

    split_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Split Percentage"),
        help_text=_("Percentage of total credit (e.g., 25.00 for 25%)."),
    )

    split_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Split Amount"),
        help_text=_(
            "Calculated split amount based on percentage and opportunity amount."
        ),
    )

    def actions(self):
        """
        This method for get custom column for action.
        """
        disabled = False
        if self.user == self.opportunity.owner and self.split_type.totals_100_percent:
            disabled = True

        return render_template(
            path="opportunity_split/actions.html",
            context={
                "instance": self,
                "disabled": disabled,
            },
        )


class BigDealAlert(HorillaCoreModel):
    """Model to store Big Deal Alert configuration."""

    alert_name = models.CharField(max_length=255, verbose_name=_("Alert Name"))

    trigger_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=0.00, verbose_name=_("Trigger Amount")
    )

    trigger_probability = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Trigger Probability"),
        help_text=_(
            "Trigger alert when opportunity probability reaches this percentage"
        ),
    )

    sender_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("Sender Name")
    )
    sender_email = models.EmailField(
        blank=True, null=True, verbose_name=_("Sender Email")
    )

    notify_emails = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Notify Emails"),
        help_text=_("Comma-separated emails to notify"),
    )
    notify_cc_emails = models.TextField(
        blank=True, null=True, verbose_name=_("Notify CC Emails")
    )
    notify_bcc_emails = models.TextField(
        blank=True, null=True, verbose_name=_("Notify BCC Emails")
    )

    notify_opportunity_owner = models.BooleanField(
        default=False, verbose_name=_("Notify Opportunity Owner")
    )
    active = models.BooleanField(
        default=False, verbose_name=_("Active")
    )  # Add active field

    class Meta:
        """Meta options for BigDealAlert model."""

        verbose_name = _("Big Deal Alert")
        verbose_name_plural = _("Big Deal Alerts")

    def __str__(self):
        return str(self.alert_name)

    def notify_email_list(self):
        """Return a list of primary notification emails."""
        return [email.strip() for email in self.notify_emails.split(",")]

    def notify_cc_emails_list(self):
        """Return a list of CC notification emails."""
        return [email.strip() for email in self.notify_cc_emails.split(",")]

    def notify_bcc_emails_list(self):
        """Return a list of BCC notification emails."""
        return [email.strip() for email in self.notify_bcc_emails.split(",")]

    def active_return(self):
        """Return 'Yes' if opportunity owner is notified, else 'No'."""
        return "Yes" if self.notify_opportunity_owner else "No"

    def probality_return(self):
        """Return the trigger probability as a percentage string."""
        return f"{self.trigger_probability} %"
