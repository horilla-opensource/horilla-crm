"""
Core models for the approvals app.

- ApprovalRule: one *approval process* (module, name, triggers).
- ApprovalProcessRule: one *rule* inside the process (criteria + approvers); multiple per process.
- ApprovalCondition / ApprovalStep: belong to a process rule.

These models stay generic so modules can register via the feature system.
"""

# Third-party imports (Django)
from django.conf import settings

# First party imports (Horilla)
from horilla.contrib.core.models import HorillaContentType, HorillaCoreModel
from horilla.contrib.utils.methods import render_template

# First party imports (Horilla)
from horilla.db import models
from horilla.registry.limiters import limit_content_types
from horilla.registry.permission_registry import permission_exempt_model
from horilla.urls import reverse, reverse_lazy
from horilla.utils.choices import OPERATOR_CHOICES
from horilla.utils.translation import gettext_lazy as _


class ApprovalRule(HorillaCoreModel):
    """
    Holds module, execution triggers for an approval process.
    Per-rule steps 3–6 live on ApprovalProcessRule.rule_config.
    """

    name = models.CharField(max_length=255, verbose_name=_("Name"))

    model = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        limit_choices_to=limit_content_types("approval_models"),
        related_name="approval_rules",
        help_text=_("Model this process applies to."),
        verbose_name=_("Module"),
    )

    description = models.TextField(blank=True)
    trigger_on_create = models.BooleanField(
        default=True,
        verbose_name=_("When Record Is Created"),
        help_text=_("Run this process when a new record is created."),
    )
    trigger_on_edit = models.BooleanField(
        default=False,
        verbose_name=_("When Record Is Edited"),
        help_text=_("Run this process when a record is edited."),
    )

    def get_detail_url(self):
        """Return the URL for the approval process detail view."""
        return reverse_lazy(
            "approvals:approval_process_detail_view", kwargs={"pk": self.pk}
        )

    def get_edit_url(self):
        """Return the URL for the approval process edit view."""
        return reverse_lazy(
            "approvals:approval_process_update_view",
            kwargs={"pk": self.pk},
        )

    def get_delete_url(self):
        """Return the URL for the approval process delete view."""
        return reverse_lazy(
            "approvals:approval_process_delete_view",
            kwargs={"pk": self.pk},
        )

    def is_active_col(self):
        """Return HTML toggle for active status column."""
        if self.is_active:
            confirm_message = _(
                "Are you sure you want to deactivate this approval process?"
            )
        else:
            confirm_message = _(
                "Activating this will deactivate any other active approval "
                "process for the %(module)s module. Do you want to continue?"
            ) % {"module": self.model}
        return render_template(
            path="components/toggle_active_col.html",
            context={
                "instance": self,
                "toggle_url": reverse_lazy(
                    "approvals:approval_process_toggle_view", kwargs={"pk": self.pk}
                ),
                "confirm_message": confirm_message,
            },
        )

    def get_execute_display(self) -> str:
        """Human-readable 'Execute on'"""
        c, e = self.trigger_on_create, self.trigger_on_edit
        if c and e:
            return str(_("Create and Edit"))
        if c:
            return str(_("Create only"))
        if e:
            return str(_("Edit only"))
        return str(_("Not set"))

    class Meta:
        """Meta options for ApprovalRule."""

        verbose_name = _("Approval Process")
        verbose_name_plural = _("Approval Processes")

    def __str__(self) -> str:
        return str(self.name)


class ApprovalProcessRule(HorillaCoreModel):
    """
    One rule inside an approval process.

    Carries criteria, approvers, and per-rule steps 3–6 (actions, rejection, record rules, admins).
    """

    rule_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=_(
            "Per-rule JSON: approval_actions, rejection_actions, record_modification, "
            "process_admins (or rule-level admin overrides)."
        ),
    )

    approval_process = models.ForeignKey(
        ApprovalRule,
        on_delete=models.CASCADE,
        related_name="process_rules",
        verbose_name=_("Approval Process"),
    )
    order = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Order"),
        help_text=_("Sequence of this rule within the process."),
    )

    class Meta:
        """Meta options for ApprovalProcessRule."""

        verbose_name = _("Approval Process Rule")
        verbose_name_plural = _("Approval Process Rules")
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["approval_process", "order"],
                name="approvals_processrule_process_order_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.approval_process.name} — {_('Rule')} {self.order}"

    def get_criteria_edit_url(self):
        """Modal URL to edit this rule’s criteria only."""
        return reverse_lazy(
            "approvals:approval_process_rule_criteria_view",
            kwargs={"pk": self.pk},
        )

    def get_edit_url(self):
        """Modal URL to edit this rule with full form."""
        return reverse_lazy(
            "approvals:approval_process_rule_update_view",
            kwargs={"process_pk": self.approval_process_id, "pk": self.pk},
        )

    def get_delete_url(self):
        """Return the URL for the approval process rule delete view."""
        return reverse_lazy(
            "approvals:approval_process_rule_delete_view",
            kwargs={"pk": self.pk},
        )


class ApprovalStep(HorillaCoreModel):
    """
    One approval step (approver) within a process rule.
    """

    APPROVER_TYPE_CHOICES = [
        ("user", _("Specific user")),
        ("owner_manager", _("Manager of record owner")),
        ("role", _("Role")),
    ]

    approval_process_rule = models.ForeignKey(
        ApprovalProcessRule,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    order = models.PositiveIntegerField(
        help_text=_("Sequence order of this step within the rule.")
    )

    approver_type = models.CharField(
        max_length=32,
        choices=APPROVER_TYPE_CHOICES,
        default="user",
    )

    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_steps_as_user",
    )

    role_identifier = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Identifier for the role (implementation-specific)."),
    )

    class Meta:
        """Meta options for ApprovalStep."""

        verbose_name = _("Approval Step")
        verbose_name_plural = _("Approval Steps")
        ordering = ["order", "id"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.approval_process_rule.approval_process.name} – {_('step')} {self.order}"


@permission_exempt_model
class ApprovalCondition(HorillaCoreModel):
    """Criteria rows for a process rule."""

    approval_process_rule = models.ForeignKey(
        ApprovalProcessRule,
        on_delete=models.CASCADE,
        related_name="conditions",
        verbose_name=_("Process Rule"),
    )
    field = models.CharField(max_length=100, verbose_name=_("Field Name"))
    operator = models.CharField(
        max_length=50,
        choices=OPERATOR_CHOICES,
        verbose_name=_("Operator"),
    )
    value = models.CharField(max_length=255, blank=True, verbose_name=_("Value"))
    logical_operator = models.CharField(
        max_length=3,
        choices=[("and", _("AND")), ("or", _("OR"))],
        default="and",
        verbose_name=_("Logical Operator"),
    )
    order = models.PositiveIntegerField(default=0, verbose_name=_("Order"))

    class Meta:
        """Meta options for ApprovalCondition."""

        verbose_name = _("Approval Condition")
        verbose_name_plural = _("Approval Conditions")
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return (
            f"{self.approval_process_rule.approval_process.name}: "
            f"{self.field} {self.operator} {self.value}"
        )


class ApprovalInstance(HorillaCoreModel):
    """A running approval for one record (still tied to the process / ApprovalRule)."""

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
        ("cancelled", _("Cancelled")),
    ]

    rule = models.ForeignKey(
        ApprovalRule,
        on_delete=models.PROTECT,
        related_name="instances",
        verbose_name=_("Rule"),
    )

    content_type = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        limit_choices_to=limit_content_types("approval_models"),
        related_name="approval_instances",
    )
    object_id = models.CharField(
        max_length=64,
        help_text=_("Primary key of the target object, stored as string."),
    )
    content_object = models.GenericForeignKey("content_type", "object_id")

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_approvals",
    )

    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
        verbose_name=_("Status"),
    )

    current_step = models.ForeignKey(
        "ApprovalStep",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_instances",
        help_text=_("The step currently awaiting decision, if any."),
    )

    delegated_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delegated_approval_instances",
        help_text=_(
            "When set, overrides current_step's approver for this instance only, "
            "without altering the shared process rule's step configuration."
        ),
    )

    class Meta:
        """Meta options for ApprovalInstance."""

        verbose_name = _("Approval Instance")
        verbose_name_plural = _("Approval Instances")
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.get_status_display()} – {self.rule.name}"

    def get_review_url(self):
        """Return the URL for the approval job review view."""
        return reverse_lazy(
            "approvals:approval_job_review_view",
            kwargs={"pk": self.pk},
        )

    def get_respond_modal_url(self):
        """HTMX GET URL for the respond modal (approve/reject/delegate without full-page detail)."""
        return reverse(
            "approvals:approval_job_respond_modal_view",
            kwargs={"pk": self.pk},
        )

    def get_history_url(self):
        """Return the URL for the approval history detail view."""
        return reverse_lazy(
            "approvals:approval_history_detail_view",
            kwargs={"pk": self.pk},
        )

    def get_delete_url(self):
        """Return the URL for the approval history delete view."""
        return reverse_lazy(
            "approvals:approval_history_delete_view",
            kwargs={"pk": self.pk},
        )


class ApprovalDecision(HorillaCoreModel):
    """A single approve/reject decision on a step."""

    DECISION_CHOICES = [
        ("approve", _("Approve")),
        ("reject", _("Reject")),
    ]

    instance = models.ForeignKey(
        ApprovalInstance,
        on_delete=models.CASCADE,
        related_name="decisions",
        verbose_name=_("Instance"),
    )
    step = models.ForeignKey(
        ApprovalStep,
        on_delete=models.CASCADE,
        related_name="decisions",
        verbose_name=_("Step"),
    )

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_decisions",
        verbose_name=_("Decided By"),
    )

    decision = models.CharField(
        max_length=16,
        choices=DECISION_CHOICES,
        verbose_name=_("Decision"),
    )
    comment = models.TextField(blank=True, verbose_name=_("Comment"))

    decided_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Decided At"))

    class Meta:
        """Meta options for ApprovalDecision."""

        verbose_name = _("Approval Decision")
        verbose_name_plural = _("Approval Decisions")
        ordering = ["-decided_at", "-id"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.get_decision_display()} by {self.decided_by or 'N/A'}"
