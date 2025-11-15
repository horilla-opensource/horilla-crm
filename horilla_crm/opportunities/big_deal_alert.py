"""
This view handles the methods for Big deal alert view
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, View

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_crm.opportunities.filters import BigDealAlertFilter
from horilla_crm.opportunities.models import BigDealAlert
from horilla_generics.views import (
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)


class BigDealAlertView(LoginRequiredMixin, HorillaView):
    """
    Template view for Big deal alert page
    """

    template_name = "big_deal_alert_view.html"
    nav_url = reverse_lazy("opportunities:big_deal_alert_nav")
    list_url = reverse_lazy("opportunities:big_deal_main_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required("opportunities.view_bigdealalert"), name="dispatch"
)
class BigDealAlertNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar for big deal alert
    """

    nav_title = BigDealAlert._meta.verbose_name_plural
    search_url = reverse_lazy("opportunities:big_deal_main_view")
    main_url = reverse_lazy("opportunities:big_deal_alert_view")
    filterset_class = BigDealAlertFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "BigDealAlert"
    model_app_label = "opportunities"
    nav_width = False
    gap_enabled = False
    url_name = "big_deal_main_view"
    search_option = False
    # border_enabled = False

    @cached_property
    def new_button(self):
        """Return the 'Big Deal Create' button if the user has add permission."""
        if self.request.user.has_perm("opportunities.add_bigdealalert"):
            return {
                "url": f"""{ reverse_lazy('opportunities:big_deal_create_form')}?new=true""",
                "attrs": {"id": "big-deal-create"},
            }
        return None


@method_decorator(htmx_required, name="dispatch")
class BigDealAlertMainView(TemplateView):
    """
    Main view
    """

    template_name = "big_deal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["alerts"] = BigDealAlert.objects.all()
        context["view_id"] = "big_deal_alert"

        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("opportunities.change_bigdealalert"), name="dispatch"
)
class UpdateAlertStatusView(View):
    """
    Handles updating the 'active' status of a Big Deal Alert.

    Only users with 'change_bigdealalert' permission can update the status.
    The view expects a POST request with the 'active' field.
    Returns an HTMX-compatible response to update the alert in the frontend.
    """

    template_name = "big_deal.html"

    def post(self, request, pk):
        """Update the 'active' status of a Big Deal Alert and return HTMX response."""
        try:
            alert = get_object_or_404(BigDealAlert, id=pk)
        except Exception as e:
            messages.error(request, e)
            return HttpResponse("<script>$('#reloadButton').click();</script>")

        active_value = request.POST.get("active") == "True"
        alert.active = active_value
        alert.save()

        messages.success(request, _("Threshold updated successfully"))
        return render(request, self.template_name, {"alerts": [alert]})


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("opportunities.add_bigdealalert"), name="dispatch"
)
class BigDealAlertFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    Form view for create and update alerts
    """

    model = BigDealAlert
    form_title = _("Big Deal Alert")
    fields = [
        "alert_name",
        "trigger_amount",
        "trigger_probability",
        "sender_name",
        "sender_email",
        "notify_emails",
        "notify_cc_emails",
        "notify_bcc_emails",
        "notify_opportunity_owner",
        "active",
    ]

    @cached_property
    def form_url(self):
        """Return the URL for the form based on the presence of a primary key."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("opportunities:big_deal_update_form", kwargs={"pk": pk})
        return reverse_lazy("opportunities:big_deal_create_form")

    def form_valid(self, form):
        """
        Handle form submission and save the task.
        """
        super().form_valid(form)
        return HttpResponse(
            "<script>htmx.trigger('#reloadButton','click');closeModal();</script>"
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("opportunities.delete_bigdealalert"), name="dispatch"
)
class BigDealAlertDelete(LoginRequiredMixin, HorillaSingleDeleteView):
    """
    View to delete a Big Deal Alert.
    """

    model = BigDealAlert

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")
