"""
Views for managing Forecast Targets, including creation, update, deletion,
and dynamic UI handling for role-based and condition-based forecasting.
"""

from functools import cached_property

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_core.models import HorillaUser, Period, Role
from horilla_crm.forecast.filters import ForecastTargetFilter
from horilla_crm.forecast.forms import ForecastTargetForm
from horilla_crm.forecast.models import ForecastTarget, ForecastType
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_utils.middlewares import _thread_local


class ForecastTargetView(LoginRequiredMixin, HorillaView):
    """Main forecast target settings page."""

    template_name = "forecast_target/forecast_target_view.html"
    nav_url = reverse_lazy("forecast:forecast_target_nav_view")
    list_url = reverse_lazy("forecast:forecast_target_list_view")
    main_url = reverse_lazy("forecast:forecast_target_view")
    filters_url = reverse_lazy("forecast:forecast_target_filters_view")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        company = getattr(self.request, "active_company", None)

        context["company"] = company
        context["forecast_types"] = ForecastType.objects.all()
        context["has_company"] = bool(company)
        context["has_forecast_types"] = context["forecast_types"].exists()
        context["nav_url"] = self.nav_url
        context["list_url"] = self.list_url
        context["main_url"] = self.main_url
        context["filters_url"] = self.filters_url

        if not company or not context["has_forecast_types"]:
            return context

        forecast_type_id = self.request.GET.get("forecast_type")
        period_id = self.request.GET.get("period")

        if forecast_type_id:
            context["default_forecast_type"] = (
                context["forecast_types"].filter(pk=forecast_type_id).first()
            )
        else:
            context["default_forecast_type"] = context["forecast_types"].first()

        context["periods"] = Period.objects.all()
        current_date = timezone.now().date()

        if period_id:
            context["default_period"] = context["periods"].filter(pk=period_id).first()
        else:
            context["default_period"] = (
                context["periods"]
                .filter(start_date__lte=current_date, end_date__gte=current_date)
                .first()
                or context["periods"].first()
            )

        context["current_forecast_type_id"] = forecast_type_id
        context["current_period_id"] = period_id

        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("forecast.view_forecasttarget"), name="dispatch")
class ForecastTargetFiltersView(LoginRequiredMixin, HorillaView):
    """Load forecast type and period filter dropdowns dynamically."""

    template_name = "forecast_target/forecast_target_filters.html"
    main_url = reverse_lazy("forecast:forecast_target_view")
    list_url = reverse_lazy("forecast:forecast_target_list_view")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        forecast_types = ForecastType.objects.all()
        forecast_type_id = self.request.GET.get("forecast_type")
        period_id = self.request.GET.get("period")

        if forecast_type_id:
            default_forecast_type = forecast_types.filter(pk=forecast_type_id).first()
        else:
            default_forecast_type = forecast_types.first()

        periods = Period.objects.all()
        current_date = timezone.now().date()

        if period_id:
            default_period = periods.filter(pk=period_id).first()
        else:
            default_period = (
                periods.filter(
                    start_date__lte=current_date, end_date__gte=current_date
                ).first()
                or periods.first()
            )

        context.update(
            {
                "forecast_types": forecast_types,
                "periods": periods,
                "default_forecast_type": default_forecast_type,
                "default_period": default_period,
                "current_forecast_type_id": forecast_type_id,
                "current_period_id": period_id,
                "main_url": self.main_url,
                "list_url": self.list_url,
            }
        )

        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("forecast.view_forecasttarget"), name="dispatch")
class ForecastTargetNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Render the forecast target navigation bar with role and condition filters.
    """

    nav_title = ForecastTarget._meta.verbose_name_plural
    search_url = reverse_lazy("forecast:forecast_target_list_view")
    main_url = reverse_lazy("forecast:forecast_target_view")
    filterset_class = ForecastTargetFilter
    nav_width = False
    gap_enabled = False
    all_view_types = False
    recently_viewed_option = False
    filter_option = False
    one_view_only = True
    reload_option = False
    border_enabled = False

    @cached_property
    def new_button(self):
        """
        Return a button element for creating a new forecast target.
        """
        if self.request.user.has_perm("forecast.add_forecasttarget"):
            return {
                "url": f"""{ reverse_lazy('forecast:forecast_target_form_view')}""",
                "attrs": {"id": "target-create"},
                "title": "Set Target",
            }
        return None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("forecast.view_forecasttarget"), name="dispatch"
)
class ForecastTargetListView(LoginRequiredMixin, HorillaListView):
    """
    Foreacst Target List view
    """

    model = ForecastTarget
    view_id = "forecast-target-list"
    filterset_class = ForecastTargetFilter
    search_url = reverse_lazy("forecast:forecast_target_list_view")
    main_url = reverse_lazy("forecast:forecast_target_view")
    save_to_list_option = False
    bulk_select_option = False
    clear_session_button_enabled = False
    table_width = False
    enable_sorting = False
    table_height_as_class = "h-[500px]"

    def get_queryset(self):
        queryset = super().get_queryset()
        forecast_type_id = self.request.GET.get("forecast_type")
        period_id = self.request.GET.get("period")

        if forecast_type_id:
            queryset = queryset.filter(forcasts_type=forecast_type_id)
        if period_id:
            queryset = queryset.filter(period=period_id)

        return queryset

    @cached_property
    def columns(self):
        """
        Return the table column headers and their corresponding model fields.
        """

        instance = self.model()
        user_model = instance._meta.get_field("assigned_to").related_model
        return [
            (instance._meta.get_field("assigned_to").verbose_name, "assigned_to"),
            (user_model._meta.get_field("role").verbose_name, "assigned_to__role"),
            (instance._meta.get_field("target_amount").verbose_name, "target_amount"),
        ]

    @cached_property
    def actions(self):
        """
        Return a list of available action buttons (Edit, Delete) based on user permissions.
        """

        actions = []
        if self.request.user.has_perm("forecast.change_forecasttarget"):
            actions.append(
                {
                    "action": "Edit",
                    "src": "assets/icons/edit.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                            hx-get="{get_edit_url}"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            """,
                },
            )
        if self.request.user.has_perm("forecast.delete_forecasttarget"):
            actions.append(
                {
                    "action": "Delete",
                    "src": "assets/icons/a4.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                            hx-get="{get_delete_url}"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            """,
                },
            )
        return actions


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("forecast.add_forecasttarget"), name="dispatch"
)
class ForecastTargetFormView(HorillaSingleFormView):
    """Form view for creating/updating ForecastTarget with dynamic conditions."""

    model = ForecastTarget
    form_class = ForecastTargetForm
    template_name = "forecast_target/forecast_target_form.html"
    fields = [
        "role",
        "assigned_to",
        "period",
        "forcasts_type",
        "target_amount",
        "is_role_based",
        "is_period_same",
        "is_target_same",
        "is_forecast_type_same",
    ]
    form_url = reverse_lazy("forecast:forecast_target_form_view")
    condition_fields = ["assigned_to", "period", "forcasts_type", "target_amount"]
    condition_field_title = "Select User"
    modal_height = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        is_period_same = self.request.POST.get("is_period_same", "off") == "on"
        is_target_same = self.request.POST.get("is_target_same", "off") == "on"
        is_forecast_type_same = (
            self.request.POST.get("is_forecast_type_same", "off") == "on"
        )
        condition_fields = ["assigned_to"]
        if not is_period_same:
            condition_fields.append("period")
        if not is_forecast_type_same:
            condition_fields.append("forcasts_type")
        if not is_target_same:
            condition_fields.append("target_amount")
        kwargs["condition_fields"] = condition_fields
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["users"] = HorillaUser.objects.all()
        context["roles"] = Role.objects.all()
        context["period_choices"] = [(p.id, p.name) for p in Period.objects.all()]
        context["forecast_type_choices"] = [
            (f.id, f.name) for f in ForecastType.objects.all()
        ]
        return context

    def add_condition_row(self, request):
        row_id = request.GET.get("row_id", "0")

        new_row_id = "0"
        if row_id == "next":
            current_count = request.session.get("condition_row_count", 0)
            current_count += 1
            request.session["condition_row_count"] = current_count
            new_row_id = str(current_count)
        else:
            try:
                new_row_id = str(int(row_id) + 1)
            except ValueError:
                new_row_id = "1"

        # Calculate condition_fields based on GET params
        is_period_same = request.GET.get("is_period_same", "off") == "on"
        is_target_same = request.GET.get("is_target_same", "off") == "on"
        is_forecast_type_same = request.GET.get("is_forecast_type_same", "off") == "on"
        condition_fields = ["assigned_to"]
        if not is_period_same:
            condition_fields.append("period")
        if not is_forecast_type_same:
            condition_fields.append("forcasts_type")
        if not is_target_same:
            condition_fields.append("target_amount")

        form_kwargs = self.get_form_kwargs()
        form_kwargs["row_id"] = new_row_id
        form_kwargs["condition_fields"] = condition_fields  # Override for this form

        if "pk" in self.kwargs:
            try:
                instance = self.model.objects.get(pk=self.kwargs["pk"])
                form_kwargs["instance"] = instance
            except self.model.DoesNotExist:
                pass

        form = self.get_form_class()(**form_kwargs)

        # Filter users based on role and is_role_based
        is_role_based = request.GET.get("is_role_based", "off") == "on"
        role_id = request.GET.get("role")
        users = HorillaUser.objects.all()
        if is_role_based:
            if role_id:
                users = users.filter(role_id=role_id)
            else:
                users = HorillaUser.objects.none()

        context = {
            "form": form,
            "condition_fields": condition_fields,
            "row_id": new_row_id,
            "submitted_condition_data": self.get_submitted_condition_data(),
            "users": users,
            "period_choices": [(p.id, p.name) for p in Period.objects.all()],
            "forecast_type_choices": [
                (f.id, f.name) for f in ForecastType.objects.all()
            ],
        }
        html = render_to_string(
            "forecast_target/condition_row.html", context, request=request
        )
        return HttpResponse(html)

    def form_valid(self, form):
        condition_data = self.get_submitted_condition_data()
        role = form.cleaned_data.get("role")
        is_role_based = form.cleaned_data.get("is_role_based", False)
        is_period_same = form.cleaned_data.get("is_period_same", False)
        is_target_same = form.cleaned_data.get("is_target_same", False)
        is_forecast_type_same = form.cleaned_data.get("is_forecast_type_same", False)
        common_period = form.cleaned_data.get("period")
        common_target = form.cleaned_data.get("target_amount")
        common_forcasts_type = form.cleaned_data.get("forcasts_type")

        if not condition_data:
            form.add_error(None, "At least one user must be assigned.")
            return self.form_invalid(form)

        combinations_to_create = []

        for row_id, row in condition_data.items():
            if "assigned_to" not in row or not row["assigned_to"]:
                form.add_error(None, f"User assignment is required for row {row_id}.")
                return self.form_invalid(form)

            period = None
            target_amount = None
            forcasts_type = None

            if is_period_same:
                if not common_period:
                    form.add_error(
                        "period",
                        "Period is required when 'Same Period for All' is selected.",
                    )
                    return self.form_invalid(form)
                period = common_period
            elif "period" in row and row["period"]:
                period = Period.objects.get(id=row["period"])
            else:
                form.add_error(
                    None,
                    f"Period is required for row {row_id} when 'Same Period for All' is not selected.",
                )
                return self.form_invalid(form)

            if is_target_same:
                if common_target is None:
                    form.add_error(
                        "target_amount",
                        "Target amount is required when 'Same Target for All' is selected.",
                    )
                    return self.form_invalid(form)
                target_amount = common_target
            elif "target_amount" in row and row["target_amount"]:
                target_amount = row["target_amount"]
            else:
                form.add_error(
                    None,
                    f"Target amount is required for row {row_id} when 'Same Target for All' is not selected.",
                )
                return self.form_invalid(form)

            if is_forecast_type_same:
                if not common_forcasts_type:
                    form.add_error(
                        "forcasts_type",
                        "Forecast type is required when 'Same Forecast Type for All' is selected.",
                    )
                    return self.form_invalid(form)
                forcasts_type = common_forcasts_type
            elif "forcasts_type" in row and row["forcasts_type"]:
                forcasts_type = ForecastType.objects.get(id=row["forcasts_type"])
            else:
                form.add_error(
                    None,
                    f"Forecast type is required for row {row_id} when 'Same Forecast Type for All' is not selected.",
                )
                return self.form_invalid(form)

            assigned_to_id = int(row["assigned_to"])
            period_id = period.id
            forcasts_type_id = forcasts_type.id

            combination = (assigned_to_id, period_id, forcasts_type_id)
            if combination in combinations_to_create:
                assigned_user = HorillaUser.objects.get(id=assigned_to_id)
                form.add_error(
                    None,
                    f"Duplicate entry found for user '{assigned_user}' with the same period and forecast type.",
                )
                return self.form_invalid(form)

            existing_target = ForecastTarget.objects.filter(
                assigned_to_id=assigned_to_id,
                period_id=period_id,
                forcasts_type_id=forcasts_type_id,
            ).first()

            if existing_target:
                assigned_user = HorillaUser.objects.get(id=assigned_to_id)
                form.add_error(
                    None,
                    f"Forecast target already exists for user '{assigned_user}' with the selected period and forecast type.",
                )
                return self.form_invalid(form)

            combinations_to_create.append(combination)

            # Create ForecastTarget instance
            instance = ForecastTarget(
                role=role if is_role_based else None,
                assigned_to=HorillaUser.objects.get(id=assigned_to_id),
                period=period,
                target_amount=target_amount,
                forcasts_type=forcasts_type,
            )
            instance.company = (
                getattr(_thread_local, "request", None).active_company
                if hasattr(_thread_local, "request")
                else self.request.user.company
            )
            instance.created_by = self.request.user
            instance.updated_by = self.request.user
            instance.save()

        self.request.session["condition_row_count"] = 0
        messages.success(self.request, "Forecast targets created successfully!")
        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")


@method_decorator(
    permission_required_or_denied("forecast.change_forecasttarget"), name="dispatch"
)
class ToggleRoleBasedView(View):
    """View to toggle role-based user filtering for forecast target conditions."""

    def post(self, request, *_args, **_kwargs):
        """
        Handle POST request to filter users based on role selection and update condition fields.
        """
        is_role_based = request.POST.get("is_role_based", "off") == "on"
        role_id = request.POST.get("role")
        is_period_same = request.POST.get("is_period_same", "off") == "on"
        is_target_same = request.POST.get("is_target_same", "off") == "on"
        is_forecast_type_same = request.POST.get("is_forecast_type_same", "off") == "on"
        users = HorillaUser.objects.all()
        if is_role_based:
            if role_id:
                users = users.filter(role_id=role_id)
            else:
                users = HorillaUser.objects.none()
        form = ForecastTargetForm(request.POST)

        condition_fields = ["assigned_to"]
        if not is_period_same:
            condition_fields.append("period")
        if not is_forecast_type_same:
            condition_fields.append("forcasts_type")
        if not is_target_same:
            condition_fields.append("target_amount")

        # Condition fields container (main response)
        condition_context = {
            "form": form,
            "condition_fields": condition_fields,
            "users": users,
            "roles": Role.objects.all(),
            "period_choices": [(p.id, p.name) for p in Period.objects.all()],
            "forecast_type_choices": [
                (f.id, f.name) for f in ForecastType.objects.all()
            ],
            "submitted_condition_data": self.get_condition_data(request),
            "condition_row_count": request.session.get("condition_row_count", 0),
        }
        html_condition = render_to_string(
            "forecast_target/condition_fields.html", condition_context, request=request
        )

        # Role container oob
        role_context = {
            "form": form,
            "is_role_based": is_role_based,
        }
        html_role = render_to_string(
            "forecast_target/role_field.html", role_context, request=request
        )
        html_role_oob = (
            f'<div id="role_container" hx-swap-oob="innerHTML">{html_role}</div>'
        )

        return HttpResponse(html_condition + html_role_oob)

    def get_condition_data(self, request):
        """Extract and return condition row data from POST request."""

        possible_condition_fields = [
            "assigned_to",
            "period",
            "target_amount",
            "forcasts_type",
        ]
        condition_data = {}
        for key, value in request.POST.items():
            for field_name in possible_condition_fields:
                if key.startswith(f"{field_name}_") and key != field_name:
                    try:
                        row_id = key.replace(f"{field_name}_", "")
                        if row_id not in condition_data:
                            condition_data[row_id] = {}
                        condition_data[row_id][field_name] = value
                    except Exception:
                        continue
        return condition_data


@method_decorator(
    permission_required_or_denied("forecast.change_forecasttarget"), name="dispatch"
)
class ToggleConditionFieldsView(View):
    """View to dynamically toggle visibility of forecast target condition fields."""

    def post(self, request, *_args, **_kwargs):
        """
        Handle POST request to update visible condition fields based on user selections.
        """
        is_period_same = request.POST.get("is_period_same", "off") == "on"
        is_target_same = request.POST.get("is_target_same", "off") == "on"
        is_forecast_type_same = request.POST.get("is_forecast_type_same", "off") == "on"
        is_role_based = request.POST.get("is_role_based", "off") == "on"
        role_id = request.POST.get("role")
        form = ForecastTargetForm(request.POST)

        condition_fields = ["assigned_to"]
        if not is_period_same:
            condition_fields.append("period")
        if not is_forecast_type_same:
            condition_fields.append("forcasts_type")
        if not is_target_same:
            condition_fields.append("target_amount")

        users = HorillaUser.objects.all()
        if is_role_based:
            if role_id:
                users = users.filter(role_id=role_id)
            else:
                users = HorillaUser.objects.none()

        # Extract condition data
        possible_condition_fields = [
            "assigned_to",
            "period",
            "target_amount",
            "forcasts_type",
        ]
        condition_data = {}
        for key, value in request.POST.items():
            for field_name in possible_condition_fields:
                if key.startswith(f"{field_name}_") and key != field_name:
                    try:
                        row_id = key.replace(f"{field_name}_", "")
                        if row_id not in condition_data:
                            condition_data[row_id] = {}
                        condition_data[row_id][field_name] = value
                    except Exception:
                        continue

        # Condition fields (main)
        context = {
            "form": form,
            "condition_fields": condition_fields,
            "users": users,
            "period_choices": [(p.id, p.name) for p in Period.objects.all()],
            "forecast_type_choices": [
                (f.id, f.name) for f in ForecastType.objects.all()
            ],
            "submitted_condition_data": condition_data,
            "condition_row_count": request.session.get("condition_row_count", 0),
        }
        html_condition = render_to_string(
            "forecast_target/condition_fields.html", context, request=request
        )

        # Period oob
        period_context = {"form": form, "is_period_same": is_period_same}
        html_period = render_to_string(
            "forecast_target/period_field.html", period_context, request=request
        )
        html_period_oob = (
            f'<div id="period_container" hx-swap-oob="innerHTML">{html_period}</div>'
        )

        # Target oob
        target_context = {"form": form, "is_target_same": is_target_same}
        html_target = render_to_string(
            "forecast_target/target_field.html", target_context, request=request
        )
        html_target_oob = (
            f'<div id="target_container" hx-swap-oob="innerHTML">{html_target}</div>'
        )

        # Forecast type oob
        forecast_context = {
            "form": form,
            "is_forecast_type_same": is_forecast_type_same,
        }
        html_forecast = render_to_string(
            "forecast_target/forecast_type_field.html",
            forecast_context,
            request=request,
        )
        html_forecast_oob = f'<div id="forecast_type_container" hx-swap-oob="innerHTML">{html_forecast}</div>'

        return HttpResponse(
            html_condition + html_period_oob + html_target_oob + html_forecast_oob
        )


@method_decorator(
    permission_required_or_denied("forecast.change_forecasttarget"), name="dispatch"
)
class UpdateTargetHelpTextView(View):
    """View to update the help text for the target amount based on forecast type."""

    template_name = "forecast_target/target_amount_help_text.html"

    def post(self, request, *_args, **_kwargs):
        """
        Update and return the help text for the target amount based on forecast type.
        """
        row_id = request.GET.get("row_id", "0")
        forecast_type_id = (
            request.POST.get("forcasts_type")
            or request.POST.get(f"forcasts_type_{row_id}")
            or request.POST.get("forcasts_type_0")
        )
        help_text = "Enter the target amount"

        if forecast_type_id:
            try:
                forecast_type = ForecastType.objects.get(id=forecast_type_id)
                if forecast_type.is_quantity_based:
                    help_text = "Enter the quantity"
                elif forecast_type.is_revenue_based:
                    help_text = "Enter the revenue amount"
            except ForecastType.DoesNotExist:
                pass

        context = {
            "help_text": help_text,
            "row_id": row_id,
        }
        return render(request, self.template_name, context)


@method_decorator(
    permission_required_or_denied("forecast.change_forecasttarget"), name="dispatch"
)
class UpdateForecastTarget(LoginRequiredMixin, HorillaSingleFormView):
    """View to update the target amount for a specific ForecastTarget."""

    model = ForecastTarget
    fields = ["target_amount"]
    full_width_fields = ["target_amount"]
    form_title = _("Update Target")
    modal_height = False

    @cached_property
    def form_url(self):
        """
        Return the URL for the update form of the specific ForecastTarget instance.
        """
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "forecast:forecast_target_update_form_view", kwargs={"pk": pk}
            )
        return None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("forecast.delete_forecasttarget"), name="dispatch"
)
class ForecastTargetDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """View to delete a ForecastTarget and handle the post-delete response."""

    model = ForecastTarget

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")
