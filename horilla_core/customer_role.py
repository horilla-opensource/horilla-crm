"""
This view handles the methods for team role view
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_core.filters import CustomerRoleFilter
from horilla_core.models import CustomerRole
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_notifications.models import Notification


class CustomerRoleView(LoginRequiredMixin, HorillaView):
    """
    Template view for customer role page
    """

    template_name = "customer_role/customer_role_view.html"
    nav_url = reverse_lazy("horilla_core:customer_role_nav_view")
    list_url = reverse_lazy("horilla_core:customer_role_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required("horilla_core.view_customerrole"), name="dispatch"
)
class CustomerRoleNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar fro customer role
    """

    nav_title = CustomerRole._meta.verbose_name_plural
    search_url = reverse_lazy("horilla_core:customer_role_list_view")
    main_url = reverse_lazy("horilla_core:customer_role_view")
    filterset_class = CustomerRoleFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "CustomerRole"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False
    url_name = "customer_role_list_view"

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("horilla_core.add_customerrole"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:customer_role_create_form')}?new=true""",
                "attrs": {"id": "customer-role-create"},
            }

    @cached_property
    def actions(self):
        if self.request.user.has_perm("horilla_core.view_customerrole"):
            return [
                {
                    "action": _("Add column to list"),
                    "attrs": f"""
                            hx-get="{reverse_lazy('horilla_generics:column_selector')}?app_label={self.model_app_label}&model_name={self.model_name}&url_name={self.url_name}"
                            onclick="openModal()"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            """,
                }
            ]


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_customerrole"), name="dispatch"
)
class CustomerRoleListView(LoginRequiredMixin, HorillaListView):
    """
    List view of customer role
    """

    model = CustomerRole
    view_id = "customer_role_list"
    filterset_class = CustomerRoleFilter
    search_url = reverse_lazy("horilla_core:customer_role_list_view")
    main_url = reverse_lazy("horilla_core:customer_role_view")
    table_width = False
    bulk_select_option = False
    header_attrs = [
        {"description": {"style": "width: 300px;"}},
    ]

    def no_record_add_button(self):
        if self.request.user.has_perm("horilla_core.add_customerrole"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:customer_role_create_form')}?new=true""",
                "attrs": 'id="customer-role-create"',
            }

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (
                instance._meta.get_field("customer_role_name").verbose_name,
                "customer_role_name",
            ),
            (instance._meta.get_field("description").verbose_name, "description"),
        ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_core.change_customerrole"):
            actions.append(
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
            )
        if self.request.user.has_perm("horilla_core.delete_customerrole"):
            actions.append(
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
                }
            )
        return actions


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.add_customerrole"), name="dispatch"
)
class CustomerRoleFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    create and update from view for customer role
    """

    model = CustomerRole
    fields = ["customer_role_name", "description"]
    full_width_fields = ["customer_role_name", "description"]
    modal_height = False
    form_title = _("Customer Role")

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_core:customer_role_update_form", kwargs={"pk": pk}
            )
        return reverse_lazy("horilla_core:customer_role_create_form")

    def form_valid(self, form):
        self.object = form.save()

        if not self.kwargs.get("pk"):
            Notification.objects.create(
                user=self.request.user,
                message=f"New Customer Role '{self.object}' created successfully.",
                sender=self.request.user,
                url=reverse_lazy("horilla_core:customer_role_view"),
            )

        response = super().form_valid(form)

        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

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
    permission_required_or_denied("horilla_core.delete_customerrole"), name="dispatch"
)
class CustomerRoleDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = CustomerRole

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")
