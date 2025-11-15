import mimetypes
import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from horilla_core.models import HorillaContentType, HorillaCoreModel, upload_path
from horilla_mail.encryption_utils import decrypt_password
from horilla_mail.fields import EncryptedCharField
from horilla_mail.methods import limit_content_types
from horilla_utils.methods import render_template
from horilla_utils.middlewares import _thread_local


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
        verbose_name=_("Mail Channel"),
        help_text=_(
            _(
                "Specifies whether this configuration handles incoming, outgoing, or both types of emails."
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
        default=False, verbose_name=_("Primary Mail Server")
    )
    use_dynamic_display_name = models.BooleanField(
        default=True,
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
        verbose_name=_("Redirect URi"), blank=True, null=True
    )
    outlook_authorization_url = models.URLField(
        verbose_name=_("OAuth authorization endpoint"), blank=True, null=True
    )
    outlook_token_url = models.URLField(
        verbose_name=_("OAuth token endpoint"), blank=True, null=True
    )
    outlook_api_endpoint = models.URLField(
        verbose_name=_("Microsoft Graph API endpoint"), blank=True, null=True
    )
    token = models.JSONField(default=dict, blank=True, null=True)
    oauth_state = models.CharField(
        editable=False, max_length=100, null=True, blank=True
    )
    last_refreshed = models.DateTimeField(null=True, editable=False, blank=True)

    def custom_actions(self):
        return render_template(path="mail_actions.html", context={"instance": self})

    def clean(self):
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
        if hasattr(self, "_saving"):
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
            super().save(*args, **kwargs)
        finally:
            del self._saving

    class Meta:
        verbose_name = _("Mail Configuration")
        verbose_name_plural = _("Mail Configurations")


class HorillaMail(HorillaCoreModel):
    MAIL_STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("scheduled", _("Scheduled")),
        ("sent", _("Sent")),
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
        help_text=_("Comma separated recipient email addresses"), verbose_name=_("To")
    )
    cc = models.TextField(blank=True, null=True, verbose_name=_("Cc"))
    bcc = models.TextField(blank=True, null=True, verbose_name=_("Bcc"))
    subject = models.CharField(
        max_length=255, blank=True, null=True, verbose_name=_("Subject")
    )
    body = models.TextField(blank=True, null=True, verbose_name=_("Body"))
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    related_to = GenericForeignKey("content_type", "object_id")
    mail_status = models.CharField(
        max_length=20, choices=MAIL_STATUS_CHOICES, default="draft"
    )
    mail_status_message = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    scheduled_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_("When the mail should be sent (for scheduled mails)."),
    )

    def __str__(self):
        return f"[{self.mail_status}] {self.subject }"

    def render_subject(self, context=None):
        from django.template import engines

        if not context:
            request = getattr(_thread_local, "request", None)
            context = {
                "instance": self.related_to,
                "user": getattr(request, "user", None),
                "active_company": request.active_company,
                "request": request,
            }
        django_engine = engines["django"]
        return django_engine.from_string(self.subject or "").render(context)

    def render_body(self, context=None):
        from django.template import engines

        if not context:
            request = getattr(_thread_local, "request", None)
            context = {
                "instance": self.related_to,
                "user": getattr(request, "user", None),
                "active_company": request.active_company,
                "request": request,
            }
        django_engine = engines["django"]
        return django_engine.from_string(self.body or "").render(context)

    def has_xss(value: str) -> bool:
        """Detect common XSS attempts (scripts, event handlers, js URLs, active content)."""
        if not isinstance(value, str):
            return False

        xss_patterns = [
            # <script> ... </script> with any attributes
            r"<\s*script[^>]*>.*?<\s*/\s*script\s*>",
            # Opening <script> tag (for incomplete scripts)
            r"<\s*script[^>]*>",
            r"javascript\s*:",  # javascript: pseudo-protocol
            r"javascript\s*:",  # javascript: pseudo-protocol
            r"on\w+\s*=",  # inline event handlers (onclick, onload, etc.)
            # dangerous active content
            r"<\s*(embed|object|iframe|svg|math|link|meta).*?>",
            # JS API abuse
            r"on\w+\s*=\s*['\"]?\s*(eval|setTimeout|setInterval|new\s+Function|XMLHttpRequest|fetch|\$\s*\()[^>]*",
        ]

        combined = re.compile("|".join(xss_patterns), re.IGNORECASE | re.DOTALL)
        result = bool(combined.search(value))
        return result

    def get_edit_url(self):
        return reverse_lazy("horilla_mail:send_mail_draft_view", kwargs={"pk": self.pk})

    def get_view_url(self):
        return reverse_lazy("horilla_mail:sent_preview_mail", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse_lazy("horilla_mail:horilla_mail_delete", kwargs={"pk": self.pk})

    def get_reschedule_url(self):
        return reverse_lazy("horilla_mail:reschedule_mail_form", kwargs={"pk": self.pk})

    class Meta:
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
        return self.file.name.split("/")[-1]

    def save(self, *args, **kwargs):
        """Automatically populate file_size and mime_type on save."""
        if self.file:
            self.file_size = self.file.size
            mime, _ = mimetypes.guess_type(self.file.name)
            self.mime_type = mime or "application/octet-stream"
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Mail Attachment")
        verbose_name_plural = _("Mail Attachments")


class HorillaMailTemplate(HorillaCoreModel):
    title = models.CharField(max_length=100, verbose_name=_("Template title"))
    body = models.TextField(verbose_name=_("Body"))
    content_type = models.ForeignKey(
        HorillaContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to=limit_content_types,
        verbose_name=_("Related Model"),
    )

    def __str__(self) -> str:
        return f"{self.title}"

    class Meta:
        verbose_name = _("Mail Template")
        verbose_name_plural = _("Mail Templates")
        unique_together = ["title", "company"]

    def get_edit_url(self):
        return reverse_lazy(
            "horilla_mail:mail_template_update_view", kwargs={"pk": self.pk}
        )

    def get_delete_url(self):
        return reverse_lazy(
            "horilla_mail:mail_template_delete_view", kwargs={"pk": self.pk}
        )

    def get_detail_view_url(self):
        return reverse_lazy(
            "horilla_mail:mail_template_detail_view", kwargs={"pk": self.pk}
        )

    def get_related_model(self):
        if self.content_type:
            return self.content_type.model_class()._meta.verbose_name.title()
        return "General"
