"""
This view handles the methods for department view
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_core.filters import DepartmentFilter
from horilla_core.models import Department
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_notifications.models import Notification


class DepartmentView(LoginRequiredMixin, HorillaView):
    """
    Templateviews for department page
    """

    template_name = "department/department_view.html"
    nav_url = reverse_lazy("horilla_core:department_nav_view")
    list_url = reverse_lazy("horilla_core:department_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("horilla_core.view_department"), name="dispatch")
class DepartmentNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar fro department
    """

    nav_title = Department._meta.verbose_name_plural
    search_url = reverse_lazy("horilla_core:department_list_view")
    main_url = reverse_lazy("horilla_core:department_view")
    filterset_class = DepartmentFilter
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "Department"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False
    url_name = "department_list_view"

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("horilla_core.add_department"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:department_create_form')}?new=true""",
                "attrs": {"id": "department-create"},
            }

    @cached_property
    def actions(self):
        if self.request.user.has_perm("horilla_core.view_department"):
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
    permission_required_or_denied("horilla_core.view_department"), name="dispatch"
)
class DepartmentListView(LoginRequiredMixin, HorillaListView):
    """
    List view of department
    """

    model = Department
    view_id = "department_list"
    filterset_class = DepartmentFilter
    search_url = reverse_lazy("horilla_core:department_list_view")
    main_url = reverse_lazy("horilla_core:department_view")
    table_width = False
    # bulk_select_option = False
    bulk_update_option = False
    table_height_as_class = "h-[500px]"

    def no_record_add_button(self):
        if self.request.user.has_perm("horilla_core.add_department"):
            return {
                "url": f"""{ reverse_lazy('horilla_core:department_create_form')}?new=true""",
                "attrs": 'id="department-create"',
            }

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (
                instance._meta.get_field("department_name").verbose_name,
                "department_name",
            ),
            (instance._meta.get_field("description").verbose_name, "description"),
        ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_core.change_department"):
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
                }
            )
        if self.request.user.has_perm("horilla_core.delete_department"):
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
    permission_required_or_denied("horilla_core.add_department"), name="dispatch"
)
class DepartmentFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    create and update from view for department
    """

    model = Department
    fields = ["department_name", "description"]
    full_width_fields = ["department_name", "description"]
    modal_height = False
    form_title = _("Department")

    @cached_property
    def form_url(self):
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "horilla_core:department_update_form", kwargs={"pk": pk}
            )
        return reverse_lazy("horilla_core:department_create_form")

    def form_valid(self, form):
        self.object = form.save()

        if not self.kwargs.get("pk"):
            Notification.objects.create(
                user=self.request.user,
                message=f"New Department '{self.object}' created successfully.",
                sender=self.request.user,
                url=reverse("horilla_core:department_view"),
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
    permission_required_or_denied("horilla_core.delete_department"), name="dispatch"
)
class DepartmentDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    model = Department

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")
