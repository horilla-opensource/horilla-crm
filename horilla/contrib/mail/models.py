"""Models for Horilla Mail App"""

# Standard library imports
import mimetypes
import re
import uuid

# Third-party imports (Django)
from django.conf import settings
from django.template import engines

from horilla.contrib.core.models import HorillaContentType, HorillaCoreModel
from horilla.contrib.utils.methods import (
    render_template,
    sanitize_html,
    sanitize_plain_text,
)
from horilla.contrib.utils.middlewares import _thread_local
from horilla.core.exceptions import ValidationError

# First-party imports (Horilla)
from horilla.db import models
from horilla.registry.limiters import limit_content_types
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _
from horilla.utils.upload import upload_path

from .encryption_utils import decrypt_password

# Local imports
from .fields import EncryptedCharField


class HorillaMailConfiguration(HorillaCoreModel):
    """
    SingletonModel to keep the mail server configurations
    """

    TYPE_CHOICES = [
        ("mail", _("Mail")),
        ("outlook", _("Outlook")),
    ]

    MAIL_CHANNELS = [
        ("incoming", _("Incoming")),
        ("outgoing", _("Outgoing")),
    ]

    type = models.CharField(
        max_length=255, choices=TYPE_CHOICES, verbose_name=_("Type")
    )
    mail_channel = models.CharField(
        max_length=20,
        choices=MAIL_CHANNELS,
        db_index=True,
        verbose_name=_("Mail Channel"),
        help_text=_(
            _(
                "Specifies whether this configuration handles incoming,"
                "outgoing, or both types of emails."
            )
        ),
    )

    host = models.CharField(
        null=True, max_length=256, verbose_name=_("Host"), blank=True
    )
    port = models.SmallIntegerField(null=True, verbose_name=_("Port"), blank=True)
    from_email = models.EmailField(
        null=True, max_length=256, verbose_name=_("Default From Mail")
    )

    username = models.CharField(
        null=True, max_length=256, verbose_name=_("Email Host Username"), blank=True
    )

    display_name = models.CharField(
        null=True,
        max_length=256,
        verbose_name=_("Display Name"),
    )
    password = EncryptedCharField(
        null=True,
        max_length=512,
        verbose_name=_("Email Authentication Password"),
        blank=True,
    )

    use_tls = models.BooleanField(
        default=True, verbose_name=_("Use TLS"), blank=True, null=True
    )

    use_ssl = models.BooleanField(
        default=False, verbose_name=_("Use SSL"), blank=True, null=True
    )

    fail_silently = models.BooleanField(
        default=False, verbose_name=_("Fail Silently"), blank=True, null=True
    )

    is_primary = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Primary Mail Server")
    )
    use_dynamic_display_name = models.BooleanField(
        default=True,
        verbose_name=_("Dynamic Display Name"),
        help_text=_(
            _("By enabling this the display name will take from who triggered the mail")
        ),
    )

    timeout = models.SmallIntegerField(
        null=True, verbose_name=_("Email Send Timeout (seconds)")
    )

    outlook_client_id = models.CharField(
        max_length=200, verbose_name=_("Client ID"), blank=True, null=True
    )
    outlook_client_secret = EncryptedCharField(
        max_length=512, verbose_name=_("Client Secret"), blank=True, null=True
    )
    outlook_tenant_id = models.CharField(
        max_length=200, verbose_name=_("Tenant ID"), blank=True, null=True
    )
    outlook_redirect_uri = models.URLField(
        verbose_name=_("Redirect URI"), blank=True, null=True
    )
    outlook_authorization_url = models.URLField(
        verbose_name=_("OAuth Authorization Endpoint"), blank=True, null=True
    )
    outlook_token_url = models.URLField(
        verbose_name=_("OAuth Token Endpoint"), blank=True, null=True
    )
    outlook_api_endpoint = models.URLField(
        verbose_name=_("Microsoft Graph API Endpoint"), blank=True, null=True
    )
    token = models.JSONField(default=dict, blank=True, null=True)
    oauth_state = models.CharField(
        editable=False, max_length=100, null=True, blank=True
    )
    last_refreshed = models.DateTimeField(
        null=True, editable=False, blank=True, verbose_name=_("Token Last Refreshed")
    )

    def __init__(self, *args, **kwargs):
        """Initialize the model instance."""
        super().__init__(*args, **kwargs)
        self._saving = False

    def custom_actions(self):
        """Return custom action buttons for the admin interface."""
        return render_template(path="mail_actions.html", context={"instance": self})

    def get_detail_url(self):
        """Return the detail modal URL for this mail configuration."""
        return reverse_lazy("mail:mail_config_detail_view", kwargs={"pk": self.pk})

    def get_edit_url(self):
        """Return the edit URL based on channel and type."""
        if self.type == "outlook":
            return reverse_lazy(
                "mail:outlook_mail_server_update_view", kwargs={"pk": self.pk}
            )
        if self.mail_channel == "incoming":
            return reverse_lazy(
                "mail:incoming_mail_server_update_view", kwargs={"pk": self.pk}
            )
        return reverse_lazy("mail:mail_server_update_view", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """Return the delete URL for this mail configuration."""
        return reverse_lazy("mail:mail_server_delete_view", kwargs={"pk": self.pk})

    def clean(self):
        """Validate that company is set when the configuration is not primary."""
        if not self.company and not self.is_primary:
            raise ValidationError({"company": _("This field is required")})

    def __str__(self):
        return str(self.username)

    def get_decrypted_password(self):
        """
        Get decrypted password.
        """
        if self.password:
            return decrypt_password(self.password)
        return None

    def get_decrypted_client_secret(self):
        """
        Get decrypted Outlook client secret - ONLY for OAuth operations.
        """
        if self.outlook_client_secret:
            return decrypt_password(self.outlook_client_secret)
        return None

    def save(self, *args, **kwargs):
        """
        Enforce only one primary mail configuration across the system.
        Automatically makes the first entry primary.
        """
        if self._saving:
            return super().save(*args, **kwargs)

        self._saving = True
        try:
            if self.type == "outlook" and not self.from_email and self.username:
                self.from_email = self.username
            if not HorillaMailConfiguration.objects.exclude(pk=self.pk).exists():
                self.is_primary = True
            elif self.is_primary:
                HorillaMailConfiguration.objects.exclude(pk=self.pk).filter(
                    is_primary=True
                ).update(is_primary=False)
            return super().save(*args, **kwargs)
        finally:
            self._saving = False

    class Meta:
        """Meta options for the mail configuration model."""

        verbose_name = _("Mail Configuration")
        verbose_name_plural = _("Mail Configurations")


class HorillaMail(HorillaCoreModel):
    """
    Model to store each email details
    """

    MAIL_STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("scheduled", _("Scheduled")),
        ("sent", _("Sent")),
        ("delivered", _("Delivered")),
        ("bounced", _("Bounced")),
        ("opened", _("Opened")),
        ("failed", _("Failed")),
    ]

    sender = models.ForeignKey(
        HorillaMailConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_mails",
        verbose_name=_("From"),
    )

    to = models.TextField(
        help_text=_("Comma separated recipient email addresses"),
        verbose_name=_("Send To"),
        blank=True,  # Allow blank for drafts, validate when sending
    )
    cc = models.TextField(blank=True, null=True, verbose_name=_("Cc"))
    bcc = models.TextField(blank=True, null=True, verbose_name=_("Bcc"))
    subject = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("Subject")
    )
    body = models.TextField(blank=True, null=True, verbose_name=_("Body"))
    rendered_subject = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Rendered subject saved at send time."),
    )
    rendered_body = models.TextField(
        blank=True,
        null=True,
        help_text=_("Rendered body saved at send time."),
    )
    content_type = models.ForeignKey(HorillaContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    related_to = models.GenericForeignKey("content_type", "object_id")
    mail_status = models.CharField(
        max_length=20,
        choices=MAIL_STATUS_CHOICES,
        default="draft",
        db_index=True,
        verbose_name=_("Mail Status"),
    )
    mail_status_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Sent At"))
    delivered_at = models.DateTimeField(blank=True, null=True)
    bounced_at = models.DateTimeField(blank=True, null=True)
    opened_at = models.DateTimeField(blank=True, null=True)
    tracking_uid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, null=True, blank=True
    )
    scheduled_at = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        help_text=_("When the mail should be sent (for scheduled mails)."),
    )
    send_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_mails_by",
        verbose_name=_("Sent By"),
    )

    def __str__(self):
        return f"[{self.mail_status}] {self.subject}"

    def render_subject(self, context=None):
        """
        Render the subject template with the given context.
        Sanitizes output to remove newlines/carriage returns (RFC 5322 prohibits
        these in email header values).
        """

        if not context:
            request = getattr(_thread_local, "request", None)
            context = {
                "instance": self.related_to,
                "user": getattr(request, "user", None),
                "active_company": request.active_company,
                "request": request,
            }
        django_engine = engines["django"]
        template_str = (self.subject or "").strip()
        if template_str:
            template_str = "{% load horilla_tags %}\n" + template_str
        rendered = django_engine.from_string(template_str).render(context)
        # Remove newlines/carriage returns - RFC 5322 forbids them in headers
        return re.sub(r"\s+", " ", rendered).strip()

    def render_body(self, context=None):
        """
        Render the body template with the given context.
        """

        if not context:
            request = getattr(_thread_local, "request", None)
            context = {
                "instance": self.related_to,
                "user": getattr(request, "user", None),
                "active_company": request.active_company,
                "request": request,
            }
        django_engine = engines["django"]
        template_str = (self.body or "").strip()
        if template_str:
            template_str = "{% load horilla_tags %}\n" + template_str
        return django_engine.from_string(template_str).render(context)

    def clean(self):
        """Sanitize XSS content from mail fields."""
        if self.subject:
            self.subject = sanitize_plain_text(self.subject)
        if self.body:
            self.body = sanitize_html(self.body)

    def save(self, *args, **kwargs):
        """Override save to ensure clean() is called for validation."""
        # Set updated_by before validation (parent save will also set it, but we need it for validation)
        request = getattr(_thread_local, "request", None)
        if request:
            user = getattr(request, "user", None)
            if user and not user.is_anonymous:
                if not self.pk:
                    # New object - set both created_by and updated_by
                    if not self.created_by:
                        self.created_by = user
                    self.updated_by = user
                else:
                    # Existing object - only update updated_by
                    self.updated_by = user

        # Only validate if required fields are set (to avoid validation errors for drafts)
        # For drafts, to field might be empty, so we skip full_clean for drafts
        if self.mail_status != "draft" or self.to:
            # Validate before saving (only if not a draft or if to is set)
            self.full_clean()
        else:
            # For drafts with empty to, just call clean() for XSS validation
            self.clean()

        return super().save(*args, **kwargs)

    def get_edit_url(self):
        """
        Get the URL to edit this mail.
        """
        return reverse_lazy("mail:send_mail_draft_view", kwargs={"pk": self.pk})

    def get_view_url(self):
        """
        Get the URL to view this mail.
        """
        return reverse_lazy("mail:sent_preview_mail", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """
        Get the URL to delete this mail.
        """
        return reverse_lazy("mail:mail_delete", kwargs={"pk": self.pk})

    def get_reschedule_url(self):
        """
        Get the URL to reschedule this mail.
        """
        return reverse_lazy("mail:reschedule_mail_form", kwargs={"pk": self.pk})

    class Meta:
        """Meta options for the mail model."""

        verbose_name = _("Mail")
        verbose_name_plural = _("Mails")


class HorillaMailAttachment(HorillaCoreModel):
    """Each email can have multiple attachments."""

    mail = models.ForeignKey(
        HorillaMail, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to=upload_path)
    file_size = models.PositiveIntegerField(blank=True, null=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    is_inline = models.BooleanField(default=False)
    content_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Attachment for Mail {self.mail.id}: {self.file.name}"

    def file_name(self):
        """Return the name of the file."""
        return self.file.name.split("/")[-1]

    def save(self, *args, **kwargs):
        """Automatically populate file_size and mime_type on save."""
        if self.file:
            self.file_size = self.file.size
            mime, _ = mimetypes.guess_type(self.file.name)
            self.mime_type = mime or "application/octet-stream"
        super().save(*args, **kwargs)

    class Meta:
        """Meta options for the mail attachment model."""

        verbose_name = _("Mail Attachment")
        verbose_name_plural = _("Mail Attachments")


class HorillaMailTemplate(HorillaCoreModel):
    """Model to store mail templates."""

    title = models.CharField(max_length=100, verbose_name=_("Template Title"))
    subject = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Subject"),
    )
    body = models.TextField(verbose_name=_("Body"))
    content_type = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to=limit_content_types("mail_template_models"),
        verbose_name=_("Related Model"),
    )

    def __str__(self) -> str:
        return f"{self.title}"

    class Meta:
        """Meta options for the mail template model."""

        verbose_name = _("Mail Template")
        verbose_name_plural = _("Mail Templates")
        unique_together = ["title", "company"]

    def get_edit_url(self):
        """Get the URL to edit this mail template."""
        return reverse_lazy("mail:mail_template_update_view", kwargs={"pk": self.pk})

    def get_delete_url(self):
        """Get the URL to delete this mail template."""
        return reverse_lazy("mail:mail_template_delete_view", kwargs={"pk": self.pk})

    def get_detail_view_url(self):
        """Get the URL to view this mail template."""
        return reverse_lazy("mail:mail_template_detail_view", kwargs={"pk": self.pk})

    def get_related_model(self):
        """Return the related model's verbose name."""
        if self.content_type:
            return self.content_type.model_class()._meta.verbose_name.title()
        return "General"

    def clean(self):
        """Sanitize XSS content from mail fields."""
        if self.subject:
            self.subject = sanitize_plain_text(self.subject)
        if self.body:
            self.body = sanitize_html(self.body)

    def save(self, *args, **kwargs):
        """Override save to ensure clean() is called for validation."""
        self.full_clean()
        return super().save(*args, **kwargs)
