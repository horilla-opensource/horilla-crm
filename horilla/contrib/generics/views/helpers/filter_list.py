"""
Save and manage filter list views for horilla.contrib.generics.

View for saving and editing reusable filter list configurations.
"""

# Third-party imports (Django)
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.views import View

from horilla.contrib.core.models import PinnedView

# First party imports (Horilla)
from horilla.shortcuts import render
from horilla.utils.decorators import htmx_required, method_decorator
from horilla.utils.translation import gettext_lazy as _
from horilla.views.generic import FormView
from horilla.web import HttpResponse, RedirectResponse

# Local imports
from ...forms import SaveFilterListForm


@method_decorator(htmx_required, name="dispatch")
class SaveFilterListView(LoginRequiredMixin, FormView):
    """View for saving and editing filter configurations as reusable filter lists."""

    template_name = "save_filter_form.html"
    form_class = SaveFilterListForm

    def get_initial(self):
        """Populate initial data from request or from saved_list_id when editing."""
        initial = super().get_initial()
        saved_list_id = self.request.GET.get("saved_list_id") or self.request.POST.get(
            "saved_list_id"
        )
        is_get = self.request.method == "GET"
        if saved_list_id:
            try:
                saved_list = self.request.user.saved_filter_lists.get(id=saved_list_id)
                initial["saved_list_id"] = saved_list.id
                if is_get:
                    initial["list_name"] = saved_list.name
                    initial["model_name"] = saved_list.model_name
                    initial["main_url"] = self.request.GET.get("main_url", "")
                    initial["make_public"] = saved_list.is_public
            except (
                ValueError,
                self.request.user.saved_filter_lists.model.DoesNotExist,
            ):
                if saved_list_id:
                    try:
                        initial["saved_list_id"] = int(saved_list_id)
                    except (TypeError, ValueError):
                        pass
        if not initial.get("model_name"):
            initial["model_name"] = self.request.GET.get("model_name")
        if "main_url" not in initial or initial["main_url"] == "":
            initial["main_url"] = self.request.GET.get(
                "main_url", self.request.POST.get("main_url", "")
            )
        return initial

    def get_context_data(self, **kwargs):
        """Add query_params, is_edit, and main_url for the save filter form template."""
        context = super().get_context_data(**kwargs)
        saved_list_id = self.request.GET.get("saved_list_id") or self.request.POST.get(
            "saved_list_id"
        )
        create_new = self.request.GET.get("create_new") == "true"
        if saved_list_id:
            try:
                saved_list = self.request.user.saved_filter_lists.get(id=saved_list_id)
                context["query_params"] = saved_list.filter_params or {}
                context["is_edit"] = True
            except (
                ValueError,
                self.request.user.saved_filter_lists.model.DoesNotExist,
            ):
                context["query_params"] = {}
                context["is_edit"] = False
        else:
            context["query_params"] = {
                k: v
                for k, v in self.request.GET.lists()
                if k
                in [
                    "field",
                    "operator",
                    "value",
                    "start_value",
                    "end_value",
                    "logic",
                    "search",
                ]
            }
            context["is_edit"] = False
        context["create_new"] = create_new
        search_url = (
            self.request.GET.get("search_url")
            or self.request.POST.get("search_url")
            or ""
        )
        context["search_url"] = search_url

        # Build the URL to load filter rows into the modal (used with hx-trigger="load")
        if search_url and (create_new or context.get("is_edit")):
            query_params = context.get("query_params", {})
            if query_params.get("field"):
                params = urlencode(
                    [("render_filter_rows", "true"), ("row_id_offset", "10000")]
                    + [("field", v) for v in query_params.get("field", [])]
                    + [("operator", v) for v in query_params.get("operator", [])]
                    + [("value", v) for v in query_params.get("value", [])]
                    + [("start_value", v) for v in query_params.get("start_value", [])]
                    + [("end_value", v) for v in query_params.get("end_value", [])]
                    + [("logic", v) for v in query_params.get("logic", [])]
                )
            else:
                params = "add_filter_row=true&row_id=9999"
            context["filter_rows_url"] = f"{search_url}?{params}"
        else:
            context["filter_rows_url"] = ""

        context["main_url"] = (
            self.request.GET.get("main_url")
            or self.request.POST.get("main_url")
            or context.get("main_url", "")
        )
        return context

    def form_valid(self, form):
        """Save or update the filter list and redirect with view_type or show form errors."""
        list_name = form.cleaned_data["list_name"]
        model_name = form.cleaned_data["model_name"]
        make_public = form.cleaned_data.get("make_public", False)
        saved_list_id = form.cleaned_data.get("saved_list_id")
        filter_params = {
            k: v
            for k, v in self.request.POST.lists()
            if k in ["field", "operator", "value", "start_value", "end_value", "logic"]
        }
        search_in_post = self.request.POST.getlist("search")
        if search_in_post:
            filter_params["search"] = search_in_post
        elif self.request.GET.get("search"):
            filter_params["search"] = [self.request.GET.get("search")]

        if saved_list_id:
            try:
                saved_filter_list = self.request.user.saved_filter_lists.get(
                    id=saved_list_id
                )
                saved_filter_list.name = list_name
                saved_filter_list.filter_params = filter_params
                saved_filter_list.is_public = make_public
                saved_filter_list.save()
                main_url = form.cleaned_data["main_url"]
                view_type = f"saved_list_{saved_filter_list.id}"
                query_params = {
                    k: v
                    for k, v in self.request.GET.items()
                    if k not in ["view_type", "search"]
                }
                query_params["view_type"] = view_type
                redirect_url = f"{main_url}?{urlencode(query_params)}"
                return RedirectResponse(request=self.request, redirect_to=redirect_url)
            except (
                ValueError,
                self.request.user.saved_filter_lists.model.DoesNotExist,
            ):
                form.add_error(
                    None,
                    "Saved list not found or you don't have permission to edit it.",
                )
                return self.form_invalid(form)

        create_new = self.request.POST.get("create_new") == "true"
        if not create_new and not any(filter_params.values()):
            form.add_error(None, _("At least one filter is required."))
            return self.form_invalid(form)
        try:
            saved_filter_list, _created = (
                self.request.user.saved_filter_lists.update_or_create(
                    name=list_name,
                    model_name=model_name,
                    defaults={
                        "filter_params": filter_params,
                        "is_public": make_public,
                    },
                )
            )
            main_url = form.cleaned_data["main_url"]
            view_type = f"saved_list_{saved_filter_list.id}"
            query_params = {
                k: v
                for k, v in self.request.GET.items()
                if k not in ["view_type", "search"]
            }
            query_params["view_type"] = view_type

            redirect_url = f"{main_url}?{urlencode(query_params)}"
            return RedirectResponse(request=self.request, redirect_to=redirect_url)
        except IntegrityError:
            form.add_error(
                "list_name", "A list with this name already exists for this model."
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Re-render the save filter form with validation errors."""
        return self.render_to_response(self.get_context_data(form=form))


@method_decorator(htmx_required, name="dispatch")
class PinView(LoginRequiredMixin, View):
    """View for pinning and unpinning filter lists for quick access."""

    def post(self, request):
        """
        Toggle a pinned view for the current user.

        If `unpin` is provided, removes the pinned view; otherwise creates or
        updates the pinned view and returns the updated navbar HTML.
        """
        view_type = request.POST.get("view_type")
        model_name = request.POST.get("model_name")
        unpin = request.POST.get("unpin") or request.GET.get("unpin")

        if not view_type or not model_name:
            return HttpResponse(status=400)

        try:
            if unpin:
                PinnedView.all_objects.filter(
                    user=request.user, model_name=model_name
                ).delete()
                context = {
                    "request": request,
                    "model_name": model_name,
                    "view_type": view_type,
                    "all_view_types": True,
                }
                return render(request, "navbar.html", context)

            # else:
            PinnedView.all_objects.update_or_create(
                user=request.user,
                model_name=model_name,
                defaults={"view_type": view_type},
            )
            context = {
                "request": request,
                "model_name": model_name,
                "view_type": view_type,
                "pinned_view": {"view_type": view_type},
                "all_view_types": True,
            }
            return render(request, "navbar.html", context)
        except Exception:
            return HttpResponse(status=500)


@method_decorator(htmx_required, name="dispatch")
class DeleteSavedListView(LoginRequiredMixin, View):
    """View for deleting saved filter lists."""

    def post(self, request, *args, **kwargs):
        """
        Delete a user's saved filter list and update pinned views.

        Validates the provided `saved_list_id`, deletes it if permitted, and
        returns a redirect to `main_url` with an HTMX push header.
        """
        saved_list_id = request.POST.get("saved_list_id")
        main_url = request.POST.get("main_url")
        model_name = request.POST.get("model_name")  # Fallback to a default URL

        if not saved_list_id:
            messages.error(request, _("Invalid saved list ID."))
            response = RedirectResponse(request=request, redirect_to=main_url)
            response["HX-Push-Url"] = "true"  # Add HTMX header
            return response

        try:
            saved_list = request.user.saved_filter_lists.get(id=saved_list_id)
            saved_list_name = saved_list.name
            pinned_view = PinnedView.all_objects.filter(
                user=self.request.user,
                model_name=saved_list.model_name,
                view_type=f"saved_list_{saved_list_id}",
            ).first()
            if pinned_view:
                pinned_view.delete()

            saved_list.delete()
            messages.success(
                request, f"Saved list '{saved_list_name}' deleted successfully."
            )
        except Exception:
            messages.error(
                request,
                "Saved list not found or you don't have permission to delete it.",
            )

        query_params = request.GET.copy()
        pinned_view = PinnedView.all_objects.filter(
            user=self.request.user, model_name=model_name
        ).first()
        view_type = pinned_view.view_type if pinned_view else "all"
        query_params["view_type"] = view_type
        redirect_url = f"{main_url}?{urlencode(query_params)}"
        response = RedirectResponse(request=request, redirect_to=redirect_url)
        response["HX-Push-Url"] = "true"
        return response
