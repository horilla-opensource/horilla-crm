from functools import cached_property

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from horilla_core.decorators import htmx_required, permission_required_or_denied
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_mail.filters import HorillaMailServerFilter
from horilla_mail.forms import IncomingHorillaMailConfigurationForm
from horilla_mail.models import HorillaMailConfiguration


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class IncomingMailServerView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for mail server page.
    """

    template_name = "mail_server_view.html"
    nav_url = reverse_lazy("horilla_mail:incoming_mail_server_navbar_view")
    list_url = reverse_lazy("horilla_mail:incoming_mail_server_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class IncomingMailServerNavbar(LoginRequiredMixin, HorillaNavView):
    """
    navbar view for mail server
    """

    nav_title = "Horilla Incoming Mail Configurations"
    search_url = reverse_lazy("horilla_mail:incoming_mail_server_list_view")
    main_url = reverse_lazy("horilla_mail:incoming_mail_server_view")
    nav_width = False
    gap_enabled = False
    all_view_types = False
    filter_option = False
    reload_option = False
    one_view_only = True

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("horilla_mail.create_horillaemailconfiguration"):
            return {
                "url": f"""{ reverse_lazy('horilla_mail:incoming_mail_server_type_selection')}?new=true""",
                "attrs": {"id": "mail-server-create"},
                "onclick": "openhorillaModal()",
                "target": "#horillaModalBox",
            }


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class IncomingMailServerTypeSelectionView(LoginRequiredMixin, TemplateView):
    """
    View to show mail server type selection options
    """

    template_name = "incoming/incoming_mail_server_type_selection.html"


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class IncomingMailServerListView(LoginRequiredMixin, HorillaListView):
    """
    List view of mail server
    """

    model = HorillaMailConfiguration
    view_id = "mail-server-list"
    search_url = reverse_lazy("horilla_mail:incoming_mail_server_list_view")
    main_url = reverse_lazy("horilla_mail:incoming_mail_server_view")
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
        return queryset.filter(mail_channel="incoming")


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
class IncomingMailServerFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    create and update from view for mail server
    """

    model = HorillaMailConfiguration
    form_class = IncomingHorillaMailConfigurationForm
    modal_height = False
    hidden_fields = ["company", "type", "mail_channel"]

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get("pk")
        company = getattr(self.request, "active_company", None)
        if not pk:
            initial["company"] = company
            initial["type"] = "mail"
            initial["host"] = "imap.gmail.com"
            initial["port"] = 993
            initial["mail_channel"] = "incoming"
        return initial

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_mail:incoming_mail_server_update_view", kwargs={"pk": pk}
            )
        return reverse_lazy("horilla_mail:incoming_mail_server_form_view")

    def form_valid(self, form):
        super().form_valid(form)
        return HttpResponse(
            "<script>$('#reloadButton').click();closeModal();closehorillaModal();</script>"
        )
