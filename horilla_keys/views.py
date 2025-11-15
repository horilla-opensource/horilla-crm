"""
Views for the horilla_keys app
"""

import logging
from functools import cached_property

from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View

from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_keys.filters import ShortKeyFilter
from horilla_keys.forms import ShortcutKeyForm
from horilla_keys.models import ShortcutKey

logger = logging.getLogger(__name__)
User = get_user_model()
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator

from horilla_core.decorators import htmx_required


class ShortKeyView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for short key view.
    """

    template_name = "short_key_view.html"
    nav_url = reverse_lazy("horilla_keys:short_key_nav")
    list_url = reverse_lazy("horilla_keys:short_key_list")


@method_decorator(htmx_required, name="dispatch")
class ShortKeyNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar fro short key
    """

    nav_title = _("Short Keys")
    search_url = reverse_lazy("horilla_keys:short_key_list")
    main_url = reverse_lazy("horilla_keys:short_key_view")
    filterset_class = ShortKeyFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "ShortcutKey"
    model_app_label = "horilla_keys"
    nav_width = False
    gap_enabled = False

    @cached_property
    def new_button(self):
        return {
            "url": f"""{ reverse_lazy('horilla_keys:short_key_create')}?new=true""",
            "attrs": {"id": "short-key-create"},
        }


@method_decorator(htmx_required, name="dispatch")
class ShortKeyListView(LoginRequiredMixin, HorillaListView):
    """
    List view of user short key
    """

    model = ShortcutKey
    view_id = "short_key_list"
    filterset_class = ShortKeyFilter
    search_url = reverse_lazy("horilla_keys:short_key_list")
    main_url = reverse_lazy("horilla_keys:short_key_view")
    table_width = False
    bulk_select_option = False
    store_ordered_ids = True
    table_height_as_class = "h-[500px]"
    list_column_visibility = False

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (instance._meta.get_field("page").verbose_name, "get_page_title"),
            (instance._meta.get_field("key").verbose_name, "custom_key_col"),
        ]

    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.user
        if user_id:
            queryset = queryset.filter(user=user_id)
        return queryset

    @cached_property
    def actions(self):
        actions = [
            {
                "action": "Edit",
                "src": "assets/icons/edit.svg",
                "img_class": "w-4 h-4",
                "attrs": """
                        hx-get="{get_edit_url}?new=true"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal()"
                        """,
            },
            {
                "action": "Delete",
                "src": "assets/icons/a4.svg",
                "img_class": "w-4 h-4",
                "attrs": """
                        hx-post="{get_delete_url}"
                        hx-target="#deleteModeBox"
                        hx-swap="innerHTML"
                        hx-trigger="click"
                        hx-vals='{{"check_dependencies": "true"}}'
                        onclick="openDeleteModeModal()"
                    """,
            },
        ]
        return actions


@method_decorator(htmx_required, name="dispatch")
class ShortKeyFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    create and update from view for short key
    """

    model = ShortcutKey
    form_class = ShortcutKeyForm
    modal_height = False
    form_title = _("Short Key")
    full_width_fields = ["page"]
    hidden_fields = ["is_active", "user"]

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("horilla_keys:short_key_update", kwargs={"pk": pk})
        return reverse_lazy("horilla_keys:short_key_create")

    def get_initial(self):
        initial = super().get_initial()
        initial["user"] = self.request.user
        company = getattr(self.request, "active_company", None)
        initial["company"] = company
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

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
class ShortcutKeyDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = ShortcutKey

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")


class ShortKeyDataView(LoginRequiredMixin, View):
    """
    View to return shortcut data as JSON for the current user.
    """

    def get(self, request, *args, **kwargs):
        shortcuts = [
            {
                "key": sk.key,
                "page": sk.page,
                "command": sk.command.lower(),
                "section": sk.get_section(),
                "title": sk.get_page_title(),
            }
            for sk in ShortcutKey.objects.filter(user=request.user)
        ]
        return JsonResponse({"shortcuts": shortcuts})
