"""
Forecast Views Module

Django class-based views for managing and displaying sales forecast data in Horilla CRM.
Features: Period-based forecasts, trend analysis, user/aggregated views, optimized queries.
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from horilla.exceptions import HorillaHttp404
from horilla_core.decorators import htmx_required, permission_required_or_denied
from horilla_core.models import Company, FiscalYearInstance, HorillaUser, Period
from horilla_crm.forecast.models import Forecast, ForecastTarget, ForecastType
from horilla_crm.forecast.utils import ForecastCalculator
from horilla_crm.opportunities.models import Opportunity
from horilla_generics.views import HorillaListView, HorillaTabView, HorillaView


class ForecastView(LoginRequiredMixin, HorillaView):
    """Main forecast dashboard view with fiscal year and user filtering capabilities."""

    template_name = "forecast_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        forcast_types = ForecastType.objects.all()
        type_count = forcast_types.count()
        fiscal_years = FiscalYearInstance.objects.all()
        current_instance = fiscal_years.filter(is_current=True).first()

        fiscal_year_id = self.request.GET.get("fiscal_year_id")
        user_id = self.request.GET.get("user_id")

        selected_instance = (
            FiscalYearInstance.objects.get(id=fiscal_year_id)
            if fiscal_year_id
            and FiscalYearInstance.objects.filter(id=fiscal_year_id).exists()
            else current_instance
        )

        query_params = self.request.GET.copy()
        query_string = query_params.urlencode() if query_params else ""

        context.update(
            {
                "users": HorillaUser.objects.filter(is_active=True),
                "fiscal_years": fiscal_years,
                "current_instance": current_instance,
                "selected_instance": selected_instance,
                "previous_instance": None,
                "next_instance": None,
                "user_id": user_id,
                "fiscal_year_id": fiscal_year_id,
                "query_string": query_string,
                "type_count": type_count,
            }
        )

        if fiscal_years and selected_instance:
            instances_list = list(fiscal_years)
            try:
                current_index = instances_list.index(selected_instance)
                if current_index > 0:
                    context["previous_instance"] = instances_list[current_index - 1]
                if current_index < len(instances_list) - 1:
                    context["next_instance"] = instances_list[current_index + 1]
            except ValueError:
                pass

        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class ForecastNavbarView(LoginRequiredMixin, HorillaView):
    """Dynamically load forecast navbar/filters."""

    template_name = "forecast_navbar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        forcast_types = ForecastType.objects.all()
        type_count = forcast_types.count()
        fiscal_years = FiscalYearInstance.objects.all()
        current_instance = fiscal_years.filter(is_current=True).first()

        fiscal_year_id = self.request.GET.get("fiscal_year_id")
        user_id = self.request.GET.get("user_id")

        selected_instance = (
            FiscalYearInstance.objects.get(id=fiscal_year_id)
            if fiscal_year_id
            and FiscalYearInstance.objects.filter(id=fiscal_year_id).exists()
            else current_instance
        )

        query_params = self.request.GET.copy()
        query_string = query_params.urlencode() if query_params else ""

        # Check permissions
        has_view_all = self.request.user.has_perm("opportunities.view_opportunity")
        has_view_own = self.request.user.has_perm("opportunities.view_own_opportunity")

        # Determine user list and default selection based on permissions
        if has_view_all:
            # User can view all opportunities - show all users
            users = HorillaUser.objects.filter(is_active=True)
            show_all_users_option = True
            # If no user_id is specified, don't force one (show all by default)
            if not user_id:
                user_id = None
        elif has_view_own:
            # User can only view their own opportunities - restrict to current user only
            users = HorillaUser.objects.filter(id=self.request.user.id, is_active=True)
            show_all_users_option = False
            # Force user_id to be the current user
            user_id = str(self.request.user.pk)
        else:
            # No permission - empty queryset
            users = HorillaUser.objects.none()
            show_all_users_option = False
            user_id = None

        context.update(
            {
                "users": users,
                "fiscal_years": fiscal_years,
                "current_instance": current_instance,
                "selected_instance": selected_instance,
                "user_id": user_id,
                "fiscal_year_id": fiscal_year_id,
                "query_string": query_string,
                "type_count": type_count,
                "show_all_users_option": show_all_users_option,
                "has_view_all": has_view_all,
                "has_view_own": has_view_own,
            }
        )

        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class ForecastTabView(LoginRequiredMixin, HorillaTabView):
    """Tabbed interface view for organizing different forecast types within a company."""

    view_id = "forecast-tab-view"
    background_class = "rounded-md"
    tab_class = "h-[500px] overflow-x-auto custom-scroll"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tabs = self.get_forecast_tabs()

    def get_forecast_tabs(self):
        """Generate tab configuration for each active forecast type with URLs and IDs."""
        tabs = []
        company = None
        if self.request.user.is_authenticated:
            company = (
                self.request.active_company
                if self.request.active_company
                else self.request.user.company
            )
        forecast_types = ForecastType.objects.filter(
            is_active=True, company=company
        ).order_by("created_at")

        query_params = self.request.GET.copy()
        for index, forecast_type in enumerate(forecast_types, 1):
            url = reverse_lazy(
                "forecast:forecast_type_view", kwargs={"pk": forecast_type.id}
            )
            if query_params:
                url = f"{url}?{query_params.urlencode()}"
            tab = {
                "title": forecast_type.name or f"Forecast {index}",
                "url": url,
                "target": f"forecast-{forecast_type.id}-content",
                "id": f"forecast-{forecast_type.id}-view",
            }
            tabs.append(tab)
        return tabs


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        ["opportunities.view_opportunity", "opportunities.view_own_opportunity"]
    ),
    name="dispatch",
)
class ForecastTypeView(TemplateView):
    """
    Detailed forecast view displaying period-by-period data with trends, targets,
    and performance metrics for a specific forecast type.
    """

    template_name = "forecast_type_view.html"
    USERS_PER_PAGE = 10

    def get(self, request, *args, **kwargs):
        user_id = request.GET.get("user_id")
        has_view_all = request.user.has_perm("opportunities.view_opportunity")
        has_view_own = request.user.has_perm("opportunities.view_own_opportunity")

        if has_view_own and not has_view_all:
            if user_id and user_id != str(request.user.pk):
                return render(request, "error/403.html")
            if not user_id:
                request.GET = request.GET.copy()
                request.GET["user_id"] = str(request.user.pk)

        context = self.get_context_data(**kwargs)
        if context.get("error"):
            return HttpResponse("<script>$('#reloadButton').click();</script>")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        forecast_type_id = kwargs.get("pk")
        try:
            forecast_type = get_object_or_404(
                ForecastType, id=forecast_type_id, is_active=True
            )
        except Exception as e:
            messages.error(self.request, str(e))
            context["error"] = True
            return context

        fiscal_year_id = self.request.GET.get("fiscal_year_id")
        fiscal_year = (
            FiscalYearInstance.objects.get(id=fiscal_year_id)
            if fiscal_year_id
            and FiscalYearInstance.objects.filter(id=fiscal_year_id).exists()
            else self.get_current_fiscal_year
        )

        self.ensure_forecasts_exist(forecast_type, fiscal_year)

        # Get user_id - this will be current user if they only have view_own permission
        user_id = self.request.GET.get("user_id")

        # Additional permission check
        has_view_all = self.request.user.has_perm("opportunities.view_opportunity")
        has_view_own = self.request.user.has_perm("opportunities.view_own_opportunity")

        # If user only has view_own, ensure they can only see their own data
        if has_view_own and not has_view_all:
            if not user_id or user_id != str(self.request.user.pk):
                user_id = str(self.request.user.pk)

        page = self.request.GET.get("page", 1)
        forecasts = self.get_forecast_data(forecast_type, fiscal_year, user_id, page)

        # Calculate totals for all periods
        forecast_totals = self.calculate_forecast_totals(forecasts, forecast_type)

        currency_symbol = (
            self.get_company_for_user.currency if self.get_company_for_user else "USD"
        )

        # Construct search_url and search_params for HTMX
        search_url = self.request.path
        search_params = self.request.GET.copy()
        if "page" in search_params:
            del search_params["page"]
        search_params = search_params.urlencode()

        title = (
            f"{forecast_type.get_forecast_type_display} Forecast for {fiscal_year.name}"
        )

        context.update(
            {
                "forecast_type": forecast_type,
                "fiscal_year": fiscal_year,
                "forecasts": forecasts,
                "forecast_totals": forecast_totals,
                "currency_symbol": currency_symbol,
                "user_id": user_id,
                "title": title,
                "search_url": search_url,
                "search_params": search_params,
                "has_view_all": has_view_all,
                "has_view_own": has_view_own,
            }
        )
        return context

    # def get(self, request, *args, **kwargs):
    #     context = self.get_context_data(**kwargs)
    #     if context.get("error"):
    #         return HttpResponse("<script>$('#reloadButton').click();</script>")
    #     return super().get(request, *args, **kwargs)

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     forecast_type_id = kwargs.get("pk")
    #     try:
    #         forecast_type = get_object_or_404(
    #             ForecastType, id=forecast_type_id, is_active=True
    #         )
    #     except Exception as e:
    #         messages.error(self.request, str(e))
    #         context["error"] = True  # Add error flag to context
    #         return context

    #     # Get fiscal_year_id from query parameters or default to current fiscal year
    #     fiscal_year_id = self.request.GET.get("fiscal_year_id")
    #     fiscal_year = (
    #         FiscalYearInstance.objects.get(id=fiscal_year_id)
    #         if fiscal_year_id
    #         and FiscalYearInstance.objects.filter(id=fiscal_year_id).exists()
    #         else self.get_current_fiscal_year
    #     )

    #     self.ensure_forecasts_exist(forecast_type, fiscal_year)

    #     user_id = self.request.GET.get("user_id")
    #     page = self.request.GET.get("page", 1)
    #     forecasts = self.get_forecast_data(forecast_type, fiscal_year, user_id, page)

    #     # Calculate totals for all periods
    #     forecast_totals = self.calculate_forecast_totals(forecasts, forecast_type)

    #     currency_symbol = (
    #         self.get_company_for_user.currency if self.get_company_for_user else "USD"
    #     )

    #     # Construct search_url and search_params for HTMX
    #     search_url = self.request.path
    #     search_params = self.request.GET.copy()
    #     if "page" in search_params:
    #         del search_params["page"]
    #     search_params = search_params.urlencode()

    #     title = (
    #         f"{forecast_type.get_forecast_type_display} Forecast for {fiscal_year.name}"
    #     )

    #     context.update(
    #         {
    #             "forecast_type": forecast_type,
    #             "fiscal_year": fiscal_year,
    #             "forecasts": forecasts,
    #             "forecast_totals": forecast_totals,
    #             "currency_symbol": currency_symbol,
    #             "user_id": user_id,
    #             "title": title,
    #             "search_url": search_url,
    #             "search_params": search_params,
    #         }
    #     )
    #     return context

    def calculate_forecast_totals(self, forecasts, forecast_type):
        """Calculate totals across all periods for the forecast data."""

        class ForecastTotals:
            """
            Aggregated totals across ALL forecasts (all users, all periods)
            for display in the totals row at the bottom of the table.
            """

            def __init__(self):
                self.forecast_type = forecast_type
                if forecast_type.is_quantity_based:
                    self.target_quantity = 0
                    self.pipeline_quantity = 0
                    self.best_case_quantity = 0
                    self.commit_quantity = 0
                    self.closed_quantity = 0
                    self.actual_quantity = 0
                    self.gap_quantity = 0
                else:
                    self.target_amount = 0
                    self.pipeline_amount = 0
                    self.best_case_amount = 0
                    self.commit_amount = 0
                    self.closed_amount = 0
                    self.actual_amount = 0
                    self.gap_amount = 0

                self.performance_percentage = 0
                self.gap_percentage = 0
                self.closed_percentage = 0
                self.closed_deals_count = 0

        totals = ForecastTotals()

        if not forecasts:
            return totals

        for forecast in forecasts:
            if forecast_type.is_quantity_based:
                totals.target_quantity += getattr(forecast, "target_quantity", 0) or 0
                totals.pipeline_quantity += (
                    getattr(forecast, "pipeline_quantity", 0) or 0
                )
                totals.best_case_quantity += (
                    getattr(forecast, "best_case_quantity", 0) or 0
                )
                totals.commit_quantity += getattr(forecast, "commit_quantity", 0) or 0
                totals.closed_quantity += getattr(forecast, "closed_quantity", 0) or 0
                totals.actual_quantity += getattr(forecast, "actual_quantity", 0) or 0
            else:
                totals.target_amount += getattr(forecast, "target_amount", 0) or 0
                totals.pipeline_amount += getattr(forecast, "pipeline_amount", 0) or 0
                totals.best_case_amount += getattr(forecast, "best_case_amount", 0) or 0
                totals.commit_amount += getattr(forecast, "commit_amount", 0) or 0
                totals.closed_amount += getattr(forecast, "closed_amount", 0) or 0
                totals.actual_amount += getattr(forecast, "actual_amount", 0) or 0

            totals.closed_deals_count += getattr(forecast, "closed_deals_count", 0) or 0

        # Calculate derived metrics
        if forecast_type.is_quantity_based:
            totals.gap_quantity = totals.target_quantity - totals.actual_quantity
            if totals.target_quantity > 0:
                totals.performance_percentage = (
                    totals.actual_quantity / totals.target_quantity
                ) * 100
                totals.gap_percentage = (
                    totals.gap_quantity / totals.target_quantity
                ) * 100
                totals.closed_percentage = (
                    totals.closed_quantity / totals.target_quantity
                ) * 100
        else:
            totals.gap_amount = totals.target_amount - totals.actual_amount
            if totals.target_amount > 0:
                totals.performance_percentage = (
                    totals.actual_amount / totals.target_amount
                ) * 100
                totals.gap_percentage = (totals.gap_amount / totals.target_amount) * 100
                totals.closed_percentage = (
                    totals.closed_amount / totals.target_amount
                ) * 100

        return totals

    @cached_property
    def get_current_fiscal_year(self):
        """Cache the current fiscal year to avoid repeated queries."""
        return FiscalYearInstance.objects.filter(is_current=True).first()

    @cached_property
    def get_company_for_user(self):
        """Cache the active company for the current user."""
        return (
            self.request.active_company
            if hasattr(self.request, "active_company")
            else Company.objects.filter(id=self.request.user.company_id).first()
        )

    def get_target_for_period_bulk(self, periods, forecast_type, user_id=None):
        """
        Get targets for all periods in bulk to avoid N+1 queries
        """
        if user_id:
            # Get individual targets for specific user
            targets = ForecastTarget.objects.filter(
                is_active=True,
                assigned_to_id=user_id,
                period__in=periods,
                forcasts_type=forecast_type,  # Corrected from forcasts_type
            ).select_related("period", "assigned_to")

            target_map = {target.period_id: target for target in targets}

            # For missing individual targets, check role-based targets
            missing_periods = [p for p in periods if p.id not in target_map]
            if missing_periods:
                try:
                    user = HorillaUser.objects.get(id=user_id)
                    if hasattr(user, "role") and user.role:
                        role_targets = ForecastTarget.objects.filter(
                            is_active=True,
                            period__in=missing_periods,
                            forcasts_type=forecast_type,  # Corrected from forcasts_type
                            role=user.role,
                            assigned_to__isnull=True,
                        ).select_related("period")

                        for role_target in role_targets:
                            if role_target.period_id not in target_map:
                                target_map[role_target.period_id] = role_target
                except HorillaUser.DoesNotExist:
                    pass

            return target_map
        all_targets = (
            ForecastTarget.objects.filter(
                is_active=True,
                period__in=periods,
                forcasts_type=forecast_type,  # Corrected from forcasts_type
            )
            .select_related("period", "assigned_to")
            .prefetch_related("role")
        )

        targets_by_period = {}
        for target in all_targets:
            period_id = target.period_id
            if period_id not in targets_by_period:
                targets_by_period[period_id] = []
            targets_by_period[period_id].append(target)

        return targets_by_period

    def ensure_forecasts_exist(self, forecast_type, fiscal_year):
        """
        Bulk create missing forecasts to reduce database operations
        """
        calculator = ForecastCalculator(user=self.request.user, fiscal_year=fiscal_year)

        all_users = list(HorillaUser.objects.filter(is_active=True).values("id"))
        all_periods = list(
            Period.objects.filter(quarter__fiscal_year=fiscal_year).values("id")
        )

        existing_forecasts = set(
            Forecast.objects.filter(
                forecast_type=forecast_type, fiscal_year=fiscal_year
            ).values_list("owner_id", "period_id")
        )

        missing_forecasts = []
        for user in all_users:
            for period in all_periods:
                combination = (user["id"], period["id"])
                if combination not in existing_forecasts:
                    missing_forecasts.append((user["id"], period["id"]))

        # Bulk create missing forecasts
        if missing_forecasts:
            calculator.bulk_create_missing_forecasts(forecast_type, missing_forecasts)

    def get_forecast_data(self, forecast_type, fiscal_year, user_id=None, page=1):
        """
        COMPLETE FIX for single user trend data display
        """
        periods = (
            Period.objects.filter(quarter__fiscal_year=fiscal_year)
            .select_related("quarter")
            .order_by("period_number")
        )

        currency_symbol = (
            self.get_company_for_user.currency if self.get_company_for_user else "USD"
        )

        periods_list = list(periods)
        targets_data = self.get_target_for_period_bulk(
            periods_list, forecast_type, user_id
        )

        forecast_queryset = Forecast.objects.filter(
            forecast_type=forecast_type, fiscal_year=fiscal_year
        ).select_related("owner", "forecast_type", "period", "quarter")

        if user_id:
            forecast_queryset = forecast_queryset.filter(owner_id=user_id)
        else:
            forecast_queryset = forecast_queryset.filter(
                owner__is_active=True
            ).prefetch_related("owner")

        forecasts_by_period = {}
        for forecast in forecast_queryset:
            period_id = forecast.period_id
            if period_id not in forecasts_by_period:
                forecasts_by_period[period_id] = []
            forecasts_by_period[period_id].append(forecast)

        # Get trend data - this is crucial for single users
        trend_data = (
            self.get_bulk_trend_data(periods_list, forecast_type, user_id)
            if periods_list
            else {}
        )

        period_forecasts = []
        for period in periods_list:
            user_forecasts = forecasts_by_period.get(period.id, [])
            target = self.extract_target_from_bulk(
                targets_data, period, None if not user_id else user_id
            )

            if user_id:
                # SINGLE USER VIEW - This is where the fix is critical
                if not user_forecasts:
                    # Create empty forecast for user with no data
                    try:
                        user = HorillaUser.objects.get(id=user_id)
                        empty_forecast = Forecast()
                        empty_forecast.id = f"empty_{period.id}_{user_id}"
                        empty_forecast.period = period
                        empty_forecast.quarter = period.quarter
                        empty_forecast.fiscal_year = period.quarter.fiscal_year
                        empty_forecast.forecast_type = forecast_type
                        empty_forecast.owner = user
                        empty_forecast.owner_id = user.id

                        # Initialize all fields to 0
                        if forecast_type.is_quantity_based:
                            empty_forecast.target_quantity = (
                                target.target_amount if target else 0
                            )
                            empty_forecast.pipeline_quantity = 0
                            empty_forecast.best_case_quantity = 0
                            empty_forecast.commit_quantity = 0
                            empty_forecast.closed_quantity = 0
                            empty_forecast.actual_quantity = 0
                        else:
                            empty_forecast.target_amount = (
                                target.target_amount if target else 0
                            )
                            empty_forecast.pipeline_amount = 0
                            empty_forecast.best_case_amount = 0
                            empty_forecast.commit_amount = 0
                            empty_forecast.closed_amount = 0
                            empty_forecast.actual_amount = 0

                        user_forecasts = [empty_forecast]
                    except HorillaUser.DoesNotExist:
                        user_forecasts = []

                # Create aggregated forecast
                aggregated_forecast = self.create_aggregated_forecast(
                    period,
                    forecast_type,
                    user_forecasts,
                    currency_symbol,
                    user_id,
                    target,
                )

                if trend_data and period.id in trend_data:
                    period_trend = trend_data[period.id]

                    aggregated_forecast.commit_trend = period_trend.get("commit_trend")
                    aggregated_forecast.best_case_trend = period_trend.get(
                        "best_case_trend"
                    )
                    aggregated_forecast.pipeline_trend = period_trend.get(
                        "pipeline_trend"
                    )
                    aggregated_forecast.closed_trend = period_trend.get("closed_trend")
                    aggregated_forecast.commit_change_text = period_trend.get(
                        "commit_change_text", ""
                    )
                    aggregated_forecast.best_case_change_text = period_trend.get(
                        "best_case_change_text", ""
                    )
                    aggregated_forecast.pipeline_change_text = period_trend.get(
                        "pipeline_change_text", ""
                    )
                    aggregated_forecast.closed_change_text = period_trend.get(
                        "closed_change_text", ""
                    )

                else:
                    aggregated_forecast.commit_trend = None
                    aggregated_forecast.best_case_trend = None
                    aggregated_forecast.pipeline_trend = None
                    aggregated_forecast.closed_trend = None
                    aggregated_forecast.commit_change_text = ""
                    aggregated_forecast.best_case_change_text = ""
                    aggregated_forecast.pipeline_change_text = ""
                    aggregated_forecast.closed_change_text = ""

                aggregated_forecast.user_forecasts = []

            else:
                users_with_data = []
                users_without_data = []
                all_active_users = HorillaUser.objects.select_related("role").filter(
                    is_active=True
                )
                user_targets = self.get_target_for_period_bulk(
                    [period], forecast_type, None
                )
                user_target_map = {
                    target.assigned_to_id: target
                    for target in user_targets.get(period.id, [])
                }

                for user in all_active_users:
                    user_forecast = next(
                        (f for f in user_forecasts if f.owner_id == user.id), None
                    )
                    user_specific_target = user_target_map.get(user.id)

                    if user_forecast:
                        if user_specific_target:
                            if forecast_type.is_quantity_based:
                                user_forecast.target_quantity = (
                                    user_specific_target.target_amount
                                )
                            else:
                                user_forecast.target_amount = (
                                    user_specific_target.target_amount
                                )
                        else:
                            if forecast_type.is_quantity_based:
                                user_forecast.target_quantity = 0
                            else:
                                user_forecast.target_amount = 0

                        has_data = (
                            forecast_type.is_quantity_based
                            and (
                                user_forecast.actual_quantity > 0
                                or user_forecast.pipeline_quantity > 0
                                or user_forecast.best_case_quantity > 0
                                or user_forecast.commit_quantity > 0
                                or user_forecast.closed_quantity > 0
                            )
                        ) or (
                            not forecast_type.is_quantity_based
                            and (
                                user_forecast.actual_amount > 0
                                or user_forecast.pipeline_amount > 0
                                or user_forecast.best_case_amount > 0
                                or user_forecast.commit_amount > 0
                                or user_forecast.closed_amount > 0
                            )
                        )
                        if has_data:
                            users_with_data.append(user_forecast)
                        else:
                            users_without_data.append(user_forecast)
                    else:
                        # Create empty forecast for users without data
                        empty_forecast = Forecast()
                        empty_forecast.id = f"empty_{period.id}_{user.id}"
                        empty_forecast.period = period
                        empty_forecast.quarter = period.quarter
                        empty_forecast.fiscal_year = period.quarter.fiscal_year
                        empty_forecast.forecast_type = forecast_type
                        empty_forecast.owner = user
                        empty_forecast.owner_id = user.id

                        if forecast_type.is_quantity_based:
                            empty_forecast.target_quantity = (
                                user_specific_target.target_amount
                                if user_specific_target
                                else 0
                            )
                            empty_forecast.pipeline_quantity = 0
                            empty_forecast.best_case_quantity = 0
                            empty_forecast.commit_quantity = 0
                            empty_forecast.closed_quantity = 0
                            empty_forecast.actual_quantity = 0
                        else:
                            empty_forecast.target_amount = (
                                user_specific_target.target_amount
                                if user_specific_target
                                else 0
                            )
                            empty_forecast.pipeline_amount = 0
                            empty_forecast.best_case_amount = 0
                            empty_forecast.commit_amount = 0
                            empty_forecast.closed_amount = 0
                            empty_forecast.actual_amount = 0

                        users_without_data.append(empty_forecast)

                # Sort users with data
                if forecast_type.is_quantity_based:
                    users_with_data.sort(
                        key=lambda f: getattr(f, "actual_quantity", 0) or 0,
                        reverse=True,
                    )
                else:
                    users_with_data.sort(
                        key=lambda f: getattr(f, "actual_amount", 0) or 0, reverse=True
                    )

                sorted_user_forecasts = users_with_data + users_without_data

                paginator = Paginator(sorted_user_forecasts, self.USERS_PER_PAGE)
                try:
                    paginated_user_forecasts = paginator.page(page)
                except Exception:
                    paginated_user_forecasts = paginator.page(1)

                aggregated_forecast = self.create_aggregated_forecast(
                    period,
                    forecast_type,
                    user_forecasts,
                    currency_symbol,
                    user_id,
                    target,
                )

                # Apply trend data to aggregated forecast
                if period.id in trend_data:
                    period_trend = trend_data[period.id]
                    aggregated_forecast.commit_trend = period_trend.get("commit_trend")
                    aggregated_forecast.best_case_trend = period_trend.get(
                        "best_case_trend"
                    )
                    aggregated_forecast.pipeline_trend = period_trend.get(
                        "pipeline_trend"
                    )
                    aggregated_forecast.closed_trend = period_trend.get("closed_trend")
                    aggregated_forecast.commit_change_text = period_trend.get(
                        "commit_change_text", ""
                    )
                    aggregated_forecast.best_case_change_text = period_trend.get(
                        "best_case_change_text", ""
                    )
                    aggregated_forecast.pipeline_change_text = period_trend.get(
                        "pipeline_change_text", ""
                    )
                    aggregated_forecast.closed_change_text = period_trend.get(
                        "closed_change_text", ""
                    )

                # Attach paginated user forecasts with individual trend data
                aggregated_forecast.user_forecasts = [
                    self.enhance_forecast_data_bulk(
                        f, currency_symbol, period, forecast_type, trend_data
                    )
                    for f in paginated_user_forecasts
                ]
                aggregated_forecast.has_next = paginated_user_forecasts.has_next()
                aggregated_forecast.next_page = (
                    paginated_user_forecasts.next_page_number()
                    if paginated_user_forecasts.has_next()
                    else None
                )
                aggregated_forecast.view_id = f"period_{period.id}"

            period_forecasts.append(aggregated_forecast)

        return period_forecasts

    def create_empty_user_forecast_with_owner(
        self, period, forecast_type, user_id, currency_symbol, target=None
    ):
        """
        Create a placeholder forecast for a user
        with no data - returns actual forecast object.
        """
        try:
            user = HorillaUser.objects.get(id=user_id)
        except HorillaUser.DoesNotExist:
            return None

        # Create an actual Forecast object (not saved to DB) with proper attributes
        forecast = Forecast()
        forecast.id = f"empty_{period.id}_{user_id}"
        forecast.period = period
        forecast.quarter = period.quarter
        forecast.fiscal_year = period.quarter.fiscal_year
        forecast.forecast_type = forecast_type
        forecast.owner = user
        forecast.owner_id = user.id  # Ensure owner_id is set

        # Set target and other fields based on forecast type
        if target and forecast_type.is_quantity_based:
            forecast.target_quantity = target.target_amount
            forecast.pipeline_quantity = 0
            forecast.best_case_quantity = 0
            forecast.commit_quantity = 0
            forecast.closed_quantity = 0
            forecast.actual_quantity = 0
            forecast.gap_quantity = forecast.target_quantity
        elif target:
            forecast.target_amount = target.target_amount
            forecast.pipeline_amount = 0
            forecast.best_case_amount = 0
            forecast.commit_amount = 0
            forecast.closed_amount = 0
            forecast.actual_amount = 0
            forecast.gap_amount = forecast.target_amount
        else:
            if forecast_type.is_quantity_based:
                forecast.target_quantity = 0
                forecast.pipeline_quantity = 0
                forecast.best_case_quantity = 0
                forecast.commit_quantity = 0
                forecast.closed_quantity = 0
                forecast.actual_quantity = 0
                forecast.gap_quantity = 0
            else:
                forecast.target_amount = 0
                forecast.pipeline_amount = 0
                forecast.best_case_amount = 0
                forecast.commit_amount = 0
                forecast.closed_amount = 0
                forecast.actual_amount = 0
                forecast.gap_amount = 0

        forecast.performance_percentage = 0
        forecast.gap_percentage = 0
        forecast.closed_percentage = 0
        forecast.closed_deals_count = 0
        forecast.currency_symbol = currency_symbol

        return forecast

    def extract_target_from_bulk(self, targets_data, period, user_id):
        """Helper to extract target from bulk loaded data"""
        if user_id:
            target = targets_data.get(period.id)
            if target:
                return target
            return None

        period_targets = targets_data.get(period.id, [])
        total_target = sum(target.target_amount for target in period_targets)

        if total_target > 0:

            class AggregatedTarget:
                """Wrapper for summed target amounts from multiple period targets."""

                def __init__(self, target_amount):
                    self.target_amount = target_amount

            return AggregatedTarget(total_target)
        return None

    def calculate_trend_direction(self, current, previous):
        """Helper to calculate trend direction"""
        if current > previous:
            return "up"
        if current < previous:
            return "down"
        return None

    def format_change_text(
        self, current, previous, period_name, is_quantity_based, currency
    ):
        """Helper to format change text"""
        if current == previous:
            return f"No change from {period_name}"

        change = abs(current - previous)
        direction = "increased" if current > previous else "decreased"
        unit = "deals" if is_quantity_based else currency or "USD"

        return (
            f"{direction.title()} by {change} {unit} from {period_name}"
            if is_quantity_based
            else f"{direction.title()} by {change:,.0f} {unit} from {period_name}"
        )

    def get_user_specific_trend_data(
        self, user_id, period_id, previous_period_id, user_period_data, forecast_type
    ):
        """
        Calculate trend data for a specific user between two periods
        """
        user_data = user_period_data.get(user_id, {})
        current_data = user_data.get(
            period_id, {"commit": 0, "best_case": 0, "pipeline": 0, "closed": 0}
        )
        previous_data = user_data.get(
            previous_period_id,
            {"commit": 0, "best_case": 0, "pipeline": 0, "closed": 0},
        )

        # Get the previous period name for change text
        previous_period = Period.objects.get(id=previous_period_id)

        return {
            "commit_trend": self.calculate_trend_direction(
                current_data["commit"], previous_data["commit"]
            ),
            "best_case_trend": self.calculate_trend_direction(
                current_data["best_case"], previous_data["best_case"]
            ),
            "pipeline_trend": self.calculate_trend_direction(
                current_data["pipeline"], previous_data["pipeline"]
            ),
            "closed_trend": self.calculate_trend_direction(
                current_data["closed"], previous_data["closed"]
            ),
            "commit_change_text": self.format_change_text(
                current_data["commit"],
                previous_data["commit"],
                previous_period.name,
                forecast_type.is_quantity_based,
                self.get_company_for_user.currency,
            ),
            "best_case_change_text": self.format_change_text(
                current_data["best_case"],
                previous_data["best_case"],
                previous_period.name,
                forecast_type.is_quantity_based,
                self.get_company_for_user.currency,
            ),
            "pipeline_change_text": self.format_change_text(
                current_data["pipeline"],
                previous_data["pipeline"],
                previous_period.name,
                forecast_type.is_quantity_based,
                self.get_company_for_user.currency,
            ),
            "closed_change_text": self.format_change_text(
                current_data["closed"],
                previous_data["closed"],
                previous_period.name,
                forecast_type.is_quantity_based,
                self.get_company_for_user.currency,
            ),
        }

    def get_bulk_trend_data(self, periods, forecast_type, user_id=None):
        """
        Properly handle both single user and multi-user individual trends
        """
        if len(periods) < 2:
            return {}

        query_params = {
            "forecast_type": forecast_type,
            "fiscal_year": periods[0].quarter.fiscal_year,
            "period__in": periods,
        }
        if user_id:
            query_params["owner_id"] = user_id

        all_forecasts = Forecast.objects.filter(**query_params).values(
            "period_id",
            "period__period_number",
            "owner_id",
            "commit_quantity" if forecast_type.is_quantity_based else "commit_amount",
            (
                "best_case_quantity"
                if forecast_type.is_quantity_based
                else "best_case_amount"
            ),
            (
                "pipeline_quantity"
                if forecast_type.is_quantity_based
                else "pipeline_amount"
            ),
            "closed_quantity" if forecast_type.is_quantity_based else "closed_amount",
        )

        field_suffix = "quantity" if forecast_type.is_quantity_based else "amount"

        period_data = {}
        user_period_data = {}

        for forecast in all_forecasts:
            period_id = forecast["period_id"]
            owner_id = forecast["owner_id"]

            if period_id not in period_data:
                period_data[period_id] = {
                    "period_number": forecast["period__period_number"],
                    "commit": 0,
                    "best_case": 0,
                    "pipeline": 0,
                    "closed": 0,
                }

            period_data[period_id]["commit"] += (
                forecast.get(f"commit_{field_suffix}", 0) or 0
            )
            period_data[period_id]["best_case"] += (
                forecast.get(f"best_case_{field_suffix}", 0) or 0
            )
            period_data[period_id]["pipeline"] += (
                forecast.get(f"pipeline_{field_suffix}", 0) or 0
            )
            period_data[period_id]["closed"] += (
                forecast.get(f"closed_{field_suffix}", 0) or 0
            )

            if owner_id not in user_period_data:
                user_period_data[owner_id] = {}

            if period_id not in user_period_data[owner_id]:
                user_period_data[owner_id][period_id] = {
                    "period_number": forecast["period__period_number"],
                    "commit": 0,
                    "best_case": 0,
                    "pipeline": 0,
                    "closed": 0,
                }

            user_period_data[owner_id][period_id]["commit"] = (
                forecast.get(f"commit_{field_suffix}", 0) or 0
            )
            user_period_data[owner_id][period_id]["best_case"] = (
                forecast.get(f"best_case_{field_suffix}", 0) or 0
            )
            user_period_data[owner_id][period_id]["pipeline"] = (
                forecast.get(f"pipeline_{field_suffix}", 0) or 0
            )
            user_period_data[owner_id][period_id]["closed"] = (
                forecast.get(f"closed_{field_suffix}", 0) or 0
            )

        # Calculate trends
        trend_results = {}
        sorted_periods = sorted(periods, key=lambda p: p.period_number)

        for i, period in enumerate(sorted_periods):
            if i == 0:  # First period has no previous data
                continue

            current_data = period_data.get(
                period.id, {"commit": 0, "best_case": 0, "pipeline": 0, "closed": 0}
            )
            previous_period = sorted_periods[i - 1]
            previous_data = period_data.get(
                previous_period.id,
                {"commit": 0, "best_case": 0, "pipeline": 0, "closed": 0},
            )

            # Period-level trends (for main aggregated row)
            trend_results[period.id] = {
                "commit_trend": self.calculate_trend_direction(
                    current_data["commit"], previous_data["commit"]
                ),
                "best_case_trend": self.calculate_trend_direction(
                    current_data["best_case"], previous_data["best_case"]
                ),
                "pipeline_trend": self.calculate_trend_direction(
                    current_data["pipeline"], previous_data["pipeline"]
                ),
                "closed_trend": self.calculate_trend_direction(
                    current_data["closed"], previous_data["closed"]
                ),
                "commit_change_text": self.format_change_text(
                    current_data["commit"],
                    previous_data["commit"],
                    previous_period.name,
                    forecast_type.is_quantity_based,
                    self.get_company_for_user.currency,
                ),
                "best_case_change_text": self.format_change_text(
                    current_data["best_case"],
                    previous_data["best_case"],
                    previous_period.name,
                    forecast_type.is_quantity_based,
                    self.get_company_for_user.currency,
                ),
                "pipeline_change_text": self.format_change_text(
                    current_data["pipeline"],
                    previous_data["pipeline"],
                    previous_period.name,
                    forecast_type.is_quantity_based,
                    self.get_company_for_user.currency,
                ),
                "closed_change_text": self.format_change_text(
                    current_data["closed"],
                    previous_data["closed"],
                    previous_period.name,
                    forecast_type.is_quantity_based,
                    self.get_company_for_user.currency,
                ),
                "user_data": user_period_data,
                "previous_period_id": previous_period.id,
            }

        return trend_results

    def enhance_forecast_data_bulk(
        self,
        forecast,
        currency_symbol,
        period=None,
        forecast_type=None,
        trend_data=None,
    ):
        """
        FIXED: Enhanced forecast data with proper individual user trend handling
        """
        gap_to_target = (
            (forecast.target_quantity - forecast.actual_quantity)
            if forecast.forecast_type.is_quantity_based
            and hasattr(forecast, "target_quantity")
            and forecast.target_quantity
            and forecast.actual_quantity
            else (
                (forecast.target_amount - forecast.actual_amount)
                if hasattr(forecast, "target_amount")
                and forecast.target_amount
                and forecast.actual_amount
                else 0
            )
        )

        is_on_track = (
            forecast.actual_quantity >= forecast.commit_quantity
            if forecast.forecast_type.is_quantity_based
            and forecast.actual_quantity
            and forecast.commit_quantity
            else (
                forecast.actual_amount >= forecast.commit_amount
                if forecast.actual_amount and forecast.commit_amount
                else False
            )
        )

        forecast.gap_to_target = gap_to_target
        forecast.is_on_track = is_on_track
        forecast.currency_symbol = currency_symbol

        if (
            trend_data
            and period
            and period.id in trend_data
            and hasattr(forecast, "owner")
            and forecast.owner
        ):
            period_trend_data = trend_data[period.id]

            if (
                "user_data" in period_trend_data
                and "previous_period_id" in period_trend_data
            ):
                user_data = period_trend_data["user_data"].get(forecast.owner.id, {})
                previous_period_id = period_trend_data["previous_period_id"]

                current_user_data = user_data.get(
                    period.id, {"commit": 0, "best_case": 0, "pipeline": 0, "closed": 0}
                )
                previous_user_data = user_data.get(
                    previous_period_id,
                    {"commit": 0, "best_case": 0, "pipeline": 0, "closed": 0},
                )

                forecast.commit_trend = self.calculate_trend_direction(
                    current_user_data["commit"], previous_user_data["commit"]
                )
                forecast.best_case_trend = self.calculate_trend_direction(
                    current_user_data["best_case"], previous_user_data["best_case"]
                )
                forecast.pipeline_trend = self.calculate_trend_direction(
                    current_user_data["pipeline"], previous_user_data["pipeline"]
                )
                forecast.closed_trend = self.calculate_trend_direction(
                    current_user_data["closed"], previous_user_data["closed"]
                )

                try:
                    previous_period = Period.objects.get(id=previous_period_id)
                    forecast.commit_change_text = self.format_change_text(
                        current_user_data["commit"],
                        previous_user_data["commit"],
                        previous_period.name,
                        forecast_type.is_quantity_based,
                        self.get_company_for_user.currency,
                    )
                    forecast.best_case_change_text = self.format_change_text(
                        current_user_data["best_case"],
                        previous_user_data["best_case"],
                        previous_period.name,
                        forecast_type.is_quantity_based,
                        self.get_company_for_user.currency,
                    )
                    forecast.pipeline_change_text = self.format_change_text(
                        current_user_data["pipeline"],
                        previous_user_data["pipeline"],
                        previous_period.name,
                        forecast_type.is_quantity_based,
                        self.get_company_for_user.currency,
                    )
                    forecast.closed_change_text = self.format_change_text(
                        current_user_data["closed"],
                        previous_user_data["closed"],
                        previous_period.name,
                        forecast_type.is_quantity_based,
                        self.get_company_for_user.currency,
                    )
                except Period.DoesNotExist:
                    forecast.commit_change_text = ""
                    forecast.best_case_change_text = ""
                    forecast.pipeline_change_text = ""
                    forecast.closed_change_text = ""
            else:
                # Use period-level trends as fallback
                forecast.commit_trend = period_trend_data.get("commit_trend")
                forecast.best_case_trend = period_trend_data.get("best_case_trend")
                forecast.pipeline_trend = period_trend_data.get("pipeline_trend")
                forecast.closed_trend = period_trend_data.get("closed_trend")
                forecast.commit_change_text = period_trend_data.get(
                    "commit_change_text", ""
                )
                forecast.best_case_change_text = period_trend_data.get(
                    "best_case_change_text", ""
                )
                forecast.pipeline_change_text = period_trend_data.get(
                    "pipeline_change_text", ""
                )
                forecast.closed_change_text = period_trend_data.get(
                    "closed_change_text", ""
                )
        else:
            # No trend data available
            forecast.commit_trend = None
            forecast.best_case_trend = None
            forecast.pipeline_trend = None
            forecast.closed_trend = None
            forecast.commit_change_text = ""
            forecast.best_case_change_text = ""
            forecast.pipeline_change_text = ""
            forecast.closed_change_text = ""

        return forecast

    def create_empty_user_forecast(
        self, period, forecast_type, user_id, currency_symbol, target=None
    ):
        """Create a placeholder forecast for a user with no data."""

        class EmptyUserForecast:
            """Placeholder forecast with zero values for users without data."""

            def __init__(self):
                self.id = f"empty_{period.id}_{user_id}"
                self.period = period
                self.quarter = period.quarter
                self.fiscal_year = period.quarter.fiscal_year
                self.forecast_type = forecast_type
                self.currency_symbol = currency_symbol
                self.owner = HorillaUser.objects.get(id=user_id)

                if target and forecast_type.is_quantity_based:
                    self.target_quantity = target.target_amount
                    self.pipeline_quantity = 0
                    self.best_case_quantity = 0
                    self.commit_quantity = 0
                    self.closed_quantity = 0
                    self.actual_quantity = 0
                    self.gap_quantity = self.target_quantity
                elif target:
                    self.target_amount = target.target_amount
                    self.pipeline_amount = 0
                    self.best_case_amount = 0
                    self.commit_amount = 0
                    self.closed_amount = 0
                    self.actual_amount = 0
                    self.gap_amount = self.target_amount
                else:
                    if forecast_type.is_quantity_based:
                        self.target_quantity = 0
                        self.pipeline_quantity = 0
                        self.best_case_quantity = 0
                        self.commit_quantity = 0
                        self.closed_quantity = 0
                        self.actual_quantity = 0
                        self.gap_quantity = 0
                    else:
                        self.target_amount = 0
                        self.pipeline_amount = 0
                        self.best_case_amount = 0
                        self.commit_amount = 0
                        self.closed_amount = 0
                        self.actual_amount = 0
                        self.gap_amount = 0

                self.performance_percentage = 0
                self.gap_percentage = 0
                self.closed_percentage = 0
                self.closed_deals_count = 0

        empty_forecast = EmptyUserForecast()
        aggregated_forecast = self.create_aggregated_forecast(
            period, forecast_type, [empty_forecast], currency_symbol, user_id, target
        )
        aggregated_forecast.user_forecasts = []
        return aggregated_forecast

    def create_aggregated_forecast(
        self,
        period,
        forecast_type,
        user_forecasts,
        currency_symbol,
        _user_id=None,
        target=None,
    ):
        """Create aggregated forecast with optimized calculations and target integration."""

        class AggregatedForecast:
            """
            Aggregated forecast data for a SINGLE period, combining data
            from multiple users for that specific period.
            """

            def __init__(self):
                self.id = f"period_{period.id}"
                self.period = period
                self.quarter = period.quarter
                self.fiscal_year = period.quarter.fiscal_year
                self.forecast_type = forecast_type
                self.currency_symbol = currency_symbol
                self.commit_trend = None
                self.best_case_trend = None
                self.pipeline_trend = None
                self.closed_trend = None
                self.commit_change_text = ""
                self.best_case_change_text = ""
                self.pipeline_change_text = ""
                self.closed_change_text = ""

                # Initialize pagination attributes for multi-user view
                self.has_next = False
                self.next_page = None
                self.view_id = None
                self.user_forecasts = []

                if target and forecast_type.is_quantity_based:
                    self.target_quantity = (
                        target.target_amount if hasattr(target, "target_amount") else 0
                    )
                    self.pipeline_quantity = 0
                    self.best_case_quantity = 0
                    self.commit_quantity = 0
                    self.closed_quantity = 0
                    self.actual_quantity = 0
                    self.gap_quantity = 0
                elif target:
                    self.target_amount = (
                        target.target_amount if hasattr(target, "target_amount") else 0
                    )
                    self.pipeline_amount = 0
                    self.best_case_amount = 0
                    self.commit_amount = 0
                    self.closed_amount = 0
                    self.actual_amount = 0
                    self.gap_amount = 0
                else:
                    if forecast_type.is_quantity_based:
                        self.target_quantity = 0
                        self.pipeline_quantity = 0
                        self.best_case_quantity = 0
                        self.commit_quantity = 0
                        self.closed_quantity = 0
                        self.actual_quantity = 0
                        self.gap_quantity = 0
                    else:
                        self.target_amount = 0
                        self.pipeline_amount = 0
                        self.best_case_amount = 0
                        self.commit_amount = 0
                        self.closed_amount = 0
                        self.actual_amount = 0
                        self.gap_amount = 0

                self.performance_percentage = 0
                self.gap_percentage = 0
                self.closed_percentage = 0
                self.closed_deals_count = 0

        aggregated = AggregatedForecast()

        if user_forecasts:
            if forecast_type.is_quantity_based:
                aggregated.pipeline_quantity = sum(
                    f.pipeline_quantity or 0 for f in user_forecasts
                )
                aggregated.best_case_quantity = sum(
                    f.best_case_quantity or 0 for f in user_forecasts
                )
                aggregated.commit_quantity = sum(
                    f.commit_quantity or 0 for f in user_forecasts
                )
                aggregated.closed_quantity = sum(
                    f.closed_quantity or 0 for f in user_forecasts
                )
                aggregated.actual_quantity = sum(
                    f.actual_quantity or 0 for f in user_forecasts
                )

                if aggregated.target_quantity > 0:
                    aggregated.gap_quantity = (
                        aggregated.target_quantity - aggregated.actual_quantity
                    )
                    aggregated.performance_percentage = (
                        aggregated.actual_quantity / aggregated.target_quantity
                    ) * 100
                    aggregated.gap_percentage = (
                        aggregated.gap_quantity / aggregated.target_quantity
                    ) * 100
                    aggregated.closed_percentage = (
                        aggregated.closed_quantity / aggregated.target_quantity
                    ) * 100
            else:
                aggregated.pipeline_amount = sum(
                    f.pipeline_amount or 0 for f in user_forecasts
                )
                aggregated.best_case_amount = sum(
                    f.best_case_amount or 0 for f in user_forecasts
                )
                aggregated.commit_amount = sum(
                    f.commit_amount or 0 for f in user_forecasts
                )
                aggregated.closed_amount = sum(
                    f.closed_amount or 0 for f in user_forecasts
                )
                aggregated.actual_amount = sum(
                    f.actual_amount or 0 for f in user_forecasts
                )

                if aggregated.target_amount > 0:
                    aggregated.gap_amount = (
                        aggregated.target_amount - aggregated.actual_amount
                    )
                    aggregated.performance_percentage = (
                        aggregated.actual_amount / aggregated.target_amount
                    ) * 100
                    aggregated.gap_percentage = (
                        aggregated.gap_amount / aggregated.target_amount
                    ) * 100
                    aggregated.closed_percentage = (
                        aggregated.closed_amount / aggregated.target_amount
                    ) * 100

            aggregated.closed_deals_count = len(user_forecasts)

        return aggregated


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "opportunities.view_opportunity",
            "opportunities.view_own_opportunity",
        ],
    ),
    name="dispatch",
)
class ForecastOpportunitiesView(LoginRequiredMixin, View):
    """HTMX-enabled modal view for displaying opportunities categorized by forecast type."""

    def col_attrs(self):
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        attrs = {}
        if self.request.user.has_perm(
            "opportunities.view_opportunity"
        ) or self.request.user.has_perm("opportunities.view_own_opportunity"):
            attrs = {
                "hx-get": f"{{get_detail_url}}?{query_string}",
                "hx-target": "#mainContent",
                "hx-swap": "outerHTML",
                "hx-push-url": "true",
                "hx-on:click": "closeContentModal()",
                "hx-select": "#mainContent",
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

    def get(self, request, forecast_id=None, opportunity_type=None):
        """
        Handle GET requests to display opportunities modal content with categorized
        opportunities and list views.
        """
        user_id = request.GET.get("user_id")
        has_view_all = request.user.has_perm("opportunities.view_opportunity")
        has_view_own = request.user.has_perm("opportunities.view_own_opportunity")

        if has_view_own and not has_view_all:
            if user_id and user_id != str(request.user.pk):
                return render(request, "error/403.html")
            if not user_id:
                user_id = str(request.user.pk)
        try:
            if forecast_id == "total":
                fiscal_year_id = request.GET.get("fiscal_year_id")
                fiscal_year = (
                    FiscalYearInstance.objects.get(id=fiscal_year_id)
                    if fiscal_year_id
                    and FiscalYearInstance.objects.filter(id=fiscal_year_id).exists()
                    else FiscalYearInstance.objects.filter(is_current=True).first()
                )

                class TotalForecastObject:
                    """Pseudo-forecast representing aggregated data across all periods."""

                    def __init__(self, fiscal_year):
                        self.id = "total"
                        self.fiscal_year = fiscal_year
                        self.period = None  # No specific period for total
                        self.forecast_type = ForecastType.objects.filter(
                            id=request.GET.get("forecast_type_id")
                        ).first()

                forecast = TotalForecastObject(fiscal_year)
            else:
                forecast = self.get_forecast_object(forecast_id)

                # Additional check: if user has view_own only, verify they own this forecast
                if has_view_own and not has_view_all:
                    if hasattr(forecast, "owner") and forecast.owner:
                        if forecast.owner.id != request.user.pk:
                            return render(request, "error/403.html")

            company = request.active_company
            currency_symbol = company.currency if company else "USD"

            opportunity_types = [
                {"key": "closed", "display_name": "Closed"},
                {"key": "committed", "display_name": "Committed"},
                {"key": "best_case", "display_name": "Best Case"},
                {"key": "open_pipeline", "display_name": "Open Pipeline"},
            ]

            for type_info in opportunity_types:
                type_info["opportunities"] = self.get_opportunities_by_type(
                    forecast, type_info["key"], user_id
                )
                columns = [("Opportunity Name", "name")]
                if (
                    hasattr(forecast, "forecast_type")
                    and forecast.forecast_type
                    and forecast.forecast_type.is_quantity_based
                ):
                    columns.append(("Quantity", "quantity"))
                else:
                    columns.append(("Amount", "amount"))
                columns.extend(
                    [
                        ("Close Date", "close_date"),
                        ("Stage", "stage__name"),
                    ]
                )
                if type_info["key"] != "closed":
                    columns.append(("Probability", "probability"))

                list_view = HorillaListView(
                    model=Opportunity,
                    view_id=f"forecast-opportunities-{type_info['key']}",
                    search_url=reverse_lazy(
                        "forecast:forecast_opportunities",
                        kwargs={
                            "forecast_id": forecast_id or "total",
                            "opportunity_type": type_info["key"],
                        },
                    ),
                    main_url=reverse_lazy(
                        "forecast:forecast_opportunities",
                        kwargs={
                            "forecast_id": forecast_id or "total",
                            "opportunity_type": type_info["key"],
                        },
                    ),
                    table_width=False,
                    columns=columns,
                    table_height_as_class="h-[400px]",
                    bulk_select_option=False,
                    clear_session_button_enabled=False,
                    list_column_visibility=False,
                    bulk_delete_enabled=False,
                    bulk_update_option=False,
                    enable_sorting=False,
                    save_to_list_option=False,
                )

                list_view.get_queryset = lambda ti=type_info: ti[
                    "opportunities"
                ].select_related("stage")
                no_record_msg = (
                    f"There are no '{type_info['display_name']}' opportunities "
                    "for this period."
                )
                list_view.request = request
                list_view.object_list = type_info["opportunities"]
                list_view.no_record_msg = no_record_msg
                list_view.col_attrs = self.col_attrs()
                list_context = list_view.get_context_data()
                type_info["list_view_html"] = render_to_string(
                    "list_view.html", list_context, request=request
                )

            opportunities = self.get_opportunities_by_type(
                forecast, opportunity_type, user_id
            )
            display_type = opportunity_type.replace("_", " ").title()
            if opportunity_type == "best_case":
                display_type = "Best Case"

            context = {
                "opportunities": opportunities,
                "opportunity_type": display_type,
                "opportunity_types": opportunity_types,
                "forecast": forecast,
                "currency_symbol": currency_symbol,
                "forecast_type": (
                    forecast.forecast_type
                    if hasattr(forecast, "forecast_type")
                    else None
                ),
                "user_id": user_id,
                "fiscal_year_id": request.GET.get("fiscal_year_id"),
                "has_view_all": has_view_all,
                "has_view_own": has_view_own,
            }

            return render(request, "forecast_opportunities_modal_content.html", context)

        except Exception as e:
            raise HorillaHttp404(e)

    def get_forecast_object(self, forecast_id):
        """
        Generate tab configuration for each active forecast type in the company.
        Returns list of tab dictionaries with title, URL, target, and ID.
        """
        fiscal_year_id = self.request.GET.get("fiscal_year_id")
        fiscal_year = (
            FiscalYearInstance.objects.get(id=fiscal_year_id)
            if fiscal_year_id
            and FiscalYearInstance.objects.filter(id=fiscal_year_id).exists()
            else FiscalYearInstance.objects.filter(is_current=True).first()
        )

        if forecast_id.startswith("period_"):
            period_id = forecast_id.replace("period_", "")
            period = get_object_or_404(
                Period, id=period_id, quarter__fiscal_year=fiscal_year
            )

            class ForecastObject:
                """Pseudo-forecast constructed from a period for aggregated views."""

                def __init__(self, period):
                    self.id = forecast_id
                    self.period = period
                    self.quarter = period.quarter
                    self.fiscal_year = period.quarter.fiscal_year
                    self.forecast_type = (
                        period.forecast_type
                        if hasattr(period, "forecast_type")
                        else None
                    )

            return ForecastObject(period)

        try:
            forecast = get_object_or_404(
                Forecast, id=forecast_id, fiscal_year=fiscal_year
            )
        except Exception as e:
            raise HorillaHttp404(e)

        return forecast

    def get_opportunities_by_type(self, forecast, opportunity_type, user_id=None):
        """
        Get opportunities based on the type requested
        """
        base_queryset = self.get_base_opportunity_queryset(forecast, user_id)

        if opportunity_type == "closed":
            return base_queryset.filter(stage__stage_type="won").select_related(
                "account", "stage"
            )

        if opportunity_type == "committed":
            return base_queryset.filter(
                forecast_category="commit", stage__stage_type="open"
            ).select_related("account", "stage")

        if opportunity_type == "best_case":
            return base_queryset.filter(
                forecast_category__in=["best_case", "commit"], stage__stage_type="open"
            ).select_related("account", "stage")

        if opportunity_type == "open_pipeline":
            return base_queryset.filter(
                forecast_category="pipeline", stage__stage_type="open"
            ).select_related("account", "stage")

        return base_queryset.none()

    def get_base_opportunity_queryset(self, forecast, user_id=None):
        """
        Get base queryset for opportunities in this forecast period or all periods for 'total'
        """
        # Additional permission check in queryset
        has_view_all = self.request.user.has_perm("opportunities.view_opportunity")
        has_view_own = self.request.user.has_perm("opportunities.view_own_opportunity")

        if forecast.id == "total":
            # For total, include all opportunities in the fiscal year
            queryset = Opportunity.objects.filter(
                close_date__gte=forecast.fiscal_year.start_date,
                close_date__lte=forecast.fiscal_year.end_date,
            )
        else:
            queryset = Opportunity.objects.filter(
                close_date__gte=forecast.period.start_date,
                close_date__lte=forecast.period.end_date,
            )

        # Enforce view_own permission
        if has_view_own and not has_view_all:
            queryset = queryset.filter(owner_id=self.request.user.pk)
        elif user_id:
            queryset = queryset.filter(owner_id=user_id)

        if (
            hasattr(forecast, "id")
            and not str(forecast.id).startswith("period_")
            and not forecast.id == "total"
            and hasattr(forecast, "owner")
            and forecast.owner
        ):
            queryset = queryset.filter(owner=forecast.owner)

        return queryset
