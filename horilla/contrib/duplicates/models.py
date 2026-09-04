"""
Models for the duplicates app
"""

# First party imports (Horilla)
from horilla.contrib.core.models import HorillaContentType, HorillaCoreModel

# First party imports (Horilla)
from horilla.core.exceptions import ValidationError
from horilla.db import models
from horilla.urls import reverse_lazy
from horilla.utils.choices import OPERATOR_CHOICES
from horilla.utils.translation import gettext_lazy as _

# Local imports
from .methods import limit_content_types

# Create your duplicates models here.


class MatchingRule(HorillaCoreModel):
    """
    Defines rules for matching potential duplicate records
    """

    MATCHING_METHOD_CHOICES = [
        ("exact", _("Exact Match")),
        ("fuzzy", _("Fuzzy Match")),
        ("phonetic", _("Phonetic Match")),
        ("edit_distance", _("Edit Distance")),
    ]

    name = models.CharField(max_length=255, unique=True, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    content_type = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        limit_choices_to=limit_content_types,
        help_text=_("The model this matching rule applies to"),
        verbose_name=_("Module"),
    )

    class Meta:
        """Meta options for MatchingRule."""

        verbose_name = _("Matching Rule")
        verbose_name_plural = _("Matching Rules")

    def __str__(self):
        return f"{self.name} ({self.content_type.model})"


class MatchingRuleCriteria(HorillaCoreModel):
    """
    Individual criteria/conditions for a matching rule
    Defines which fields to compare and how
    """

    MATCHING_METHOD_CHOICES = [
        ("exact", _("Exact")),
        ("fuzzy", _("Fuzzy")),
    ]

    matching_rule = models.ForeignKey(
        MatchingRule,
        on_delete=models.CASCADE,
        related_name="criteria",
        verbose_name=_("Matching Rule"),
    )
    field_name = models.CharField(
        max_length=100, verbose_name=_("Field"), help_text=_("Field name to match on")
    )
    matching_method = models.CharField(
        max_length=30,
        choices=MATCHING_METHOD_CHOICES,
        default="exact",
        verbose_name=_("Matching Method"),
    )
    match_blank_fields = models.BooleanField(
        default=False,
        verbose_name=_("Match Blank Fields"),
        help_text=_("If checked, blank fields will be considered a match"),
    )
    order = models.IntegerField(default=0, help_text=_("Order of evaluation"))

    class Meta:
        """Meta options for MatchingRuleCriteria."""

        verbose_name = _("Matching Criterion")
        verbose_name_plural = _("Matching Criteria")
        unique_together = [["matching_rule", "field_name"]]

    def __str__(self):
        return f"{self.matching_rule.name} - {self.field_name} ({self.matching_method})"


class DuplicateRule(HorillaCoreModel):
    """
    Defines actions to take when duplicates are detected
    """

    ACTION_CHOICES = [
        ("allow", _("Allow")),
        ("block", _("Block")),
    ]

    name = models.CharField(max_length=255, unique=True, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    content_type = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        help_text=_("The model this duplicate rule applies to"),
        limit_choices_to=limit_content_types,
        verbose_name=_("Module"),
    )
    matching_rule = models.ForeignKey(
        MatchingRule,
        on_delete=models.CASCADE,
        related_name="duplicate_rules",
        help_text=_("The matching rule to use for detection"),
        verbose_name=_("Matching Rule"),
    )

    action_on_create = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        default="allow",
        verbose_name=_("Action on Create"),
    )
    action_on_edit = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        default="allow",
        verbose_name=_("Action on Edit"),
    )

    # Alert settings (used when action is 'allow')
    alert_title = models.CharField(
        max_length=255,
        default="Potential Duplicate Detected",
        help_text=_("Title shown in the alert dialog"),
        verbose_name=_("Alert Title"),
    )
    alert_message = models.TextField(
        default="Similar records found. Do you want to proceed?",
        help_text=_("Message to show in alert when duplicates are detected"),
        verbose_name=_("Alert Message"),
    )
    show_duplicate_records = models.BooleanField(
        default=True,
        help_text=_("Show list of potential duplicates in the alert"),
        verbose_name=_("Show Duplicate Records"),
    )

    class Meta:
        """Meta options for DuplicateRule."""

        verbose_name = _("Duplicate Rule")
        verbose_name_plural = _("Duplicate Rules")

    def __str__(self):
        return f"{self.name} ({self.content_type.model})"

    def clean(self):
        """Ensure the matching rule applies to the same content type as this rule."""
        if not self.matching_rule_id or not self.content_type_id:
            return
        if self.matching_rule.content_type_id != self.content_type_id:
            raise ValidationError(
                "Matching rule must apply to the same content type as duplicate rule"
            )

    def get_edit_url(self):
        """
        This method to get edit url
        """
        return reverse_lazy(
            "duplicates:duplicate_rule_update_view", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        This method to get delete url
        """
        return reverse_lazy(
            "duplicates:duplicate_rule_delete_view", kwargs={"pk": self.pk}
        )

    def get_detail_view_url(self):
        """
        This method to get detail view url
        """
        return reverse_lazy(
            "duplicates:duplicate_rule_detail_view", kwargs={"pk": self.pk}
        )


class DuplicateRuleCondition(HorillaCoreModel):
    """
    Defines optional conditions that a record must meet for the duplicate rule to run
    """

    duplicate_rule = models.ForeignKey(
        DuplicateRule,
        on_delete=models.CASCADE,
        related_name="conditions",
        verbose_name=_("Duplicate Rule"),
    )

    field = models.CharField(
        max_length=100,
        verbose_name=_("Field Name"),
        help_text=_("Field name to evaluate"),
    )
    operator = models.CharField(
        max_length=50,
        choices=OPERATOR_CHOICES,
        verbose_name=_("Operator"),
    )
    value = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Value"),
        help_text=_("Value to compare against"),
    )
    logical_operator = models.CharField(
        max_length=10,
        choices=[
            ("and", _("AND")),
            ("or", _("OR")),
        ],
        default="and",
        verbose_name=_("Logical Operator"),
        help_text=_("How to combine with next condition"),
    )
    order = models.IntegerField(default=0, help_text=_("Order of evaluation"))

    class Meta:
        """Meta options for DuplicateRuleCondition."""

        verbose_name = _("Duplicate Rule Condition")
        verbose_name_plural = _("Duplicate Rule Conditions")
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.duplicate_rule.name} - {self.field} {self.operator} {self.value}"
