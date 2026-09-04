"""
Event create/update form view.
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

from ...forms import EventForm
from ...models import Activity
from .mixins import ActivityOwnerPermissionMixin


@method_decorator(htmx_required, name="dispatch")
class EventCreateForm(
    ActivityOwnerPermissionMixin, LoginRequiredMixin, HorillaSingleFormView
):
    """Form view for event activity."""

    model = Activity
    form_class = EventForm
    modal_height = False
    full_width_fields = ["notes"]
    save_and_new = False

    @cached_property
    def form_url(self):
        """Return the create or update URL depending on whether a pk is present."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("activity:event_update_form", kwargs={"pk": pk})
        return reverse_lazy("activity:event_create_form")

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
        """Set initial event form values including all-day toggle and related record."""
        initial = super().get_initial()
        if self.request.method == "POST":
            initial["is_all_day"] = self.request.POST.get("is_all_day") == "on"
        else:
            object_id = self.request.GET.get("object_id")
            model_name = self.request.GET.get("model_name")
            all_day = self.request.GET.get("is_all_day")
            toggle_is_all_day = self.request.GET.get("toggle_is_all_day")

            if toggle_is_all_day == "true" and self.kwargs.get("pk"):
                initial["is_all_day"] = False
            elif all_day is not None:
                initial["is_all_day"] = all_day == "on"
            elif hasattr(self, "object") and self.object:
                initial["is_all_day"] = self.object.is_all_day

            if object_id and model_name:
                initial["object_id"] = object_id
                content_type = HorillaContentType.objects.get(model=model_name.lower())
                initial["content_type"] = content_type.id
                initial["activity_type"] = "event"
                initial["owner"] = self.request.user

        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method == "POST":
            return kwargs
        initial = self.get_initial()
        get_data = self.request.GET.dict()
        for key, value in get_data.items():
            if value:
                initial[key] = value
        kwargs["initial"] = initial
        return kwargs

    def form_valid(self, form):
        super().form_valid(form)
        return ScriptResponse(extra="htmx.trigger('#EventTab','click');", close=True)
