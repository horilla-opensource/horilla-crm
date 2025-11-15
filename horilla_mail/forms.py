from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _

from horilla.registry.permission_registry import PERMISSION_EXEMPT_MODELS
from horilla_generics.forms import HorillaModelForm, PasswordInputWithEye
from horilla_mail.models import HorillaMailConfiguration, HorillaMailTemplate


# Define your horilla_mail forms here
class DynamicMailTestForm(forms.Form):
    """
    Form for testing email configuration
    """

    to_email = forms.EmailField(
        label=_("To Email"),
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Enter email address to send test email"),
                "required": True,
            }
        ),
        help_text=_("Enter the email address where you want to send the test email."),
    )

    def clean_to_email(self):
        """
        Validate the email address
        """
        email = self.cleaned_data.get("to_email")
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise forms.ValidationError(_("Please enter a valid email address."))
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add Bootstrap classes or custom styling if needed
        for field_name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control"})


class HorillaMailTemplateForm(forms.ModelForm):
    """Form for creating and editing Horilla Mail Templates"""

    class Meta:
        model = HorillaMailTemplate
        fields = ["title", "content_type", "body", "company"]

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if not title or title.strip() == "":
            raise ValidationError("Template title is required.")
        return title.strip()

    def clean_body(self):
        body = self.cleaned_data.get("body")
        if not body or body.strip() == "":
            raise ValidationError("Template body is required.")
        return body


class MailTemplateSelectForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=HorillaMailTemplate.objects.none(),
        label="Select Mail Template",
        empty_label="Choose a template",
        required=True,
        widget=forms.Select(attrs={"class": "js-example-basic-single headselect"}),
    )

    def __init__(self, *args, model_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        if model_name:
            try:
                content_type = ContentType.objects.get(model=model_name.lower())
                self.fields["template"].queryset = HorillaMailTemplate.objects.filter(
                    Q(content_type=content_type) | Q(content_type__isnull=True)
                )
            except ContentType.DoesNotExist:
                self.fields["template"].queryset = HorillaMailTemplate.objects.none()

        else:
            self.fields["template"].queryset = HorillaMailTemplate.objects.filter(
                content_type__isnull=True
            )


class SaveAsMailTemplateForm(forms.ModelForm):
    class Meta:
        model = HorillaMailTemplate
        fields = ["title", "body", "company", "content_type"]

    def clean_body(self):
        body = self.cleaned_data.get("body")
        if not body or strip_tags(body).strip() == "" or body == "<p><br></p>":
            raise ValidationError("Body content cannot be empty.")

        return body


class HorillaMailConfigurationForm(HorillaModelForm):

    password = forms.CharField(
        widget=PasswordInputWithEye(attrs={"placeholder": _("Enter app password")}),
        help_text=_("Enter the app-specific password for your mail account."),
        required=True,
    )

    class Meta:
        model = HorillaMailConfiguration
        fields = [
            "host",
            "port",
            "from_email",
            "username",
            "display_name",
            "password",
            "use_tls",
            "use_ssl",
            "fail_silently",
            "is_primary",
            "use_dynamic_display_name",
            "timeout",
            "company",
            "type",
            "mail_channel",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_fields = [
            "host",
            "port",
            "from_email",
            "username",
            "display_name",
            "password",
        ]

        # Set fields as required
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True


class IncomingHorillaMailConfigurationForm(HorillaModelForm):
    password = forms.CharField(
        widget=PasswordInputWithEye(attrs={"placeholder": _("Enter app password")}),
        help_text=_("Enter the app-specific password  for your mail account."),
        required=True,
    )

    class Meta:
        model = HorillaMailConfiguration
        fields = [
            "host",
            "port",
            "username",
            "password",
            "is_primary",
            "company",
            "type",
            "mail_channel",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_fields = [
            "host",
            "port",
            "username",
            "password",
        ]

        # Set fields as required
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True


class OutlookMailConfigurationForm(HorillaModelForm):
    outlook_client_secret = forms.CharField(
        widget=PasswordInputWithEye(attrs={"placeholder": _("Enter client secret")}),
        help_text=_(
            "Enter the client secret generated from your Microsoft Azure app registration. "
            "This secret is used to authenticate your Outlook integration securely."
        ),
        required=True,
    )

    class Meta:
        model = HorillaMailConfiguration
        fields = [
            "mail_channel",
            "outlook_client_id",
            "outlook_client_secret",
            "outlook_tenant_id",
            "username",
            "display_name",
            "outlook_redirect_uri",
            "outlook_authorization_url",
            "outlook_token_url",
            "outlook_api_endpoint",
            "is_primary",
            "company",
            "type",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # For Outlook, these fields are mandatory
        outlook_required_fields = [
            "outlook_client_id",
            "outlook_client_secret",
            "outlook_tenant_id",
            "username",
            "display_name",
            "outlook_redirect_uri",
            "outlook_authorization_url",
            "outlook_token_url",
            "outlook_api_endpoint",
        ]

        # Set fields as required
        for field_name in outlook_required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
