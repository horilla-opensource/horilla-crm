"""
Views for managing notes and attachments in Horilla, including listing, detail view, creation, and deletion of attachments.
These views handle permissions, rendering, and interactions for attachments related to various models in Horilla.
"""

# Standard library imports
import logging

# Third-party imports (Django)
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from horilla.contrib.core.models import HorillaAttachment, HorillaContentType
from horilla.contrib.core.utils import get_allowed_user_ids
from horilla.shortcuts import get_object_or_404, render

# First party imports (Horilla)
from horilla.urls import reverse_lazy
from horilla.utils.decorators import htmx_required, method_decorator
from horilla.utils.translation import gettext_lazy as _
from horilla.views.generic import DetailView, FormView
from horilla.web import Http404, HttpResponse, HxTriggerResponse, ScriptResponse

from ..forms import HorillaAttachmentForm
from .delete import HorillaSingleDeleteView
from .details import (
    HorillaModalDetailView,
    check_record_access,
    check_record_change_access,
    check_record_delete_access,
)

# Local imports
from .list import HorillaListView

logger = logging.getLogger(__name__)


class AttachmentListView(HorillaListView):
    """List view for displaying horilla attachments."""

    model = HorillaAttachment
    columns = ["title", "created_by", "created_at"]
    bulk_select_option = False
    list_column_visibility = False
    no_record_fit_height = False
    table_auto = True


@method_decorator(htmx_required, name="dispatch")
class HorillaNotesAttachementSectionView(DetailView):
    """View for displaying notes and attachments section in detail views."""

    template_name = "notes_attachments.html"
    context_object_name = "obj"

    def get_actions(
        self,
        can_change_parent=False,
        can_delete_parent=False,
        has_global_change=False,
        has_global_delete=False,
    ):
        """
        Return actions for attachments based on parent record permissions.
        - Edit shown when user can change parent; hidden_if restricts to own/subordinate rows for Change Own users.
        - Delete shown when user can delete parent; same hidden_if restriction for Delete Own users.
        """
        actions = [
            {
                "action": "View",
                "src": "assets/icons/eye1.svg",
                "img_class": "w-4 h-4",
                "attrs": """
                            hx-get="{get_detail_view_url}"
                            hx-target="#contentModalBox"
                            hx-swap="innerHTML"
                            onclick="openContentModal()"
                            """,
            },
        ]

        if can_change_parent or can_delete_parent:
            allowed_ids = get_allowed_user_ids(self.request.user)

            def _hidden_if_not_allowed(attachment):
                created_by = getattr(attachment, "created_by", None)
                if not created_by:
                    return False
                return created_by.pk not in allowed_ids

        if can_change_parent:
            actions.append(
                {
                    "action": "Edit",
                    "src": "assets/icons/edit.svg",
                    "img_class": "w-4 h-4",
                    **(
                        {"hidden_if": _hidden_if_not_allowed}
                        if not has_global_change
                        else {}
                    ),
                    "attrs": """
                            hx-get="{get_edit_url}"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            hx-on:click="openModal();"
                            """,
                }
            )

        if can_delete_parent:
            actions.append(
                {
                    "action": "Delete",
                    "src": "assets/icons/a4.svg",
                    "img_class": "w-4 h-4",
                    **(
                        {"hidden_if": _hidden_if_not_allowed}
                        if not has_global_delete
                        else {}
                    ),
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

    def check_attachment_add_permission(self):
        """
        Check if user has permission to add attachments to the related object.

        Allowed when the user can change the parent record (change or change_own+owner).
        """
        return check_record_change_access(self.request.user, self.get_object())

    def get(self, request, *args, **kwargs):
        """Load attachment list for the detail object and render with add-permission flag."""
        self.object = self.get_object()
        if not check_record_access(request.user, self.object):
            return render(request, "403.html", status=403)
        object_id = self.kwargs.get("pk")

        try:
            content_type = HorillaContentType.objects.get_for_model(model=self.model)
        except HorillaContentType.DoesNotExist:
            from horilla.web import HttpResponseNotFound

            return HttpResponseNotFound("Model not found")

        queryset = HorillaAttachment.objects.filter(
            content_type=content_type, object_id=object_id
        )

        # Store instance_ids in session for navigation
        ordered_ids_key = "ordered_ids_horillaattachment"
        ordered_ids = list(queryset.values_list("pk", flat=True))
        self.request.session[ordered_ids_key] = ordered_ids

        list_view = AttachmentListView()
        list_view.request = self.request
        list_view.queryset = queryset
        list_view.object_list = queryset
        list_view.view_id = f"attachments_{content_type.model}_{object_id}"
        list_view.main_session_id = list_view.view_id
        user = request.user
        app = self.object._meta.app_label
        model_name = self.object._meta.model_name
        has_global_change = user.is_superuser or user.has_perm(
            f"{app}.change_{model_name}"
        )
        has_global_delete = user.is_superuser or user.has_perm(
            f"{app}.delete_{model_name}"
        )
        can_change_parent = has_global_change or check_record_change_access(
            user, self.object
        )
        can_delete_parent = has_global_delete or check_record_delete_access(
            user, self.object
        )
        list_view.actions = self.get_actions(
            can_change_parent=can_change_parent,
            can_delete_parent=can_delete_parent,
            has_global_change=has_global_change,
            has_global_delete=has_global_delete,
        )
        sorted_queryset = list_view.get_queryset()
        list_view.object_list = sorted_queryset
        context = list_view.get_context_data()
        context.update(super().get_context_data())
        context["can_add_attachment"] = can_change_parent
        return render(request, self.template_name, context)


@method_decorator(htmx_required, name="dispatch")
class HorillaNotesAttachementDetailView(HorillaModalDetailView):
    """Detail view for displaying individual notes and attachments."""

    template_name = "notes_attachments_detail.html"
    model = HorillaAttachment
    title = _("Notes and Attachment")

    def get(self, request, *args, **kwargs):
        """Load attachment detail or return error script if not found."""
        try:
            self.object = self.get_object()
        except Http404:
            self.object = None

        if not self.object:
            messages.error(self.request, _("The requested attachment does not exist."))
            return ScriptResponse(reload=True, msgs=True, extra="closeContentModal();")

        related_obj = self.object.related_object
        if related_obj and not check_record_access(request.user, related_obj):
            return render(request, "403.html", status=403)

        user = request.user
        can_change = can_delete = False
        if related_obj:
            app = related_obj._meta.app_label
            model_name = related_obj._meta.model_name
            has_global_change = user.is_superuser or user.has_perm(
                f"{app}.change_{model_name}"
            )
            has_global_delete = user.is_superuser or user.has_perm(
                f"{app}.delete_{model_name}"
            )
            allowed_ids = get_allowed_user_ids(user)
            created_by = getattr(self.object, "created_by", None)
            note_owner_allowed = not created_by or created_by.pk in allowed_ids
            can_change = has_global_change or (
                check_record_change_access(user, related_obj) and note_owner_allowed
            )
            can_delete = has_global_delete or (
                check_record_delete_access(user, related_obj) and note_owner_allowed
            )

        context = self.get_context_data()
        context["can_change_attachment"] = can_change
        context["can_delete_attachment"] = can_delete
        return self.render_to_response(context)


@method_decorator(htmx_required, name="dispatch")
class HorillaNotesAttachmentCreateView(LoginRequiredMixin, FormView):
    """View for creating new notes and attachments."""

    template_name = "forms/notes_attachment_form.html"
    form_class = HorillaAttachmentForm
    model = HorillaAttachment

    def get_context_data(self, **kwargs):
        """Set form_url for create or edit based on pk."""
        context = super().get_context_data(**kwargs)
        context["form_url"] = reverse_lazy("generics:notes_attachment_create")
        pk = self.kwargs.get("pk")
        if pk:
            context["form_url"] = reverse_lazy(
                "generics:notes_attachment_edit", kwargs={"pk": pk}
            )
        return context

    def get_object(self):
        """Return object if pk exists (for edit mode)."""
        pk = self.kwargs.get("pk")
        if pk:
            obj = get_object_or_404(HorillaAttachment, pk=pk)
            return obj
        return None

    def get_form(self, form_class=None):
        """Bind instance if editing."""
        form_class = self.get_form_class()
        obj = self.get_object()
        return form_class(instance=obj, **self.get_form_kwargs())

    def check_related_object_permission(self, related_object, permission_type="add"):
        """
        Allow add/change when user has change access on the parent record.
        For Change Own users editing a note, also verify the note's created_by
        is in the user's allowed set (own or subordinate).
        """
        user = self.request.user
        app = related_object._meta.app_label
        model = related_object._meta.model_name
        has_global_change = user.is_superuser or user.has_perm(f"{app}.change_{model}")
        if not (has_global_change or check_record_change_access(user, related_object)):
            return False
        if permission_type == "change" and not has_global_change:
            pk = self.kwargs.get("pk")
            if pk:
                try:
                    attachment = self.model.objects.get(pk=pk)
                    created_by = getattr(attachment, "created_by", None)
                    if created_by and created_by.pk not in get_allowed_user_ids(user):
                        return False
                except self.model.DoesNotExist:
                    pass
        return True

    def dispatch(self, request, *args, **kwargs):
        """Check permissions before processing the request."""
        # For edit mode, check if attachment exists and user has permission
        pk = kwargs.get("pk")
        if pk:
            try:
                attachment = self.model.objects.get(pk=pk)
                related_object = attachment.related_object

                if related_object:
                    if not self.check_related_object_permission(
                        related_object, "change"
                    ):
                        messages.error(
                            request,
                            _("You don't have permission to edit this attachment."),
                        )
                        return ScriptResponse(reload=True, msgs=True, close=True)
            except self.model.DoesNotExist:
                messages.error(request, _("The requested attachment does not exist."))
                return ScriptResponse(reload=True, msgs=True, close=True)

        # For create mode, check permission on the related object
        else:
            model_name = request.GET.get("model_name")
            object_id = request.GET.get("object_id")

            if model_name and object_id:
                try:
                    content_type = HorillaContentType.objects.get(
                        model=model_name.lower()
                    )
                    related_model = content_type.model_class()
                    related_object = related_model.objects.get(pk=object_id)

                    if not self.check_related_object_permission(related_object, "add"):
                        messages.error(
                            request,
                            _(
                                "You don't have permission to add attachments to this record."
                            ),
                        )
                        return ScriptResponse(reload=True, msgs=True, close=True)
                except (
                    HorillaContentType.DoesNotExist,
                    related_model.DoesNotExist,
                    ValueError,
                ):
                    messages.error(request, _("Invalid related object."))
                    return ScriptResponse(reload=True, msgs=True, close=True)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Save attachment (create or update) and return close-modal/reload script."""
        model_name = self.request.GET.get("model_name")
        pk = self.kwargs.get("pk")

        attachment = form.save(commit=False)
        if not pk:
            content_type = HorillaContentType.objects.get(model=model_name.lower())
            attachment.created_by = self.request.user
            attachment.object_id = self.request.GET.get("object_id")
            attachment.content_type = content_type
            attachment.company = self.request.active_company
            messages.success(self.request, f"{attachment.title} created successfully")
        else:
            messages.success(self.request, f"{attachment.title} updated successfully")
        attachment.save()
        return HttpResponse(
            "<script>$('#tab-notes-attachments').click();closeModal();$('#detailReloadButton').click();</script>"
        )

    def get(self, request, *args, **kwargs):
        """Validate attachment pk when editing; then delegate to parent get."""
        pk = kwargs.get("pk")
        if pk:
            try:
                self.model.objects.get(pk=pk)
            except self.model.DoesNotExist:
                messages.error(request, _("The requested attachment does not exist."))
                return ScriptResponse(reload=True, msgs=True, close=True)

        return super().get(request, *args, **kwargs)


@method_decorator(htmx_required, name="dispatch")
class HorillaNotesAttachmentDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """View for deleting notes and attachments."""

    model = HorillaAttachment
    check_delete_permission = False

    def dispatch(self, request, *args, **kwargs):
        """Allow delete only when user has change access on the parent record."""
        try:
            attachment = self.model.objects.get(pk=kwargs.get("pk"))
        except self.model.DoesNotExist:
            messages.error(request, _("The requested attachment does not exist."))
            return ScriptResponse(reload=True, msgs=True, close=True)

        user = request.user
        related_object = attachment.related_object
        if user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if related_object:
            app = related_object._meta.app_label
            model = related_object._meta.model_name
            has_global_change = user.has_perm(f"{app}.change_{model}")
            if has_global_change or check_record_change_access(user, related_object):
                if has_global_change:
                    return super().dispatch(request, *args, **kwargs)
                created_by = getattr(attachment, "created_by", None)
                if not created_by or created_by.pk in get_allowed_user_ids(user):
                    return super().dispatch(request, *args, **kwargs)

        messages.error(
            request, _("You don't have permission to delete this attachment.")
        )
        return ScriptResponse(reload=True, msgs=True, close=True)

    def get_post_delete_response(self):
        return HxTriggerResponse(extra="closeContentModal();")
