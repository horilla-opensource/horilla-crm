"""
Forecast module for managing Forecast Types and Targets.

Includes views for listing, creating, updating, and deleting
forecast types and their associated conditions.
"""

from functools import cached_property

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator

from horilla_core.decorators import (
    htmx_required,
    permission_required,
    permission_required_or_denied,
)
from horilla_crm.forecast.filters import ForecastTypeFilter
from horilla_crm.forecast.forms import ForecastTypeForm
from horilla_crm.forecast.models import ForecastCondition, ForecastType
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla_utils.middlewares import _thread_local


class ForecastTypeView(LoginRequiredMixin, HorillaView):
    """Displays the forecast type settings page."""

    template_name = "forecast_type/forecast_type_view.html"
    nav_url = reverse_lazy("forecast:forecast_type_nav_view")
    list_url = reverse_lazy("forecast:forecast_type_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required("forecast.view_forecasttype"), name="dispatch")
class ForecastTypeNavbar(LoginRequiredMixin, HorillaNavView):
    """Navigation bar for ForecastType with optional 'New' button."""

    nav_title = ForecastType._meta.verbose_name_plural
    search_url = reverse_lazy("forecast:forecast_type_list_view")
    main_url = reverse_lazy("forecast:forecast_type_view")
    filterset_class = ForecastTypeFilter
    nav_width = False
    gap_enabled = False
    all_view_types = False
    recently_viewed_option = False
    filter_option = False
    one_view_only = True
    reload_option = False
    border_enabled = False

    @cached_property
    def new_button(self):
        """Return dictionary for the 'New' button if user has permission."""

        if self.request.user.has_perm("forecast.add_forecasttype"):
            return {
                "url": f"""{ reverse_lazy('forecast:forecast_type_create_form_view')}""",
                "attrs": {"id": "type-create"},
                "title": "New",
            }
        return None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("forecast.view_forecasttype"), name="dispatch"
)
class ForecastTypeListView(LoginRequiredMixin, HorillaListView):
    """Lists all ForecastType records with optional actions."""

    model = ForecastType
    view_id = "forecast-type-list"
    filterset_class = ForecastTypeFilter
    search_url = reverse_lazy("forecast:forecast_type_list_view")
    main_url = reverse_lazy("forecast:forecast_type_view")
    save_to_list_option = False
    bulk_select_option = False
    clear_session_button_enabled = False
    table_width = False
    enable_sorting = False
    table_height_as_class = "h-[500px]"

    @cached_property
    def columns(self):
        """Return table column definitions."""
        instance = self.model()
        return [
            (instance._meta.get_field("name").verbose_name, "name"),
            (
                instance._meta.get_field("forecast_type").verbose_name,
                "get_forecast_type_display",
            ),
            (instance._meta.get_field("is_active").verbose_name, "is_active"),
        ]

    @cached_property
    def actions(self):
        """Return list of permitted actions (Edit/Delete)."""
        actions = []
        if self.request.user.has_perm("forecast.change_forecasttype"):
            actions.append(
                {
                    "action": "Edit",
                    "src": "assets/icons/edit.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                            hx-get="{get_edit_url}"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            onclick="openModal()"
                            """,
                },
            )
        if self.request.user.has_perm("forecast.delete_forecasttype"):
            actions.append(
                {
                    "action": "Delete",
                    "src": "assets/icons/a4.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                        hx-get="{get_delete_url}"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal()"
                        """,
                },
            )

        return actions


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("forecast.add_forecasttype"), name="dispatch"
)
class ForecastTypeFormView(LoginRequiredMixin, HorillaSingleFormView):
    """Form view to create or update ForecastType records with conditions."""

    model = ForecastType
    form_class = ForecastTypeForm
    fields = ["name", "forecast_type", "description"]
    full_width_fields = ["description"]
    condition_fields = ["field", "operator", "value", "logical_operator"]
    condition_model = ForecastCondition
    condition_field_title = "Filter Opportunities"
    modal_height = False

    def get_form_kwargs(self):
        """Return keyword arguments for initializing the form."""
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        kwargs["condition_model"] = ForecastCondition

        model_name = (
            self.request.GET.get("model_name")
            or self.request.POST.get("model_name")
            or "opportunity"
        )
        if "initial" not in kwargs:
            kwargs["initial"] = {}
        kwargs["initial"]["model_name"] = model_name

        return kwargs

    @cached_property
    def form_url(self):
        """Return URL for form submission based on create or update."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy(
                "forecast:forecast_type_update_form_view", kwargs={"pk": pk}
            )
        return reverse_lazy("forecast:forecast_type_create_form_view")

    def get_existing_conditions(self):
        """Return existing forecast conditions for editing."""

        if self.kwargs.get("pk") and hasattr(self, "object") and self.object:
            return self.object.conditions.all().order_by("order", "created_at")
        return None

    def get(self, request, *args, **kwargs):
        """Handle GET request and setup session data."""
        if self.kwargs.get("pk"):
            # Clear session data first
            for key in self.session_keys_to_clear_on_edit:
                if key in request.session:
                    del request.session[key]
            request.session.modified = True

            # Get the object first
            self.object = get_object_or_404(self.model, pk=self.kwargs["pk"])

            # Set up condition row count based on existing conditions
            existing_conditions = self.get_existing_conditions()
            if existing_conditions is not None:
                condition_count = existing_conditions.count()
                request.session["condition_row_count"] = max(
                    condition_count - 1, 0
                )  # Subtract 1 because row 0 is always present
                request.session.modified = True

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Override to pass existing conditions to the template"""
        context = super().get_context_data(**kwargs)

        # Add existing conditions to context for template rendering
        if self.kwargs.get("pk") and hasattr(self, "object") and self.object:
            context["existing_conditions"] = self.get_existing_conditions()
            form = context.get("form")
            if form and hasattr(form, "condition_field_choices"):
                context["condition_field_choices"] = form.condition_field_choices

        return context

    def form_valid(self, form):
        """Override to handle multiple condition rows"""
        if not self.request.user.is_authenticated:
            messages.error(
                self.request, "You must be logged in to perform this action."
            )
            return self.form_invalid(form)

        # Check if using the new condition rows method
        condition_rows = form.cleaned_data.get("condition_rows", [])

        if condition_rows:
            # Use new method like ScoringCriterionCreateUpdateView
            try:
                with transaction.atomic():
                    # Save the main ForecastType
                    self.object = form.save(commit=False)

                    if self.kwargs.get("pk"):
                        self.object.updated_at = timezone.now()
                        self.object.updated_by = self.request.user
                    else:
                        self.object.created_at = timezone.now()
                        self.object.created_by = self.request.user
                        self.object.updated_at = timezone.now()
                        self.object.updated_by = self.request.user

                    self.object.company = (
                        getattr(_thread_local, "request", None).active_company
                        if hasattr(_thread_local, "request")
                        else self.request.user.company
                    )
                    self.object.save()

                    # Delete existing conditions and create new ones
                    if self.kwargs.get("pk"):
                        self.object.conditions.all().delete()

                    created_conditions = []
                    for row_data in condition_rows:
                        condition = ForecastCondition(
                            forecast_type=self.object,
                            field=row_data["field"],
                            operator=row_data["operator"],
                            value=row_data.get("value", ""),
                            logical_operator=row_data.get("logical_operator", "and"),
                            order=row_data.get("order", 0),
                            created_at=timezone.now(),
                            created_by=self.request.user,
                            updated_at=timezone.now(),
                            updated_by=self.request.user,
                            company=(
                                getattr(_thread_local, "request", None).active_company
                                if hasattr(_thread_local, "request")
                                else self.request.user.company
                            ),
                        )
                        condition.save()
                        created_conditions.append(condition)

                    self.request.session["condition_row_count"] = 0
                    self.request.session.modified = True
                    messages.success(
                        self.request,
                        f"Successfully {'updated' if self.kwargs.get('pk') else 'created'} forecast type with {len(created_conditions)} conditions!",
                    )

            except Exception as e:
                messages.error(self.request, f"Error saving forecast type: {str(e)}")
                return self.form_invalid(form)

        else:
            # Fallback to old method if condition_rows not available
            self.object = form.save(commit=False)
            if self.kwargs.get("pk"):
                self.object.updated_at = timezone.now()
                self.object.updated_by = self.request.user
            else:
                self.object.created_at = timezone.now()
                self.object.created_by = self.request.user
                self.object.updated_at = timezone.now()
                self.object.updated_by = self.request.user

            self.object.company = (
                getattr(_thread_local, "request", None).active_company
                if hasattr(_thread_local, "request")
                else self.request.user.company
            )
            self.object.save()
            form.save_m2m()

            # Now save the conditions using the old method
            self._save_conditions(self.object)

            self.request.session["condition_row_count"] = 0
            self.request.session.modified = True
            messages.success(
                self.request,
                f"{self.model._meta.verbose_name.title()} {'updated' if self.kwargs.get('pk') else 'created'} successfully!",
            )

        return HttpResponse("<script>$('#reloadButton').click();closeModal();</script>")

    def _get_condition_data_from_request(self):
        """Extract condition data from POST request."""
        condition_data = {}
        if self.request.method == "POST":
            post_data = self.request.POST

            for key, value in post_data.items():
                if value and "_" in key:
                    try:
                        # Split field name and row_id
                        parts = key.split("_")
                        if len(parts) >= 2:
                            field_name = "_".join(
                                parts[:-1]
                            )  # Everything except last part
                            row_id = parts[-1]  # Last part is row_id
                            if field_name in [
                                "field",
                                "operator",
                                "value",
                                "logical_operator",
                            ]:
                                if row_id not in condition_data:
                                    condition_data[row_id] = {}
                                condition_data[row_id][field_name] = value
                    except (ValueError, IndexError):
                        continue

            # Also handle row 0 fields (without row_id suffix)
            for field_name in ["field", "operator", "value", "logical_operator"]:
                if field_name in post_data and post_data[field_name]:
                    if "0" not in condition_data:
                        condition_data["0"] = {}
                    condition_data["0"][field_name] = post_data[field_name]

        return condition_data

    def _save_conditions(self, forecast_type):
        """Save condition data from form submission (fallback method)"""
        condition_data = self._get_condition_data_from_request()

        forecast_type.conditions.all().delete()

        order = 0
        for row_id in sorted(
            condition_data.keys(), key=lambda x: int(x) if x.isdigit() else 0
        ):
            data = condition_data[row_id]
            if data.get("field") and data.get("operator"):
                ForecastCondition.objects.create(
                    forecast_type=forecast_type,
                    field=data["field"],
                    operator=data["operator"],
                    value=data.get("value", ""),
                    logical_operator=data.get("logical_operator", "and"),
                    order=order,
                    company=(
                        getattr(_thread_local, "request", None).active_company
                        if hasattr(_thread_local, "request")
                        else self.request.user.company
                    ),
                )
                order += 1


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("forecast.delete_forecasttype"), name="dispatch"
)
class ForecastTypeDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """Delete view for forecast types."""

    model = ForecastType

    def get_post_delete_response(self):
        return HttpResponse("<script>htmx.trigger('#reloadButton','click');</script>")
