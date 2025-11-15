from datetime import datetime
from functools import cached_property

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import cache
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from requests_oauthlib import OAuth2Session

from horilla_core.decorators import htmx_required, permission_required_or_denied
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_mail.filters import HorillaMailServerFilter
from horilla_mail.forms import OutlookMailConfigurationForm
from horilla_mail.models import HorillaMailConfiguration


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["horilla_mail.add_horillamailconfiguration"]),
    name="dispatch",
)
class OutlookMailServerFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    create and update from view for mail server
    """

    model = HorillaMailConfiguration
    modal_height = False
    form_class = OutlookMailConfigurationForm
    hidden_fields = ["company", "type", "mail_channel"]

    def get_initial(self):
        initial = super().get_initial()
        pk = self.kwargs.get("pk")
        company = getattr(self.request, "active_company", None)
        if not pk:
            initial["outlook_authorization_url"] = (
                "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
            )
            initial["outlook_token_url"] = (
                "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            )
            initial["outlook_api_endpoint"] = "https://graph.microsoft.com/v1.0"
            initial["company"] = company
            initial["type"] = "outlook"
            initial["mail_channel"] = "outgoing"
            if self.request.GET.get("type") == "incoming":
                initial["mail_channel"] = "incoming"
        return initial

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_mail:outlook_mail_server_update_view", kwargs={"pk": pk}
            )
        return reverse_lazy("horilla_mail:outlook_mail_server_form_view")

    def form_valid(self, form):
        super().form_valid(form)
        return HttpResponse(
            "<script>$('#reloadButton').click();closeModal();closehorillaModal();</script>"
        )


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class OutlookLoginView(View):
    """
    Handles Outlook login OAuth flow
    """

    def get(self, request, pk=None, *args, **kwargs):
        selected_company = request.active_company

        if pk:
            api = HorillaMailConfiguration.objects.filter(pk=pk).first()
        else:
            api = HorillaMailConfiguration.objects.filter(
                company=selected_company
            ).first()

        if not api:
            messages.info(request, "Not configured outlook")
            return redirect("/")  # redirect somewhere safe if no config

        oauth = OAuth2Session(
            api.outlook_client_id,
            redirect_uri=api.outlook_redirect_uri,
            scope=["Mail.Read", "Mail.Send", "offline_access"],
        )
        authorization_url, state = oauth.authorization_url(
            api.outlook_authorization_url
        )

        self.request.session["outlook_pk"] = pk
        self.request.session.modified = True
        self.request.session.save()

        api.oauth_state = state
        api.save()

        cache.cache.set("oauth_state", state)

        return redirect(authorization_url)


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class OutlookCallbackView(View):
    """
    Handles Outlook OAuth callback
    """

    def get(self, request, *args, **kwargs):
        selected_company = request.active_company
        pk = self.request.session.get("outlook_pk")

        if pk:
            api = HorillaMailConfiguration.objects.filter(pk=pk).first()
        else:
            api = HorillaMailConfiguration.objects.filter(
                company=selected_company
            ).first()

        if not api:
            messages.error(request, "Invalid Outlook configuration")
            return redirect("/")

        state = api.oauth_state

        oauth = OAuth2Session(
            api.outlook_client_id,
            state=state,
            redirect_uri=api.outlook_redirect_uri,
        )

        authorization_response_uri = request.build_absolute_uri()
        authorization_response_uri = authorization_response_uri.replace(
            "http://", "https://"
        )

        api.last_refreshed = datetime.now()
        token = oauth.fetch_token(
            api.outlook_token_url,
            client_secret=api.get_decrypted_client_secret(),
            authorization_response=authorization_response_uri,
        )
        api.token = token
        api.save()

        return redirect("/")


def refresh_outlook_token(api: HorillaMailConfiguration):
    """
    Refresh Outlook token
    """
    oauth = OAuth2Session(
        api.outlook_client_id,
        token=api.token,
        auto_refresh_kwargs={
            "client_id": api.outlook_client_id,
            "client_secret": api.get_decrypted_client_secret(),
        },
        auto_refresh_url=api.outlook_token_url,
    )
    new_token = oauth.refresh_token(
        api.outlook_token_url,
        refresh_token=api.token["refresh_token"],
        client_id=api.outlook_client_id,
        client_secret=api.get_decrypted_client_secret(),
    )
    api.token = new_token
    api.last_refreshed = timezone.now()
    api.save()
    return api


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailconfiguration"]),
    name="dispatch",
)
class OutlookRefreshTokenView(View):
    """
    Refresh Outlook token
    """

    def get(self, request, pk, *args, **kwargs):
        try:
            api = HorillaMailConfiguration.objects.get(pk=pk)
        except:
            messages.error(
                request,
                f"{HorillaMailConfiguration._meta.verbose_name.title()} not found or no longer exists.",
            )
            return HttpResponse(
                "<script>$('#reloadButton').click();closeModal();</script>"
            )

        old_token = api.token.get("access_token")

        api = refresh_outlook_token(api)

        if api.token.get("access_token") == old_token:
            messages.info(request, _("Token not refreshed, Login required"))
        else:
            messages.success(request, _("Token refreshed successfully"))

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
