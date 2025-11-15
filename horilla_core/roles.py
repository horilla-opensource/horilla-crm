from functools import cached_property
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView

from horilla_core.decorators import htmx_required, permission_required_or_denied
from horilla_core.filters import UserFilter
from horilla_core.forms import AddUsersToRoleForm
from horilla_core.models import HorillaUser, Role
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
)
from horilla_utils.middlewares import _thread_local


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.add_role"), name="dispatch"
)
class AddRole(LoginRequiredMixin, HorillaSingleFormView):

    model = Role
    fields = ["role_name", "parent_role", "description"]
    full_width_fields = ["role_name", "parent_role", "description"]
    modal_height = False
    # hidden_fields = ["parent_role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = getattr(_thread_local, "request", None)
        role_id = request.GET.get("role_id")
        role_count = Role.objects.all().count()
        if role_id or role_count == 0:
            self.hidden_fields = ["parent_role"]

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("horilla_core:edit_roles_view", kwargs={"pk": pk})
        return reverse_lazy("horilla_core:create_roles_view")

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        if pk:
            try:
                self.model.objects.get(pk=pk)
            except self.model.DoesNotExist:
                messages.error(request, "The requested role does not exist.")
                return HttpResponse("<script>$('reloadButton').click();</script>")

        return super().get(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        role_id = self.request.GET.get("role_id")
        role = Role.objects.filter(pk=role_id).first()
        if role:
            initial["parent_role"] = role
        return initial

    def form_valid(self, form):
        super().form_valid(form)
        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.craete_horillauser"), name="dispatch"
)
class AddUserToRole(LoginRequiredMixin, HorillaSingleFormView):

    model = HorillaUser
    form_class = AddUsersToRoleForm
    full_width_fields = ["role", "users"]
    modal_height = False
    form_url = reverse_lazy("horilla_core:add_user_to_roles_view")
    hidden_fields = ["role"]

    def get_initial(self):
        initial = super().get_initial()
        role_id = self.request.GET.get("role_id")
        role = Role.objects.filter(pk=role_id).first()  # Get the first object or None
        if role:
            initial["role"] = role
        return initial

    def form_valid(self, form):
        users = form.save(commit=True)
        messages.success(
            self.request,
            _(
                f"Successfully assigned {len(users)} user(s) to the role '{form.cleaned_data['role']}'."
            ),
        )
        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_horillauser"), name="dispatch"
)
class RoleUsersListView(LoginRequiredMixin, HorillaListView):

    model = HorillaUser
    filterset_class = UserFilter
    table_width = False
    view_id = "user-roles"

    search_url = reverse_lazy("horilla_core:view_user_in_role_list_view")
    main_url = reverse_lazy("horilla_core:view_user_in_role")
    bulk_delete_enabled = False
    bulk_update_fields = ["role"]

    def get_queryset(self):
        queryset = super().get_queryset()
        role_id = self.request.GET.get("role_id")
        queryset = queryset.filter(role=role_id)
        return queryset

    @cached_property
    def col_attrs(self):
        query_params = self.request.GET.dict()
        query_params = {}
        if "section" in self.request.GET:
            query_params["section"] = self.request.GET.get("section")
        query_string = urlencode(query_params)
        htmx_attrs = {
            "hx-get": f"{{get_detail_view_url}}?{query_string}",
            "hx-target": "#role-container",
            "hx-swap": "outerHTML",
            "hx-push-url": "true",
            "hx-select": "#users-view",
            "hx-on:click": "closeContentModal()",
        }
        return [
            {
                "get_avatar_with_name": {
                    "style": "cursor:pointer",
                    "class": "hover:text-primary-600",
                    **htmx_attrs,
                }
            }
        ]

    columns = [
        (_("Users"), "get_avatar_with_name"),
    ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_core.delete_role"):
            actions.append(
                {
                    "action": "Delete",
                    "src": "assets/icons/a4.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                    hx-post="{get_delete_user_from_role}"
                    hx-target="#deleteModeBox"
                    hx-swap="innerHTML"
                    hx-trigger="confirmed"
                    hx-on:click="hxConfirm(this,'Are you sure you want to delete the user from this role?')"
                    hx-on::after-request="$('#reloadMessagesButton').click();"
                """,
                }
            )
        return actions


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_horillauser"), name="dispatch"
)
class UsersInRoleView(LoginRequiredMixin, TemplateView):

    template_name = "role/view_user.html"


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_horillauser"), name="dispatch"
)
class RoleUsersNavView(LoginRequiredMixin, HorillaNavView):

    search_url = reverse_lazy("horilla_core:view_user_in_role_list_view")
    main_url = reverse_lazy("horilla_core:view_user_in_role")
    filterset_class = UserFilter
    model_name = "HorillaUser"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False
    all_view_types = False
    recently_viewed_option = False
    one_view_only = True
    reload_option = False
    border_enabled = False
    navbar_indication = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role_id = self.request.GET.get("role_id")
        role = Role.objects.filter(pk=role_id).first()
        self.nav_title = role

        context["nav_title"] = self.nav_title
        return context

    def get_navbar_indication_attrs(self):

        return {"onclick": "closeContentModal()"}


@method_decorator(htmx_required, name="dispatch")
class DeleteUserFromRole(LoginRequiredMixin, View):
    """
    Remove role from a user (without deleting the user)
    """

    def post(self, request, *args, **kwargs):
        user_id = kwargs.get("pk")
        try:
            user = get_object_or_404(HorillaUser, pk=user_id)
        except:
            messages.error(request, _("The requested user does not exist."))
            return HttpResponse(
                "<script>$('#reloadButton').click();closeDeleteModeModal();closeContentModal();</script>"
            )

        user.role = None
        user.save()

        messages.success(request, f"{user.username} removed from role")

        return HttpResponse(
            "<script>"
            "htmx.trigger('#reloadButton','click');"
            "closeDeleteModeModal();"
            "closeContentModal();"
            "</script>"
        )


@method_decorator(htmx_required, name="dispatch")
class RoleDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):

    model = Role

    def get_post_delete_response(self):

        return HttpResponse(
            "<script>$('#reloadButton').click();closeDeleteModeModal();</script>"
        )
