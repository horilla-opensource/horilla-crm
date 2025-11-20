import re
from functools import cached_property

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from django.views.generic import FormView, TemplateView

from horilla_core.decorators import htmx_required, permission_required_or_denied
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_mail.filters import HorillaMailServerFilter
from horilla_mail.forms import DynamicMailTestForm, HorillaMailConfigurationForm
from horilla_mail.models import HorillaMailConfiguration
from horilla_utils.middlewares import _thread_local

from .horilla_backends import HorillaDefaultMailBackend


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class MailServerView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for mail server page.
    """

    template_name = "mail_server_view.html"
    nav_url = reverse_lazy("horilla_mail:mail_server_navbar_view")
    list_url = reverse_lazy("horilla_mail:mail_server_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class MailServerNavbar(LoginRequiredMixin, HorillaNavView):
    """
    navbar view for mail server
    """

    nav_title = "Horilla Outgoing Mail Configurations"
    search_url = reverse_lazy("horilla_mail:mail_server_list_view")
    main_url = reverse_lazy("horilla_mail:mail_server_view")
    nav_width = False
    gap_enabled = False
    all_view_types = False
    one_view_only = True
    filter_option = False
    reload_option = False

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("horilla_mail.create_horillaemailconfiguration"):
            return {
                "url": f"""{ reverse_lazy('horilla_mail:mail_server_type_selection')}?new=true""",
                "attrs": {"id": "mail-server-create"},
                "onclick": "openhorillaModal()",
                "target": "#horillaModalBox",
            }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class MailServerTypeSelectionView(LoginRequiredMixin, TemplateView):
    """
    View to show mail server type selection options
    """

    template_name = "mail_server_type_selection.html"


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class MailServerListView(LoginRequiredMixin, HorillaListView):
    """
    List view of mail server
    """

    model = HorillaMailConfiguration
    view_id = "mail-server-list"
    search_url = reverse_lazy("horilla_mail:mail_server_list_view")
    main_url = reverse_lazy("horilla_mail:mail_server_view")
    filterset_class = HorillaMailServerFilter
    bulk_update_two_column = True
    table_width = False
    bulk_delete_enabled = False
    table_height_as_class = "h-[500px]"
    bulk_select_option = False
    list_column_visibility = False
    action_method = "custom_actions"

    columns = ["username", "type"]

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(mail_channel="outgoing")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.view_horillamailconfiguration",
            "horilla_mail.add_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class OutgoingMailServerFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    create and update from view for mail server
    """

    model = HorillaMailConfiguration
    form_class = HorillaMailConfigurationForm
    form_title = "Outgoing Mail Server Configuration"
    modal_height = False
    hidden_fields = ["company", "type", "mail_channel"]

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get("pk")
        company = getattr(self.request, "active_company", None)
        if not pk:
            initial["company"] = company
            initial["type"] = "mail"
            initial["mail_channel"] = "outgoing"
        return initial

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_mail:mail_server_update_view", kwargs={"pk": pk}
            )
        return reverse_lazy("horilla_mail:mail_server_form_view")

    def form_valid(self, form):
        super().form_valid(form)
        return HttpResponse(
            "<script>$('#reloadButton').click();closeModal();closehorillaModal();</script>"
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.view_horillamailconfiguration",
            "horilla_mail.add_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class MailServerTestEmailView(LoginRequiredMixin, FormView):
    template_name = "form_email_test.html"
    form_class = DynamicMailTestForm

    def get_html_content(self, company):
        """Generate HTML email content from template"""
        user = self.request.user.get_full_name()
        button_url = f"{self.request.scheme}://{self.request.get_host()}"

        context = {
            "user": user,
            "company": company,
            "button_url": button_url,
        }

        html_content = render_to_string("mail_server_success.html", context)
        return html_content

    def get_email_backend(self):
        """Get configured email backend with specific instance"""
        instance_id = self.request.GET.get("instance_id")
        setattr(_thread_local, "from_mail_id", instance_id)
        email_backend = HorillaDefaultMailBackend()

        if getattr(_thread_local, "invalid_config", False):
            try:
                delattr(_thread_local, "invalid_config")
            except Exception:
                pass
            return HttpResponse(
                "<script>$('#reloadButton').click();closeModal();</script>"
            )

        return email_backend

    def send_test_email(self, form):
        """Send the test email with inline images"""
        email_to = form.cleaned_data["to_email"]
        company = self.request.active_company
        subject = f"Test mail from {company}"

        html_content = self.get_html_content(company)
        text_content = strip_tags(html_content)

        email_backend = self.get_email_backend()
        if isinstance(email_backend, HttpResponse):
            return None, email_backend

        try:
            msg = EmailMultiAlternatives(
                subject,
                text_content,
                email_backend.dynamic_from_email_with_display_name,
                [email_to],
                connection=email_backend,
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            return True, None

        except Exception as e:
            return False, str(e)

    def parse_error_message(self, error_str):
        """Extract human-readable part from error messages"""
        error_str = str(error_str)

        # Pattern 1: Handle tuple errors like (535, b'5.7.8 Username and Password not accepted...')
        tuple_pattern = r'\(\d+,\s*b?[\'"]([^\'"]*).*?\'\)'
        tuple_match = re.search(tuple_pattern, error_str)
        if tuple_match:
            message = tuple_match.group(1)
            message = re.sub(r"^\d+\.\d+\.\d+\s+", "", message)
            message = re.sub(r"\\n", " ", message)
            message = re.sub(r"\s+", " ", message).strip()
            message = re.split(r"(?i)(for more information|learn more|go to)", message)[
                0
            ].strip()
            return message

        # Pattern 2: Handle [Errno X] messages
        errno_pattern = r"\[Errno -?\d+\]\s*(.+?)(?:\s*\((?!.*\))|$)"
        errno_match = re.search(errno_pattern, error_str)
        if errno_match:
            message = errno_match.group(1).strip()
            # Clean up any trailing punctuation or extra info
            message = re.sub(r"\s*[\(\[].*$", "", message).strip()
            return message

        # Pattern 3: Handle OSError and similar exceptions
        os_error_pattern = (
            r"(?:OSError|ConnectionError|TimeoutError):\s*(.+?)(?:\s*\(|$)"
        )
        os_error_match = re.search(os_error_pattern, error_str)
        if os_error_match:
            return os_error_match.group(1).strip()

        # Pattern 4: Handle authentication errors
        auth_patterns = [
            r"(?i)(authentication\s+failed?)",
            r"(?i)(invalid\s+credentials?)",
            r"(?i)(username\s+and\s+password\s+not\s+accepted)",
            r"(?i)(access\s+denied)",
            r"(?i)(login\s+failed?)",
        ]
        for pattern in auth_patterns:
            auth_match = re.search(pattern, error_str)
            if auth_match:
                return auth_match.group(1)

        # Pattern 5: Handle connection errors
        connection_patterns = [
            r"(?i)(connection\s+refused)",
            r"(?i)(network\s+is\s+unreachable)",
            r"(?i)(timeout\s+error)",
            r"(?i)(host\s+not\s+found)",
            r"(?i)(dns\s+resolution\s+failed)",
        ]
        for pattern in connection_patterns:
            conn_match = re.search(pattern, error_str)
            if conn_match:
                return conn_match.group(1)

        cleaned = re.sub(r"^(Exception|Error):\s*", "", error_str, flags=re.IGNORECASE)
        sentences = re.split(r"[.!?]\s+", cleaned)
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 100:
                first_sentence = first_sentence[:97] + "..."
            return first_sentence if first_sentence else "Unknown error occurred"

        return "Unknown error occurred"

    def form_valid(self, form):
        """Handle valid form submission"""
        success, error = self.send_test_email(form)

        if success is None and isinstance(error, HttpResponse):
            return error

        if success:
            messages.success(self.request, _("Mail sent successfully"))
        else:
            parsed_error = self.parse_error_message(error)
            messages.error(self.request, f"{_('Something went wrong:')} {parsed_error}")

        return HttpResponse("<script>closeModal();$('#reloadButton').click();</script>")

    def get_context_data(self, **kwargs):
        """Add instance_id to context"""
        context = super().get_context_data(**kwargs)
        context["instance_id"] = self.request.GET.get("instance_id")
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_mail.delete_horillamailconfiguration"),
    name="dispatch",
)
class MailServerDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):

    model = HorillaMailConfiguration

    def get_post_delete_response(self):
        return HttpResponse("<script>$('#reloadButton').click();</script>")
