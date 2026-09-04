"""
Models for the automations app
"""

# Third-party imports (Django)
from django.conf import settings

from horilla.contrib.core.models import HorillaContentType, HorillaCoreModel
from horilla.contrib.mail.models import HorillaMailConfiguration, HorillaMailTemplate
from horilla.contrib.notifications.models import NotificationTemplate
from horilla.core.exceptions import ValidationError

# First party imports (Horilla)
from horilla.db import models
from horilla.registry.limiters import limit_content_types
from horilla.registry.permission_registry import permission_exempt_model
from horilla.urls import reverse_lazy
from horilla.utils.choices import OPERATOR_CHOICES
from horilla.utils.html import format_html
from horilla.utils.translation import gettext_lazy as _

# Create your automations models here.
CONDITIONS = [
    ("equal", _("Equal (==)")),
    ("notequal", _("Not Equal (!=)")),
    ("lt", _("Less Than (<)")),
    ("gt", _("Greater Than (>)")),
    ("le", _("Less Than or Equal To (<=)")),
    ("ge", _("Greater Than or Equal To (>=)")),
    ("icontains", _("Contains")),
]


class HorillaAutomation(HorillaCoreModel):
    """
    MailAutoMation
    """

    choices = [
        ("on_create", _("On Create")),
        ("on_update", _("On Update")),
        ("on_create_or_update", _("Both Create and Update")),
        ("on_delete", _("On Delete")),
        ("scheduled", _("Scheduled (time-based)")),
    ]
    SEND_OPTIONS = [
        ("mail", _("Send as Mail")),
        ("notification", _("Send as Notification")),
        ("both", _("Send as Mail and Notification")),
    ]

    title = models.CharField(max_length=256, unique=True, verbose_name=_("Title"))
    method_title = models.CharField(
        max_length=100, editable=False, verbose_name=_("Method Title")
    )
    model = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        limit_choices_to=limit_content_types("automation_models"),
        verbose_name=_("Module"),
    )
    mail_to = models.TextField(
        verbose_name=_("Mail to/Notify To"),
        help_text=_(
            "Specify recipients for email/notifications. Supports:\n"
            "- Direct email: user@example.com\n"
            "- Self: 'self' (person who triggered)\n"
            "- Instance fields: 'instance.owner.email', 'instance.created_by', 'instance.owner'\n"
            "- Multiple: comma-separated (e.g., 'self, instance.owner.email, admin@example.com')\n\n"
            "For notifications: Use user fields directly (e.g., 'instance.owner') or email addresses.\n"
            "The system will find users by email if an email address is provided."
        ),
    )
    also_sent_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        verbose_name=_("Also Send To"),
    )

    mail_detail_choice = models.TextField(
        default="", editable=False, verbose_name=_("Mail Detail Choice")
    )
    trigger = models.CharField(
        max_length=20, choices=choices, verbose_name=_("Trigger")
    )
    mail_template = models.ForeignKey(
        HorillaMailTemplate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Mail Template"),
    )
    notification_template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Notification Template"),
    )
    mail_server = models.ForeignKey(
        HorillaMailConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"mail_channel": "outgoing"},
        verbose_name=_("Outgoing Mail Server"),
        help_text=_(
            "Select the mail server to use for sending emails. If not selected, the primary mail server will be used."
        ),
    )
    delivery_channel = models.CharField(
        default="mail",
        max_length=50,
        choices=SEND_OPTIONS,
        verbose_name=_("Choose Delivery Channel"),
    )

    schedule_date_field = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Target Date Field"),
        help_text=_(
            "The date field on the record to schedule around (e.g., 'close_date', 'due_date'). "
            "Required for scheduled automations."
        ),
    )
    schedule_offset_amount = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Adjust By"),
        help_text=_(
            "How many days/weeks/months away from the Target Date.\n"
            "Use 0 to send on the same day."
        ),
    )
    schedule_offset_direction = models.CharField(
        max_length=10,
        blank=True,
        choices=[("before", _("Before")), ("after", _("After"))],
        verbose_name=_("Timing"),
        help_text=_(
            "Before = send earlier than the Target Date.\n"
            "After = send later than the Target Date."
        ),
    )
    schedule_offset_unit = models.CharField(
        max_length=16,
        blank=True,
        choices=[("days", _("Days")), ("weeks", _("Weeks")), ("months", _("Months"))],
        verbose_name=_("Offset Unit"),
        help_text=_("Choose Days, Weeks, or Months."),
    )
    schedule_run_time = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Run Time"),
        help_text=_("Optional. Leave empty to run whenever the scheduler runs."),
    )

    class Meta:
        """
        Meta class for HorillaAutomation model
        """

        verbose_name = _("Mail and Notification")
        verbose_name_plural = _("Mail and Notifications")

    def get_template(self):
        """
        Returns the template content based on the selected delivery channel.
        """
        templates = {
            "mail": self.mail_template,
            "notification": self.notification_template,
        }

        if self.delivery_channel in templates:
            return templates[self.delivery_channel]

        return format_html(
            "Mail Template: {}<br>Notification Template: {}",
            self.mail_template,
            self.notification_template,
        )

    def clean(self):
        """Validate template fields based on delivery_channel."""
        super().clean()
        # Validate scheduled configuration if trigger is scheduled
        if getattr(self, "trigger", None) == "scheduled":
            errors = {}
            if not self.schedule_date_field:
                errors["schedule_date_field"] = _(
                    "This field is required when Trigger is 'Scheduled'."
                )
            if self.schedule_offset_amount is None:
                errors["schedule_offset_amount"] = _(
                    "This field is required when Trigger is 'Scheduled'."
                )
            if not self.schedule_offset_direction:
                errors["schedule_offset_direction"] = _(
                    "This field is required when Trigger is 'Scheduled'."
                )
            if not self.schedule_offset_unit:
                errors["schedule_offset_unit"] = _(
                    "This field is required when Trigger is 'Scheduled'."
                )
            if errors:
                raise ValidationError(errors)

        if (
            self.delivery_channel == "notification"
            and not self.notification_template_id
        ):
            raise ValidationError(
                {
                    "notification_template": _(
                        "Notification template is required when delivery channel is "
                        "'Send as Notification'."
                    )
                }
            )
        if self.delivery_channel == "mail":
            if not self.mail_template_id:
                raise ValidationError(
                    {
                        "mail_template": _(
                            "Mail template is required when delivery channel is "
                            "'Send as Mail'."
                        )
                    }
                )
            if not self.mail_server_id:
                raise ValidationError(
                    {
                        "mail_server": _(
                            "Outgoing mail server is required when delivery channel is "
                            "'Send as Mail'."
                        )
                    }
                )
        if self.delivery_channel == "both":
            if not self.mail_template_id:
                raise ValidationError(
                    {
                        "mail_template": _(
                            "Mail template is required when delivery channel is "
                            "'Send as Mail and Notification'."
                        )
                    }
                )
            if not self.notification_template_id:
                raise ValidationError(
                    {
                        "notification_template": _(
                            "Notification template is required when delivery channel is "
                            "'Send as Mail and Notification'."
                        )
                    }
                )
            if not self.mail_server_id:
                raise ValidationError(
                    {
                        "mail_server": _(
                            "Outgoing mail server is required when delivery channel is "
                            "'Send as Mail and Notification'."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.pk:
            self.method_title = self.title.replace(" ", "_").lower()
        return super().save(*args, **kwargs)

    def get_edit_url(self):
        """
        Get the URL to edit this automation.
        """
        return reverse_lazy(
            "automations:automation_update_view", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        """
        Get the URL to delete this automation.
        """
        return reverse_lazy(
            "automations:automation_delete_view", kwargs={"pk": self.pk}
        )

    def __str__(self) -> str:
        return str(self.title)


@permission_exempt_model
class AutomationCondition(HorillaCoreModel):
    """
    Defines filtering conditions for automations
    """

    automation = models.ForeignKey(
        HorillaAutomation,
        on_delete=models.CASCADE,
        related_name="conditions",
        verbose_name=_("Automation"),
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
        """Meta options for AutomationCondition model."""

        verbose_name = _("Automation Condition")
        verbose_name_plural = _("Automation Conditions")
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.automation.title} - {self.field} {self.operator} {self.value}"


@permission_exempt_model
class AutomationRunLog(HorillaCoreModel):
    """
    Keeps track of scheduled automation executions to prevent duplicates.

    We log both:
    - run_date: when the task ran (today)
    - scheduled_for: the target date value the instance matched (e.g., close_date)
    This allows re-running when the instance date changes (e.g., close_date updated).
    """

    automation = models.ForeignKey(
        HorillaAutomation,
        on_delete=models.CASCADE,
        related_name="run_logs",
        verbose_name=_("Automation"),
    )
    content_type = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content Type"),
    )
    object_id = models.CharField(max_length=64, verbose_name=_("Object ID"))
    run_date = models.DateField(verbose_name=_("Run Date"))
    scheduled_for = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Scheduled For"),
        help_text=_(
            "The instance date value that matched when this automation executed."
        ),
    )

    class Meta:
        """Meta options for AutomationRunLog model."""

        verbose_name = _("Automation Run Log")
        verbose_name_plural = _("Automation Run Logs")
        unique_together = ("automation", "content_type", "object_id", "scheduled_for")

    def __str__(self) -> str:
        return f"{self.automation_id}:{self.content_type_id}:{self.object_id}@{self.run_date}"
