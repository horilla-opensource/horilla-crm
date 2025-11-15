"""
This view handles the methods for user sepcific holidays view
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from horilla_core.decorators import htmx_required
from horilla_core.filters import HolidayFilter
from horilla_core.models import Holiday
from horilla_generics.views import (
    HorillaListView,
    HorillaModalDetailView,
    HorillaNavView,
    HorillaView,
)


class UserHolidayView(LoginRequiredMixin, HorillaView):
    """
    Templateviews for user sepcific holiday page
    """

    template_name = "holidays/user_holiday_view.html"
    nav_url = reverse_lazy("horilla_core:user_holiday_nav")
    list_url = reverse_lazy("horilla_core:user_holiday_list")


@method_decorator(htmx_required, name="dispatch")
class UserHolidayNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar fro user sepcific holidays
    """

    nav_title = _("My Holidays")
    search_url = reverse_lazy("horilla_core:user_holiday_list")
    main_url = reverse_lazy("horilla_core:user_holiday_view")
    filterset_class = HolidayFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "Holiday"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False


@method_decorator(htmx_required, name="dispatch")
class UserHolidayListView(LoginRequiredMixin, HorillaListView):
    """
    List view of user sepcific holidays
    """

    model = Holiday
    view_id = "user_holiday_list"
    filterset_class = HolidayFilter
    search_url = reverse_lazy("horilla_core:user_holiday_list")
    main_url = reverse_lazy("horilla_core:user_holiday_view")
    table_width = False
    bulk_select_option = False
    store_ordered_ids = True

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("name").verbose_name, "name"),
            (instance._meta.get_field("start_date").verbose_name, "start_date"),
            (instance._meta.get_field("end_date").verbose_name, "end_date"),
            (instance._meta.get_field("is_recurring").verbose_name, "is_recurring"),
            (_("Holiday Type"), "holiday_type"),
        ]

    def get_queryset(self):
        user = self.request.user
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name

        queryset = Holiday.objects.all()

        if user.has_perm(f"{app_label}.view_{model_name}"):
            pass
        elif user.has_perm(f"{app_label}.view_own_{model_name}"):
            queryset = queryset.filter(
                Q(all_users=True) | Q(specific_users=user)
            ).distinct()
        else:
            queryset = queryset.none()

        if self.store_ordered_ids:
            self.request.session[f"ordered_ids_{self.model.__name__.lower()}"] = list(
                queryset.values_list("pk", flat=True)
            )

        return queryset

    @cached_property
    def col_attrs(self):
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = self.request.session.get(self.ordered_ids_key, [])
        htmx_attrs = {
            "hx-get": f"{{get_user_detail_url}}?instance_ids={query_string}",
            "hx-target": "#detailModalBox",
            "hx-swap": "innerHTML",
            "hx-push-url": "false",
            "hx-on:click": "openDetailModal();",
        }
        return [
            {
                "name": {
                    "style": "cursor:pointer",
                    "class": "hover:text-primary-600",
                    **htmx_attrs,
                }
            }
        ]


@method_decorator(htmx_required, name="dispatch")
class UserHolidayDetailView(LoginRequiredMixin, HorillaModalDetailView):
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
