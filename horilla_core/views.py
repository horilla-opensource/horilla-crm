"""
A generic class-based view for rendering the home page.
"""

import logging
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse

import pycountry
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.models import User
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.functional import cached_property  # type: ignore
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from horilla import settings
from horilla.exceptions import HorillaHttp404
from horilla_core.forms import BusinessHourForm, HolidayForm
from horilla_core.initialiaze_database import InitializeDatabaseConditionView
from horilla_core.models import (
    ActiveTab,
    BusinessHour,
    Company,
    DatedConversionRate,
    Holiday,
    HorillaUser,
    MultipleCurrency,
    Role,
)
from horilla_generics.views import (
    HorillaListView,
    HorillaModalDetailView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaTabView,
)
from horilla_mail.models import HorillaMailConfiguration

logger = logging.getLogger(__name__)
User = get_user_model()
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken

from horilla_core.decorators import htmx_required, permission_required_or_denied


def is_jwt_token_valid(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None  # No token

    token = auth_header.split("Bearer ")[1].strip()
    try:
        UntypedToken(token)  # Will raise if invalid
        validated_token = JWTAuthentication().get_validated_token(token)
        user = JWTAuthentication().get_user(validated_token)
        return user
    except (InvalidToken, TokenError):
        return None


def protected_media(request, path):
    public_pages = [
        "/login",
        "/sign-up-user",
        "/forgot-password",
        "/change-password",
        "/reset-password",
        "/initialize-database",
        "/initialize-database-user",
        "/initialize-database-role",
        "/initialize-database-company",
        "/initialize-company-form",
        "/load-data" "/load-demo-data",
    ]
    exempted_folders = ["assets/icons/"]

    media_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(media_path):
        raise HorillaHttp404("File not found")

    referer_path = urlparse(request.META.get("HTTP_REFERER", "")).path

    # Try Bearer token auth
    jwt_user = is_jwt_token_valid(request.META.get("HTTP_AUTHORIZATION", ""))

    # Access control logic
    if referer_path not in public_pages and not any(
        path.startswith(f) for f in exempted_folders
    ):
        if not request.user.is_authenticated and not jwt_user:
            messages.error(
                request,
                "You must be logged in or provide a valid token to access this file.",
            )
            next_url = f"/media/{path}"
            login_url = (
                f"{redirect('horilla_core:login').url}?{urlencode({'next': next_url})}"
            )
            return redirect(login_url)

    return FileResponse(open(media_path, "rb"))


class HomePageView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return redirect(settings.DEFAULT_HOME_REDIRECT)


@method_decorator(htmx_required, name="dispatch")
class ReloadMessages(LoginRequiredMixin, TemplateView):
    """
    Reload messages
    """

    template_name = "messages.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class SaveActiveTabView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        tab_target = request.POST.get("tab_target")
        path = request.POST.get("path")
        user = request.user if request.user.is_authenticated else None
        company = getattr(request, "active_company", None)

        if user and tab_target and path:
            ActiveTab.objects.update_or_create(
                created_by=user,
                path=path,
                company=company if company else user.company,
                defaults={"tab_target": tab_target},
            )
            return JsonResponse({"status": "success"})

        return JsonResponse({"status": "error", "message": "Invalid data"}, status=400)

    def get(self, request, *args, **kwargs):
        return JsonResponse(
            {"status": "error", "message": "Invalid method"}, status=405
        )


class LoginUserView(View):
    def get(self, request):
        """
        Render login page with an optional 'next' param preserved.
        """
        next_url = request.GET.get("next", "/")
        condition_view = InitializeDatabaseConditionView()
        initialize_database = condition_view.get_initialize_condition()
        show_forgot_password = False
        hq_company = Company.objects.filter(hq=True).first()

        if hq_company:
            show_forgot_password = HorillaMailConfiguration.objects.filter(
                company=hq_company
            ).exists()

        context = {
            "next": next_url,
            "initialize_database": initialize_database,
            "show_forgot_password": show_forgot_password,
        }

        return render(request, "login.html", context=context)

    def post(self, request):
        """
        Handle login attempt with **two valid methods**:
        1. Email + Phone number
        2. Username + Password
        """
        identifier = request.POST.get("username")
        secret = request.POST.get("password")
        next_url = request.POST.get("next", "/")

        user = None

        user_by_email_phone = User.objects.filter(
            email=identifier, contact_number=secret
        ).first()
        if user_by_email_phone:
            user = user_by_email_phone

        if not user:
            user = authenticate(request, username=identifier, password=secret)

        if not user:
            messages.error(
                request, _("Invalid credentials. Please check and try again.")
            )
            return redirect(reverse_lazy("horilla_core:login") + f"?next={next_url}")
            # return render(request, "login.html", {"next": next_url})

        if not user.is_active:
            messages.warning(
                request,
                _("This user is archived or blocked. Please contact support."),
            )
            # return render(request, "login.html", {"next": next_url})
            return redirect(reverse_lazy("horilla_core:login") + f"?next={next_url}")

        login(request, user)
        messages.success(request, _("Login successful."))

        if not url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            next_url = "/"

        return redirect(next_url)


class LogoutView(View):
    """
    Class-based view to logout the user and clear local storage.
    """

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        response = HttpResponse()
        response.content = """
            <script>
                localStorage.clear();
            </script>
            <meta http-equiv="refresh" content="0;url=/login">
        """
        return response


class ConmpanyInformationTabView(LoginRequiredMixin, HorillaTabView):
    """
    A generic class-based view for rendering the company information settings page.
    """

    view_id = "company-information-view"
    background_class = "bg-primary-100 rounded-md"

    @cached_property
    def tabs(self):
        if self.request.user.has_perm("horilla_core.view_company"):
            tabs = [
                {
                    "title": _("Details"),
                    "url": reverse_lazy("horilla_core:company_details_tab"),
                    "target": "company-information-view-content",
                    "id": "company-information-view",
                },
                {
                    "title": _("Fiscal Year"),
                    "url": reverse_lazy("horilla_core:company_fiscal_year_tab"),
                    "target": "fiscal-year-view-content",
                    "id": "fiscal-year-view",
                },
                {
                    "title": _("Business Hours "),
                    "url": reverse_lazy("horilla_core:business_hour_view"),
                    "target": "business-hour-content",
                    "id": "business-hour-view",
                },
                {
                    "title": _("Holidays "),
                    "url": reverse_lazy("horilla_core:holiday_view"),
                    "target": "holidays-view-content",
                    "id": "holidays-view",
                },
                {
                    "title": _("Currencies"),
                    "url": reverse_lazy("horilla_core:multiple_currency"),
                    "target": "currency-view-content",
                    "id": "currency-view",
                },
                {
                    "title": _("Recycle Bin Policy"),
                    "url": reverse_lazy("horilla_core:recycle_bin_policy_view"),
                    "target": "recycle-view-content",
                    "id": "recycle-view",
                },
            ]
        return tabs


class SettingView(LoginRequiredMixin, TemplateView):
    """
    TemplateView for settings page.
    """

    template_name = "settings/settings.html"


class MySettingView(LoginRequiredMixin, TemplateView):
    """
    TemplateView for settings page.
    """

    template_name = "settings/my_settings.html"


class ConmpanyInformationView(LoginRequiredMixin, TemplateView):
    """
    TemplateView for company information settings page.
    """

    template_name = "settings/company_information.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "active_company", None)
        context["has_company"] = bool(company)
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.add_company"), name="dispatch"
)
class CompanyFormView(LoginRequiredMixin, HorillaSingleFormView):

    model = Company
    view_id = "company-form-view"

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("horilla_core:edit_company", kwargs={"pk": pk})
        return reverse_lazy("horilla_core:create_company")

    def form_valid(self, form):
        super().form_valid(form)
        if not self.kwargs.get("pk") and apps.is_installed("horilla_crm.leads"):
            return HttpResponse(
                """
                <script>
                    closeModal();
                    $('#reloadButton').click();
                     openContentModal();
                        var div = document.createElement('div');
                        div.setAttribute('hx-get', '%s');
                        div.setAttribute('hx-target', '#contentModalBox');
                        div.setAttribute('hx-trigger', 'load');
                        div.setAttribute('hx-swap', 'innerHTML');
                        document.body.appendChild(div);
                        htmx.process(div);
                </script>
                """
                % reverse_lazy(
                    "leads:load_lead_stages", kwargs={"company_id": self.object.id}
                ),
                headers={"X-Debug": "Modal transition in progress"},
            )
        elif self.request.GET.get("details") == "true":
            return HttpResponse(
                "<script>$('#reloadButton').click();closeModal();</script>"
            )
        branches_view_url = reverse_lazy("horilla_core:branches_view")

        response_html = (
            f"<span "
            f'hx-trigger="load" '
            f'hx-get="{branches_view_url}" '
            f'hx-select="#branches-view" '
            f'hx-target="#branches-view" '
            f'hx-swap="outerHTML" '
            f'hx-on::after-request="closeModal();"'
            f'hx-select-oob="#dropdown-companies">'
            f"</span>"
        )
        return HttpResponse(mark_safe(response_html))


@method_decorator(
    permission_required_or_denied("horilla_core.can_switch_company"), name="dispatch"
)
class SwitchCompanyView(LoginRequiredMixin, View):
    def post(self, request, company_id):
        if request.user.is_authenticated and (
            request.user.is_superuser or request.user.company_id == company_id
        ):
            request.session["active_company_id"] = company_id
        return redirect(request.META.get("HTTP_REFERER", "/"))


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_company"), name="dispatch"
)
class CompanyDetailsTab(LoginRequiredMixin, TemplateView):

    template_name = "settings/company_details_tab.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "active_company", None)
        if company:
            obj = company
        else:
            obj = self.request.user.company
        context["obj"] = obj
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_company"), name="dispatch"
)
class CompanyFiscalYearTab(LoginRequiredMixin, TemplateView):

    template_name = "settings/fiscal_year.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "active_company", None)
        if company:
            cmp = company
        else:
            cmp = self.request.user.company
        if not company:
            context["has_company"] = False
            return context
        obj = cmp.fiscalyear_set.first() if cmp.fiscalyear_set.exists() else None
        start_date = None
        if obj:
            current_fy_instance = obj.year_instances.filter(is_current=True).first()
            if current_fy_instance:
                start_date = current_fy_instance.start_date
        context["obj"] = obj
        context["start_date"] = start_date
        context["has_company"] = True
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_holiday"), name="dispatch"
)
class HolidayView(LoginRequiredMixin, TemplateView):
    """
    TemplateView for holiday view.
    """

    template_name = "settings/holiday.html"


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_holiday"), name="dispatch"
)
class HolidayListView(LoginRequiredMixin, HorillaListView):
    """
    List View for holiday list.
    """

    model = Holiday
    view_id = "holiday-list-view"
    table_width = False
    bulk_select_option = False
    clear_session_button_enabled = False
    search_url = reverse_lazy("horilla_core:holiday_list_view")
    store_ordered_ids = True

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("name").verbose_name, "name"),
            (instance._meta.get_field("start_date").verbose_name, "start_date"),
            (instance._meta.get_field("end_date").verbose_name, "end_date"),
            (instance._meta.get_field("is_recurring").verbose_name, "is_recurring"),
        ]

    @cached_property
    def col_attrs(self):
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = self.request.session.get(self.ordered_ids_key, [])
        attrs = {}
        if self.request.user.has_perm("horilla_core.view_holiday"):
            attrs = {
                "hx-get": f"{{get_detail_url}}?instance_ids={query_string}",
                "hx-target": "#detailModalBox",
                "hx-swap": "innerHTML",
                "hx-push-url": "false",
                "hx-on:click": "openDetailModal();",
                "style": "cursor:pointer",
                "class": "hover:text-primary-600",
            }
        return [
            {
                "name": {
                    **attrs,
                }
            }
        ]

    @cached_property
    def actions(self):
        actions = []
        if self.request.user.has_perm("horilla_core.change_holiday"):
            actions.append(
                {
                    "action": "Edit",
                    "src": "assets/icons/edit.svg",
                    "img_class": "w-4 h-4 flex gap-4",
                    "attrs": """
                    hx-get="{get_edit_url}"
                    hx-target="#modalBox"
                    hx-swap="innerHTML"
                    onclick="openModal()"
                """,
                },
            )
        if self.request.user.has_perm("horilla_core.delete_holiday"):
            actions.append(
                {
                    "action": "Delete",
                    "src": "assets/icons/a4.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                    hx-post="{get_delete_url}"
                    hx-target="#modalBox"
                    hx-swap="innerHTML"
                    hx-trigger="click"
                    hx-vals='{{"check_dependencies": "false"}}'
                    onclick="openModal()"
                """,
                },
            )
        return actions


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.delete_holiday"), name="dispatch"
)
class HolidayDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = Holiday

    def get_post_delete_response(self):
        return HttpResponse(
            "<script>$('#reloadButton').click();closeDeleteModeModal();</script>"
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.add_holiday"), name="dispatch"
)
class HolidayFormView(LoginRequiredMixin, HorillaSingleFormView):
    model = Holiday
    form_class = HolidayForm
    view_id = "holiday-form-view"
    form_title = "Holiday Form"
    # hidden_fields = ["company"]
    full_width_fields = ["name"]

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("horilla_core:holiday_update_form", kwargs={"pk": pk})
        return reverse_lazy("horilla_core:holiday_create_form")

    def get_initial(self):
        initial = super().get_initial()

        toggle = self.request.GET.get("toggle_all_users")

        if toggle == "true":
            current = self.request.GET.get("all_users", "").lower()
            current_recurring = self.request.GET.get("is_recurring", "").lower()

            initial["all_users"] = current in ["true", "on", "1"]
            initial["is_recurring"] = current_recurring in ["true", "on", "1"]
            initial["frequency"] = self.request.GET.get("frequency", "")
            initial["monthly_repeat_type"] = self.request.GET.get(
                "monthly_repeat_type", ""
            )
            initial["yearly_repeat_type"] = self.request.GET.get(
                "yearly_repeat_type", ""
            )

        elif hasattr(self, "object") and self.object:
            initial["all_users"] = self.object.all_users
            initial["is_recurring"] = self.object.is_recurring
            initial["frequency"] = getattr(self.object, "frequency", "")
            initial["monthly_repeat_type"] = getattr(
                self.object, "monthly_repeat_type", ""
            )
            initial["yearly_repeat_type"] = getattr(
                self.object, "yearly_repeat_type", ""
            )

        else:
            initial["all_users"] = False
            initial["is_recurring"] = False
            initial["frequency"] = ""
            initial["monthly_repeat_type"] = ""
            initial["yearly_repeat_type"] = ""

        initial.update(self.request.GET.dict())

        return initial

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk:
            try:
                self.model.objects.get(pk=pk)
            except self.model.DoesNotExist:
                messages.error(request, "The requested data does not exist.")
                return HttpResponse("<script>$('reloadButton').click();</script>")
        if self.request.user.pk != self.kwargs.get(
            "pk"
        ) and not self.request.user.has_perm("horilla_core.add_horillauser"):
            return render(self.request, "error/403.html")

        return super().get(request, *args, **kwargs)

    def form_invalid(self, form):
        response = super().form_invalid(form)
        return response


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_holiday"), name="dispatch"
)
class HolidayDetailView(LoginRequiredMixin, HorillaModalDetailView):
    """
    detail view of page
    """

    model = Holiday
    title = _("Details")
    header = {
        "title": "name",
        "subtitle": "",
        "avatar": "get_avatar",
    }

    body = [
        (_("Holiday Start Date"), "start_date"),
        (_("Holiday End Date"), "end_date"),
        (_("Specific Users"), "specific_users_enable"),
        (_("Recurring"), "is_recurring_holiday"),
    ]

    @cached_property
    def actions(self):
        actions = []
        if self.request.user.has_perm("horilla_core.change_holiday"):
            actions.append(
                [
                    {
                        "action": "Edit",
                        "src": "assets/icons/edit_white.svg",
                        "img_class": "w-3 h-3 flex gap-4 filter brightness-0 invert",
                        "attrs": """
                        class="w-24 justify-center px-4 py-2 bg-primary-600 text-white rounded-md text-xs flex items-center gap-2 hover:bg-primary-800 transition duration-300 disabled:cursor-not-allowed"
                        hx-get="{get_edit_url}"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal();"
                    """,
                    },
                ]
            )
        if self.request.user.has_perm("horilla_core.delete_holiday"):
            actions.append(
                [
                    {
                        "action": "Delete",
                        "src": "assets/icons/a4.svg",
                        "img_class": "w-3 h-3 flex gap-4 brightness-0 saturate-100",
                        "image_style": "filter: invert(27%) sepia(51%) saturate(2878%) hue-rotate(346deg) brightness(104%) contrast(97%)",
                        "attrs": """
                                class="w-24 justify-center px-4 py-2 bg-[white] rounded-md text-xs flex items-center gap-2 border border-primary-500 hover:border-primary-600 transition duration-300 disabled:cursor-not-allowed text-primary-600"
                                hx-post="{get_delete_url}"
                                hx-target="#deleteModeBox"
                                hx-swap="innerHTML"
                                hx-trigger="confirmed"
                                hx-on:click="hxConfirm(this,'Are you sure you want to delete this holiday?')"
                                hx-on::after-request="closeDetailModal();"
                            """,
                    },
                ]
            )
        return actions


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_multiplecurrency"), name="dispatch"
)
class CompanyMultipleCurrency(LoginRequiredMixin, TemplateView):

    template_name = "settings/multiple_currency.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "active_company", None)
        if company:
            cmp = company
        else:
            cmp = self.request.user.company
        context["has_company"] = bool(cmp)
        if not cmp:
            return context
        currencies = MultipleCurrency.objects.filter(company=cmp)
        obj = currencies.filter(company=cmp, is_default=True).first()
        context["obj"] = obj
        context["cmp"] = cmp
        context["currencies"] = currencies
        start_dates = (
            DatedConversionRate.objects.values_list("start_date", flat=True)
            .distinct()
            .order_by("start_date")
        )
        date_ranges = []
        current_date = datetime.now().date()
        selected_start_date = None

        for i, start_date in enumerate(start_dates):
            end_date = None
            if i < len(start_dates) - 1:
                end_date = start_dates[i + 1] - timedelta(days=1)
                date_ranges.append(
                    {
                        "start_date": start_date,
                        "end_date": end_date,
                        "display": f"{start_date.strftime('%d-%m-%Y')} to {end_date.strftime('%d-%m-%Y')}",
                    }
                )
                if start_date <= current_date <= end_date:
                    selected_start_date = start_date
            else:
                date_ranges.append(
                    {
                        "start_date": start_date,
                        "end_date": None,
                        "display": f"{start_date.strftime('%d-%m-%Y')} and After",
                    }
                )
                if start_date <= current_date:
                    selected_start_date = start_date

        context["date_ranges"] = date_ranges
        context["selected_start_date"] = selected_start_date
        return context

    def post(self, request, *args, **kwargs):
        """Handle HTMX toggle for multiple currency activation"""
        company = getattr(request, "active_company", None)
        if company:
            cmp = company
        else:
            cmp = request.user.company
        cmp.activate_multiple_currencies = not cmp.activate_multiple_currencies
        cmp.save()
        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_businesshour"), name="dispatch"
)
class BusinessHourView(LoginRequiredMixin, TemplateView):
    """
    TemplateView for business hour view.
    """

    template_name = "settings/business_hour/business_hour.html"


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_businesshour"), name="dispatch"
)
class BusinessHourListView(LoginRequiredMixin, HorillaListView):
    """
    List View for business hour.
    """

    model = BusinessHour
    view_id = "business-hour-list-view"
    table_width = False
    bulk_select_option = False
    clear_session_button_enabled = False
    search_url = reverse_lazy("horilla_core:business_hour_list_view")
    store_ordered_ids = True

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("name").verbose_name, "name"),
            (instance._meta.get_field("time_zone").verbose_name, "time_zone"),
            (
                instance._meta.get_field("business_hour_type").verbose_name,
                "get_business_hour_type_display",
            ),
            (
                instance._meta.get_field("week_start_day").verbose_name,
                "get_week_start_day_display",
            ),
            (instance._meta.get_field("is_default").verbose_name, "is_default_hour"),
        ]

    @cached_property
    def col_attrs(self):
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = self.request.session.get(self.ordered_ids_key, [])
        attrs = {}
        attrs = {
            "hx-get": f"{{get_detail_url}}?instance_ids={query_string}",
            "hx-target": "#detailModalBox",
            "hx-swap": "innerHTML",
            "hx-push-url": "false",
            "hx-on:click": "openDetailModal();",
            "style": "cursor:pointer",
            "class": "hover:text-primary-600",
        }
        return [
            {
                "name": {
                    **attrs,
                }
            }
        ]

    @cached_property
    def actions(self):
        actions = []
        if self.request.user.has_perm("horilla_core.change_businesshour"):
            actions.append(
                {
                    "action": "Edit",
                    "src": "assets/icons/edit.svg",
                    "img_class": "w-4 h-4 flex gap-4",
                    "attrs": """
                    hx-get="{get_edit_url}"
                    hx-target="#modalBox"
                    hx-swap="innerHTML"
                    onclick="openModal()"
                """,
                },
            )
        if self.request.user.has_perm("horilla_core.delete_businesshour"):
            actions.append(
                {
                    "action": "Delete",
                    "src": "assets/icons/a4.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                        hx-post="{get_delete_url}"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        hx-trigger="click"
                        hx-vals='{{"check_dependencies": "false"}}'
                        onclick="openModal()"
                    """,
                },
            )
        return actions


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.add_businesshour"), name="dispatch"
)
class BusinessHourFormView(LoginRequiredMixin, HorillaSingleFormView):
    model = BusinessHour
    form_class = BusinessHourForm
    view_id = "business-hour-form-view"
    form_title = "Business Hour Form"
    hidden_fields = ["company"]

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_core:business_hour_update_form", kwargs={"pk": pk}
            )
        return reverse_lazy("horilla_core:business_hour_create_form")

    def get_initial(self):
        initial = super().get_initial()
        toggle = self.request.GET.get("toggle_data")
        company = getattr(self.request, "active_company", None)
        initial["company"] = company
        if toggle == "true":
            initial["business_hour_type"] = self.request.GET.get(
                "business_hour_type", ""
            )
            initial["timing_type"] = self.request.GET.get("timing_type", "")

        elif hasattr(self, "object") and self.object:
            initial["business_hour_type"] = getattr(
                self.object, "business_hour_type", ""
            )
            initial["timing_type"] = getattr(self.object, "timing_type", "")

        else:
            initial["business_hour_type"] = ""
            initial["timing_type"] = ""

        initial.update(self.request.GET.dict())
        return initial

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk:
            try:
                self.model.objects.get(pk=pk)
            except self.model.DoesNotExist:
                messages.error(request, "The requested data does not exist.")
                return HttpResponse("<script>$('reloadButton').click();</script>")

        return super().get(request, *args, **kwargs)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.delete_businesshour"), name="dispatch"
)
class BusinessHourDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = BusinessHour

    def get_post_delete_response(self):
        return HttpResponse(
            "<script>$('#reloadButton').click();closeDeleteModeModal();</script>"
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_businesshour"), name="dispatch"
)
class BusinessHourDetailView(LoginRequiredMixin, HorillaModalDetailView):
    """
    detail view of page
    """

    model = BusinessHour
    title = _("Details")
    header = {
        "title": "name",
        "subtitle": "",
        "avatar": "get_avatar",
    }

    body = [
        (_("Time Zone"), "time_zone"),
        (_("Hour Type"), "get_business_hour_type_display"),
        (_("Is Default"), "is_default_hour"),
        (_("Week Starts On"), "get_week_start_day_display"),
        (_("Business Days"), "get_formatted_week_days"),
    ]

    @cached_property
    def actions(self):
        actions = []
        if self.request.user.has_perm("horilla_core.change_businesshour"):
            actions.append(
                [
                    {
                        "action": "Edit",
                        "src": "assets/icons/edit_white.svg",
                        "img_class": "w-3 h-3 flex gap-4 filter brightness-0 invert",
                        "attrs": """
                    class="w-24 justify-center px-4 py-2 bg-primary-600 text-white rounded-md text-xs flex items-center gap-2 hover:bg-primary-800 transition duration-300 disabled:cursor-not-allowed"
                    hx-get="{get_edit_url}"
                    hx-target="#modalBox"
                    hx-swap="innerHTML"
                    onclick="openModal();"
                """,
                    },
                ]
            )
        if self.request.user.has_perm("horilla_core.delete_businesshour"):
            actions.append(
                [
                    {
                        "action": "Delete",
                        "src": "assets/icons/a4.svg",
                        "img_class": "w-3 h-3 flex gap-4 brightness-0 saturate-100",
                        "image_style": "filter: invert(27%) sepia(51%) saturate(2878%) hue-rotate(346deg) brightness(104%) contrast(97%)",
                        "attrs": """
                                class="w-24 justify-center px-4 py-2 bg-[white] rounded-md text-xs flex items-center gap-2 border border-primary-500 hover:border-primary-600 transition duration-300 disabled:cursor-not-allowed text-primary-600"
                                hx-post="{get_delete_url}"
                                hx-target="#deleteModeBox"
                                hx-swap="innerHTML"
                                hx-trigger="confirmed"
                                hx-on:click="hxConfirm(this,'Are you sure you want to delete this holiday?')"
                                hx-on::after-request="closeDetailModal();"
                            """,
                    },
                ]
            )
        return actions


@method_decorator(htmx_required, name="dispatch")
class GetCountrySubdivisionsView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        country_code = request.GET.get("country")
        options = '<option value="">Select State</option>'

        if country_code:
            subdivisions = pycountry.subdivisions.get(country_code=country_code.upper())
            for subdivision in subdivisions:
                options += (
                    f'<option value="{subdivision.code}">{subdivision.name}</option>'
                )

        return HttpResponse(options)


# def get_country_subdivisions(request):
#     country_code = request.GET.get("country")
#     options = '<option value="">Select State</option>'

#     if country_code:
#         subdivisions = pycountry.subdivisions.get(country_code=country_code.upper())
#         for subdivision in subdivisions:
#             options += f'<option value="{subdivision.code}">{subdivision.name}</option>'

#     return HttpResponse(options)


class RolesView(LoginRequiredMixin, TemplateView):
    """
    TemplateView for role settings page.
    """

    template_name = "role/role.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        roles = Role.objects.all()

        def build_role_tree(parent_role=None):
            """Recursively build role hierarchy"""
            children = roles.filter(parent_role=parent_role)
            role_tree = []

            for role in children:
                user_count = role.users.count()
                role_dict = {
                    "id": role.id,
                    "name": role.role_name,
                    "description": getattr(role, "description", ""),
                    "user_count": user_count,
                    "children": build_role_tree(role),
                }
                role_tree.append(role_dict)

            return role_tree

        roles_data = build_role_tree()

        context["roles_data"] = roles_data
        context["roles_count"] = roles.count()
        return context
