"""
This view handles the methods for recycle bin view
"""

import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django.views import View

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_core.models import RecycleBin, RecycleBinPolicy
from horilla_core.utils import delete_recycle_bin_records, restore_recycle_bin_records
from horilla_generics.views import HorillaListView, HorillaNavView, HorillaView


class RecycleBinView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for recycle bin page.
    """

    template_name = "settings/recycle_bin/recycle_bin.html"
    nav_url = reverse_lazy("horilla_core:recycle_bin_navbar")
    list_url = reverse_lazy("horilla_core:recycle_bin_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("horilla_core.view_recyclebin"), name="dispatch")
class RecycleBinNavbar(LoginRequiredMixin, HorillaNavView):
    """
    navbar for recyclebin
    """

    nav_title = RecycleBin._meta.verbose_name_plural
    main_url = reverse_lazy("horilla_core:recycle_bin_view")
    one_view_only = True
    all_view_types = False
    filter_option = False
    reload_option = False
    model_name = "RecycleBin"
    model_app_label = "horilla_core"
    nav_width = False
    gap_enabled = False
    url_name = "recycle_bin_list_view"
    search_option = False


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_recyclebin"), name="dispatch"
)
class RecycleBinListView(LoginRequiredMixin, HorillaListView):
    """
    listview for recyclebin
    """

    model = RecycleBin
    view_id = "RecycleBinlist"
    main_url = reverse_lazy("horilla_core:recycle_bin_view")
    bulk_update_option = False
    table_width = False
    bulk_delete_enabled = False
    bulk_export_option = False
    table_height_as_class = "h-[500px]"
    clear_session_button_enabled = False

    custom_bulk_actions = [
        {
            "name": "delete",
            "label": "Delete",
            "url": reverse_lazy("horilla_core:bulk_recycle_bin_delete"),
            "method": "post",
            "target": "#modalBox",
            "swap": "innerHTML",
            "icon": "fa-trash-alt",
            "bg_color": "#ff980026",
            "hover_bg_color": "#ff9800",
            "text_color": "#ff9800",
            "border_color": "#ff98004a",
            "hover_text_color": "white",
            "target": "#deleteModeBox",
            "swap": "innerHTML",
            "trigger": "confirmed",
            "hx_click": "hxConfirm(this,'Are you sure you want to delete the selected items?','When deleting the items, its dependent data will be set to NULL or reassigned.')",
        },
        {
            "name": "restore",
            "label": "Restore",
            "url": reverse_lazy("horilla_core:bulk_recycle_bin_restore"),
            "method": "post",
            "icon": "fa-undo",
            "bg_color": "#e8f5e9",
            "hover_bg_color": "#4caf50",
            "text_color": "#2e7d32",
            "border_color": "#a5d6a7",
            "hover_text_color": "white",
            "target": "#deleteModeBox",
            "swap": "innerHTML",
            "trigger": "confirmed",
            "hx_click": "hxConfirm(this,'Are you sure you want restore the selected items ?')",
        },
    ]

    additional_action_button = [
        {
            "name": "empty_recyclebin",
            "label": "Empty Recycle Bin",
            "url": reverse_lazy("horilla_core:recycle_bin_empty"),
            "method": "post",
            "icon": "fa-recycle",
            "bg_color": "#f44336",
            "text_color": "white",
            "border_color": "#ef9a9a",
            "target": "#deleteModeBox",
            "swap": "innerHTML",
            "trigger": "confirmed",
            "hx_click": "hxConfirm(this,'Are you sure you want empty this bin?')",
        },
    ]

    @cached_property
    def columns(self):
        instance = self.model()
        return [
            (_("Record Name"), "record_name"),
            (_("Type"), "get_model_display_name"),
            (_("Deleted By"), "deleted_by"),
            (_("Deleted At"), "deleted_at"),
        ]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_core.change_recyclebin"):
            actions.append(
                {
                    "action": "Restore",
                    "icon": "fa-solid fa-undo",
                    "icon_class": "fa-solid fa-undo w-4 h-4",
                    "attrs": """
                            hx-post="{get_restore_url}"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            hx-trigger='confirmed'
                            hx-on:click="hxConfirm(this,'Are you sure you want to restore this item?')"
                            """,
                },
            )
        if self.request.user.has_perm("horilla_core.delete_recyclebin"):
            actions.append(
                {
                    "action": "Delete",
                    "src": "assets/icons/a4.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                        hx-post="{get_delete_url}"
                        hx-target="#deleteModeBox"
                        hx-swap="innerHTML"
                        hx-trigger='confirmed'
                        hx-on:click="hxConfirm(this,'Are you sure you want to delete this item?',
                        'When deleting the item, its dependent data will be set to NULL or reassigned.')"
                    """,
                }
            )
        return actions


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.delete_recyclebin"), name="dispatch"
)
class RecycleDeleteView(LoginRequiredMixin, View):
    """
    View to handle deletion of a single RecycleBin record
    """

    def post(self, request, pk, *args, **kwargs):
        try:
            recycle_obj = get_object_or_404(RecycleBin, pk=pk)
        except:
            messages.error(request, _("The requested data does not exist."))
            return HttpResponse("<script>$('#reloadButton').click();</script>")
        deleted_count, failed_records = delete_recycle_bin_records(request, recycle_obj)

        if deleted_count > 0:
            messages.success(
                request, f"Record '{recycle_obj.record_name()}' deleted successfully!"
            )
        if failed_records:
            messages.error(request, f"Error deleting record: {failed_records[0]}")

        return HttpResponse(
            "<script>htmx.trigger('#reloadButton','click');</script>", status=200
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.delete_recyclebin"), name="dispatch"
)
class BulkDeleteRecycleBinView(LoginRequiredMixin, View):
    """
    View to handle bulk deletion of selected RecycleBin records
    """

    def post(self, request, *args, **kwargs):
        record_ids = json.loads(request.POST.get("selected_ids", "[]"))
        if not record_ids:
            messages.error(request, "No records selected for deletion.")
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse_lazy("horilla_core:recycle_bin_view")
            return response
        recycle_objs = RecycleBin.objects.filter(id__in=record_ids)
        deleted_count, failed_records = delete_recycle_bin_records(
            request, recycle_objs
        )
        if deleted_count > 0:
            messages.success(
                request,
                f"Successfully deleted {deleted_count} item(s) from the recycle bin.",
            )
        if failed_records:
            messages.warning(
                request,
                f"Failed to delete {len(failed_records)} item(s): {', '.join(failed_records)}",
            )
        response = HttpResponse(
            "<script>htmx.trigger('#reloadButton','click');$('#unselect-all-btn-RecycleBinlist').click();closeModal();</script>",
            status=200,
        )
        return response


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.change_recyclebin"), name="dispatch"
)
class RecycleRestoreView(LoginRequiredMixin, View):

    def post(self, request, pk, *args, **kwargs):
        try:
            recycle_obj = get_object_or_404(RecycleBin, pk=pk)
        except:
            messages.error(request, _("The requested data does not exist."))
            return HttpResponse("<script>$('#reloadButton').click();</script>")
        restored_count, failed_records = restore_recycle_bin_records(
            request, recycle_obj
        )

        if restored_count > 0:
            messages.success(
                request, f"Record '{recycle_obj.record_name()}' restored successfully!"
            )
        if failed_records:
            messages.error(request, f"Error restoring record: {failed_records[0]}")

        return HttpResponse(
            "<script>htmx.trigger('#reloadButton','click');</script>", status=200
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.change_recyclebin"), name="dispatch"
)
class BulkRestoreRecycleView(LoginRequiredMixin, View):
    """
    View to handle bulk restoration of selected RecycleBin records
    """

    def post(self, request, *args, **kwargs):
        record_ids = json.loads(request.POST.get("selected_ids", "[]"))
        if not record_ids:
            messages.error(request, "No records selected for restoration.")
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse_lazy("horilla_core:recycle_bin_view")
            return response
        recycle_objs = RecycleBin.objects.filter(id__in=record_ids)
        restored_count, failed_records = restore_recycle_bin_records(
            request, recycle_objs
        )
        if restored_count > 0:
            messages.success(
                request,
                f"Successfully restored {restored_count} item(s) from the recycle bin.",
            )
        if failed_records:
            messages.warning(
                request,
                f"Failed to restore {len(failed_records)} item(s): {', '.join(failed_records)}",
            )
        response = HttpResponse(
            "<script>htmx.trigger('#reloadButton','click');$('#unselect-all-btn-RecycleBinlist').click();closeModal();</script>",
            status=200,
        )
        return response


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.delete_recyclebin"), name="dispatch"
)
class EmptyRecycleBinView(LoginRequiredMixin, View):
    """
    View to handle emptying the entire RecycleBin model
    """

    def post(self, request, *args, **kwargs):
        deleted_count, _ = RecycleBin.objects.all().delete()

        messages.success(
            request,
            f"Successfully deleted {deleted_count} item(s) from the recycle bin.",
        )

        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse_lazy("horilla_core:recycle_bin_view")
        return response


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_core.view_recyclebinpolicy"), name="dispatch"
)
class BinPolicyView(LoginRequiredMixin, View):
    """
    TemplateView for recycle bin policy view.
    """

    template_name = "settings/recycle_bin/bin_policy.html"

    def get(self, request, *args, **kwargs):
        company = request.active_company
        policy = RecycleBinPolicy.objects.filter(company=company).first()
        context = {
            "days": policy.retention_days if policy else 30,
            "view_id": "bin-policy",
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        days = request.POST.get("days")
        company = request.active_company

        policy, created = RecycleBinPolicy.objects.get_or_create(
            company=company, defaults={"retention_days": days}
        )

        if not created:
            policy.retention_days = days
            policy.save()
            messages.success(request, _("Recycle bin policy updated successfully!"))
        return HttpResponse("")
