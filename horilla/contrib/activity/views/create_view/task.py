"""
Task create/update form view.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin

from horilla.contrib.core.models import HorillaContentType
from horilla.contrib.generics.views import HorillaSingleFormView
from horilla.shortcuts import get_object_or_404
from horilla.urls import reverse_lazy
from horilla.utils.decorators import htmx_required, method_decorator
from horilla.utils.functional import cached_property  # type: ignore
from horilla.web import Http404, ScriptResponse

from ...models import Activity
from .mixins import ActivityOwnerPermissionMixin


@method_decorator(htmx_required, name="dispatch")
class TaskCreateForm(
    ActivityOwnerPermissionMixin, LoginRequiredMixin, HorillaSingleFormView
):
    """Form view for task activity."""

    model = Activity
    full_width_fields = ["description"]
    modal_height = False
    hidden_fields = ["object_id", "content_type", "activity_type"]
    save_and_new = False
    fields = [
        "object_id",
        "content_type",
        "title",
        "subject",
        "owner",
        "task_priority",
        "assigned_to",
        "due_datetime",
        "status",
        "description",
        "activity_type",
    ]

    @cached_property
    def form_url(self):
        """Return the create or update URL depending on whether a pk is present."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("activity:task_update_form", kwargs={"pk": pk})
        return reverse_lazy("activity:task_create_form")

    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        object_id = request.GET.get("object_id")
        model_name = request.GET.get("model_name")
        app_label = request.GET.get("app_label")

        if pk:
            try:
                activity = get_object_or_404(Activity, pk=pk)
            except Http404:
                messages.error(
                    request,
                    f"{self.model._meta.verbose_name} not found or no longer exists.",
                )
                return ScriptResponse(
                    reload=True,
                    close=True,
                )
            object_id = object_id or activity.object_id
            model_name = model_name or activity.content_type.model
            app_label = app_label or activity.content_type.app_label

        denied = self._check_owner_permission(
            request, object_id, model_name, app_label, pk
        )
        if denied is not None:
            return denied
        return super().get(request, *args, **kwargs)

    def get_initial(self):
        """Set initial task form values including related record, owner, and activity type."""
        initial = super().get_initial()
        object_id = self.request.GET.get("object_id")
        model_name = self.request.GET.get("model_name")
        if object_id and model_name:
            initial["object_id"] = object_id
            content_type = HorillaContentType.objects.get(model=model_name.lower())
            initial["content_type"] = content_type.id
            initial["owner"] = self.request.user
            initial["activity_type"] = "task"
        return initial

    def form_valid(self, form):
        super().form_valid(form)
        return ScriptResponse(extra="htmx.trigger('#TaskTab','click');", close=True)
