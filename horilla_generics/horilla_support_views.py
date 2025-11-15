import importlib
import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode, urlparse

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import IntegrityError, models
from django.db.models import CharField, Q, TextField
from django.db.models.fields import Field
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
    QueryDict,
)
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.views import View
from django.views.generic import FormView

from horilla import settings
from horilla.exceptions import HorillaHttp404
from horilla_core.decorators import htmx_required
from horilla_core.models import KanbanGroupBy, ListColumnVisibility, PinnedView
from horilla_generics.views import HorillaKanbanView

from .forms import ColumnSelectionForm, KanbanGroupByForm, SaveFilterListForm

logger = logging.getLogger(__name__)


@method_decorator(htmx_required, name="dispatch")
class HorillaKanbanGroupByView(FormView):

    template_name = "kanban_settings_form.html"
    form_class = KanbanGroupByForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        model_name = self.request.GET.get("model")
        app_label = self.request.GET.get("app_label")

        exclude_fields = self.request.POST.get(
            "exclude_fields"
        ) or self.request.GET.get("exclude_fields", None)

        if exclude_fields:
            exclude_fields = [f.strip() for f in exclude_fields.split(",") if f.strip()]
            exclude_fields = exclude_fields if exclude_fields else None
        else:
            exclude_fields = None

        include_fields = self.request.POST.get(
            "include_fields"
        ) or self.request.GET.get("include_fields", None)
        if include_fields:
            include_fields = [f.strip() for f in include_fields.split(",") if f.strip()]
            include_fields = include_fields if include_fields else None
        else:
            include_fields = None

        if model_name and app_label:
            kwargs["instance"] = KanbanGroupBy(
                model_name=model_name, app_label=app_label, user=self.request.user
            )
        kwargs["exclude_fields"] = exclude_fields
        kwargs["include_fields"] = include_fields
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user  # set the user server-side
        form.save()
        return HttpResponse("<script>closeModal();$('#kanbanBtn').click();</script>")


@method_decorator(htmx_required, name="dispatch")
class ListColumnSelectFormView(LoginRequiredMixin, FormView):
    template_name = "add_column_to_list.html"
    form_class = ColumnSelectionForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        app_label = self.request.POST.get(
            "app_label", self.request.GET.get("app_label")
        )
        model_name = self.request.POST.get(
            "model_name", self.request.GET.get("model_name")
        )
        url_name = self.request.POST.get("url_name", self.request.GET.get("url_name"))
        model_name = model_name.strip('"') if model_name else model_name
        if model_name and "." in model_name:
            model_name = model_name.split(".")[-1]

        path_context = (
            urlparse(self.request.META.get("HTTP_REFERER", ""))
            .path.strip("/")
            .replace("/", "_")
        )
        path_context = re.sub(r"_\d+$", "", path_context)
        user = self.request.user

        if app_label and model_name and url_name:
            try:
                model = apps.get_model(app_label=app_label, model_name=model_name)
                kwargs["model"] = model
                kwargs["app_label"] = app_label
                kwargs["path_context"] = path_context
                kwargs["user"] = user
                kwargs["model_name"] = model_name
                kwargs["url_name"] = url_name
            except LookupError:
                self.form_error = "Invalid model specified."
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app_label = self.request.GET.get(
            "app_label", self.request.POST.get("app_label")
        )
        model_name = self.request.GET.get(
            "model_name", self.request.POST.get("model_name")
        )
        url_name = self.request.GET.get("url_name", self.request.POST.get("url_name"))

        model_name = model_name.strip('"') if model_name else model_name
        if model_name and "." in model_name:
            model_name = model_name.split(".")[-1]
        path_context = (
            urlparse(self.request.META.get("HTTP_REFERER", ""))
            .path.strip("/")
            .replace("/", "_")
        )
        path_context = re.sub(r"_\d+$", "", path_context)
        context["app_label"] = app_label
        context["model_name"] = model_name
        context["url_name"] = url_name

        visible_fields = []
        all_fields = []
        visibility = None
        if app_label and model_name:
            try:
                model = apps.get_model(app_label=app_label, model_name=model_name)
                instance = model()
                model_fields = [
                    [
                        force_str(f.verbose_name or f.name.title()),
                        (
                            f.name
                            if not getattr(f, "choices", None)
                            else f"get_{f.name}_display"
                        ),
                    ]
                    for f in model._meta.get_fields()
                    if isinstance(f, Field) and f.name not in ["history"]
                ]
                all_fields = (
                    getattr(instance, "columns", model_fields)
                    if hasattr(instance, "columns")
                    else model_fields
                )

                session_key = (
                    f"visible_fields_{app_label}_{model_name}_{path_context}_{url_name}"
                )
                visibility = ListColumnVisibility.all_objects.filter(
                    user=self.request.user,
                    app_label=app_label,
                    model_name=model_name,
                    context=path_context,
                    url_name=url_name,
                ).first()
                if visibility:
                    visible_fields = visibility.visible_fields

                self.request.session[session_key] = [f[1] for f in visible_fields]
                self.request.session.modified = True
            except LookupError:
                context["error"] = "Invalid model specified."

        context["visible_fields"] = visible_fields
        removed_custom_field_lists = (
            visibility.removed_custom_fields if visibility else []
        )
        visible_field_names = [f[1] for f in visible_fields]

        related_field_parents = set()
        for _, field_name in visible_fields + removed_custom_field_lists:
            if "__" in field_name:
                parent_field = field_name.split("__")[0]
                related_field_parents.add(parent_field)
        exclude_fields = self.request.GET.get("exclude")
        exclude_fields_list = exclude_fields.split(",") if exclude_fields else []
        context["exclude_fields"] = exclude_fields
        sensitive_fields = ["id", "password"]

        context["available_fields"] = [
            [verbose_name, field_name]
            for verbose_name, field_name in all_fields + removed_custom_field_lists
            if field_name not in visible_field_names
            and field_name not in related_field_parents
            and field_name not in exclude_fields_list
            and field_name not in sensitive_fields
        ]

        if hasattr(self, "form_error"):
            context["error"] = self.form_error
        return context

    def form_valid(self, form):
        with translation.override("en"):
            app_label = self.request.POST.get("app_label")
            model_name = self.request.POST.get("model_name")
            url_name = self.request.POST.get("url_name")
            if model_name and "." in model_name:
                model_name = model_name.split(".")[-1]
            field_names = self.request.POST.getlist("visible_fields")

            if not app_label or not model_name:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Missing app_label or model_name",
                        "htmx": '<div id="error-message">Missing app_label or model_name</div>',
                    }
                )

            path_context = (
                urlparse(self.request.META.get("HTTP_REFERER", ""))
                .path.strip("/")
                .replace("/", "_")
            )
            path_context = re.sub(r"_\d+$", "", path_context)
            try:
                model = apps.get_model(app_label=app_label, model_name=model_name)
                instance = model()
                model_fields = [
                    [
                        force_str(f.verbose_name or f.name.title()),
                        (
                            f.name
                            if not getattr(f, "choices", None)
                            else f"get_{f.name}_display"
                        ),
                    ]
                    for f in model._meta.get_fields()
                    if isinstance(f, Field) and f.name not in ["history"]
                ]
                all_fields = (
                    getattr(instance, "columns", model_fields)
                    if hasattr(instance, "columns")
                    else model_fields
                )
                all_field_names = {item[1] for item in all_fields}
                visibility = ListColumnVisibility.all_objects.filter(
                    user=self.request.user,
                    app_label=app_label,
                    model_name=model_name,
                    context=path_context,
                    url_name=url_name,
                ).first()
                custom_fields = []
                if visibility:
                    for display_name, field_name in visibility.visible_fields:
                        if (
                            field_name not in all_field_names
                            and field_name not in model_fields
                        ):
                            custom_fields.append([display_name, field_name])
                all_fields = all_fields + custom_fields
                verbose_name_map = {f[1]: f[0] for f in all_fields}

                # Include removed custom fields in the verbose name map to preserve original display names
                removed_custom_field_lists = (
                    visibility.removed_custom_fields if visibility else []
                )
                for display_name, field_name in removed_custom_field_lists:
                    verbose_name_map[field_name] = display_name

                model_field_names = {
                    f.name for f in model._meta.get_fields() if isinstance(f, Field)
                }

                visible_fields = [
                    [force_str(verbose_name_map.get(f, f.replace("_", " ").title())), f]
                    for f in field_names
                ]

                previous_visible_fields = (
                    visibility.visible_fields if visibility else []
                )
                previous_non_model_fields = [
                    f[1]
                    for f in previous_visible_fields
                    if f[1] not in model_field_names and not f[1].startswith("get_")
                ]
                removed_non_model_fields = [
                    [force_str(verbose_name_map.get(f, f.replace("_", " ").title())), f]
                    for f in previous_non_model_fields
                    if f not in field_names
                ]

                existing_removed = (
                    visibility.removed_custom_fields if visibility else []
                )
                # Only add to removed_custom_fields if not already there
                for removed_field in removed_non_model_fields:
                    if not any(
                        existing[1] == removed_field[1] for existing in existing_removed
                    ):
                        existing_removed.append(removed_field)

                # Remove fields from removed_custom_fields if they're being added back
                updated_removed_custom_fields = [
                    field for field in existing_removed if field[1] not in field_names
                ]

                session_key = (
                    f"visible_fields_{app_label}_{model_name}_{path_context}_{url_name}"
                )
                self.request.session[session_key] = field_names
                self.request.session.modified = True

                ListColumnVisibility.all_objects.filter(
                    user=self.request.user,
                    app_label=app_label,
                    model_name=model_name,
                    context=path_context,
                    url_name=url_name,
                ).delete()
                ListColumnVisibility.all_objects.create(
                    user=self.request.user,
                    app_label=app_label,
                    model_name=model_name,
                    visible_fields=visible_fields,
                    removed_custom_fields=updated_removed_custom_fields,
                    context=path_context,
                    url_name=url_name,
                )

                cache_key = f"visible_columns_{self.request.user.id}_{app_label}_{model_name}_{path_context}_{url_name}"
                cache.delete(cache_key)

                return HttpResponse(
                    "<script>$('#reloadButton').click();closeModal();</script>"
                )
            except LookupError:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Invalid model",
                        "htmx": '<div id="error-message">Invalid model</div>',
                    }
                )

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        context["error"] = "Form submission failed. Please review the selected fields."
        return self.render_to_response(context)


@method_decorator(htmx_required, name="dispatch")
class MoveFieldView(LoginRequiredMixin, View):
    template_name = "add_column_to_list.html"

    def post(self, request, *args, **kwargs):
        app_label = request.GET.get("app_label")
        model_name = request.GET.get("model_name")
        url_name = request.GET.get("url_name")
        field = request.GET.get("field")
        action = request.GET.get("action")
        path_context = (
            urlparse(request.META.get("HTTP_REFERER", ""))
            .path.strip("/")
            .replace("/", "_")
        )
        path_context = re.sub(r"_\d+$", "", path_context)
        user = request.user

        try:
            model = apps.get_model(app_label=app_label, model_name=model_name)
            instance = model()
            model_fields = [
                [
                    force_str(f.verbose_name or f.name.title()),
                    (
                        f.name
                        if not getattr(f, "choices", None)
                        else f"get_{f.name}_display"
                    ),
                ]
                for f in model._meta.get_fields()
                if isinstance(f, Field) and f.name not in ["history"]
            ]
            all_fields = (
                getattr(instance, "columns", model_fields)
                if hasattr(instance, "columns")
                else model_fields
            )
            all_field_names = {item[1] for item in all_fields}
            visibility = ListColumnVisibility.all_objects.filter(
                user=user,
                app_label=app_label,
                model_name=model_name,
                context=path_context,
                url_name=url_name,
            ).first()
            custom_fields = []
            if visibility:
                for display_name, field_name in visibility.visible_fields:
                    if (
                        field_name not in all_field_names
                        and field_name not in model_fields
                    ):
                        custom_fields.append([display_name, field_name])
            all_fields = all_fields + custom_fields
            session_key = (
                f"visible_fields_{app_label}_{model_name}_{path_context}_{url_name}"
            )
            visible_field_names = request.session.get(session_key, [])

            verbose_name_map = {f[1]: f[0] for f in all_fields}
            model_field_names = {
                f.name for f in model._meta.get_fields() if isinstance(f, Field)
            }

            removed_custom_field_lists = (
                visibility.removed_custom_fields if visibility else []
            )

            # Store original display name before modifying removed_custom_field_lists
            field_display_name = None
            if action == "add":
                # Find the display name in removed_custom_field_lists before removing it
                for removed_field in removed_custom_field_lists:
                    if removed_field[1] == field:
                        field_display_name = removed_field[0]
                        break

            if action == "add" and field not in visible_field_names:
                visible_field_names.append(field)
                # Remove from removed_custom_fields if present
                removed_custom_field_lists = [
                    f for f in removed_custom_field_lists if f[1] != field
                ]
            elif action == "remove" and field in visible_field_names:
                visible_field_names.remove(field)
                if (
                    field not in model_field_names
                    and not field.startswith("get_")
                    and not any(f[1] == field for f in removed_custom_field_lists)
                ):
                    removed_custom_field_lists.append(
                        [
                            force_str(
                                verbose_name_map.get(
                                    field, field.replace("_", " ").title()
                                )
                            ),
                            field,
                        ]
                    )
            elif action == "move_up" and field in visible_field_names:
                index = visible_field_names.index(field)
                if index > 0:
                    visible_field_names[index], visible_field_names[index - 1] = (
                        visible_field_names[index - 1],
                        visible_field_names[index],
                    )
            elif action == "move_down" and field in visible_field_names:
                index = visible_field_names.index(field)
                if index < len(visible_field_names) - 1:
                    visible_field_names[index], visible_field_names[index + 1] = (
                        visible_field_names[index + 1],
                        visible_field_names[index],
                    )

            request.session[session_key] = visible_field_names
            request.session.modified = True

            # Create an enhanced verbose_name_map that includes the stored display name
            enhanced_verbose_name_map = verbose_name_map.copy()
            if field_display_name and action == "add":
                enhanced_verbose_name_map[field] = field_display_name

            visible_fields = [
                [enhanced_verbose_name_map.get(f, f.replace("_", " ").title()), f]
                for f in visible_field_names
            ]

            form_data = QueryDict(mutable=True)
            form_data.setlist("visible_fields", visible_field_names)

            form = ColumnSelectionForm(
                model=model,
                app_label=app_label,
                model_name=model_name,
                path_context=path_context,
                user=user,
                data=form_data,
                url_name=url_name,
            )

            related_field_parents = set()
            for _, field_name in visible_fields + removed_custom_field_lists:
                if "__" in field_name:
                    parent_field = field_name.split("__")[0]
                    related_field_parents.add(parent_field)
            exclude_fields = request.GET.get("exclude")
            exclude_fields_list = exclude_fields.split(",") if exclude_fields else []
            if not form.is_valid():
                context = {
                    "form": form,
                    "app_label": app_label,
                    "model_name": model_name,
                    "visible_fields": visible_fields,
                    "url_name": url_name,
                    "exclude_fields": exclude_fields,
                    "available_fields": [
                        [verbose_name, field_name]
                        for verbose_name, field_name in {
                            f[1]: f for f in all_fields + removed_custom_field_lists
                        }.values()
                        if field_name not in visible_field_names
                        and field_name not in related_field_parents
                        and field_name not in exclude_fields_list
                    ],
                    "error": "Invalid field selection. Please try again.",
                }
                return render(request, self.template_name, context)

            context = {
                "form": form,
                "app_label": app_label,
                "model_name": model_name,
                "visible_fields": visible_fields,
                "exclude_fields": exclude_fields,
                "url_name": url_name,
                "available_fields": [
                    [verbose_name, field_name]
                    for verbose_name, field_name in {
                        f[1]: f for f in all_fields + removed_custom_field_lists
                    }.values()  # Deduplicate based on field_name
                    if field_name not in visible_field_names
                    and field_name not in related_field_parents
                    and field_name not in exclude_fields_list
                ],
            }
            return render(request, self.template_name, context)

        except LookupError:
            return HttpResponse(
                "<div id='error-message'>Invalid model</div>", status=400
            )


@method_decorator(htmx_required, name="dispatch")
class SaveFilterListView(FormView):
    template_name = "save_filter_form.html"
    form_class = SaveFilterListForm

    def get_initial(self):
        initial = super().get_initial()
        initial["model_name"] = self.request.GET.get("model_name")
        initial["main_url"] = self.request.GET.get("main_url", "")
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_params = {
            k: v
            for k, v in self.request.GET.lists()
            if k in ["field", "operator", "value", "start_value", "end_value", "search"]
        }
        context["query_params"] = query_params
        context["main_url"] = self.request.GET.get("main_url", "")
        return context

    def form_valid(self, form):
        list_name = form.cleaned_data["list_name"]
        model_name = form.cleaned_data["model_name"]
        filter_params = {
            k: v
            for k, v in self.request.POST.lists()
            if k in ["field", "operator", "value", "start_value", "end_value"]
        }
        search_query = self.request.GET.get("search", "")
        if search_query:
            filter_params["search"] = [search_query]
        if not any(filter_params.values()):
            form.add_error(None, "At least one filter is required.")
            return self.form_invalid(form)
        try:
            saved_filter_list, created = (
                self.request.user.saved_filter_lists.update_or_create(
                    name=list_name,
                    model_name=model_name,
                    defaults={"filter_params": filter_params},
                )
            )
            main_url = form.cleaned_data["main_url"]
            view_type = f"saved_list_{saved_filter_list.id}"
            # Preserve other query parameters from the original request
            query_params = {
                k: v
                for k, v in self.request.GET.items()
                if k not in ["view_type", "search"]  # Exclude existing view_type
            }
            query_params["view_type"] = view_type

            redirect_url = f"{main_url}?{urlencode(query_params)}"
            return HttpResponseRedirect(redirect_url)
        except IntegrityError:
            form.add_error(
                "list_name", "A list with this name already exists for this model."
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


@method_decorator(htmx_required, name="dispatch")
class PinView(LoginRequiredMixin, View):
    def post(self, request):
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
                html = render_to_string("navbar.html", context)
                return HttpResponse(html)
            else:
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
                html = render_to_string("navbar.html", context)
                return HttpResponse(html)
        except Exception as e:
            return HttpResponse(status=500)


@method_decorator(htmx_required, name="dispatch")
class DeleteSavedListView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        saved_list_id = request.POST.get("saved_list_id")
        main_url = request.POST.get("main_url")
        model_name = request.POST.get("model_name")  # Fallback to a default URL

        if not saved_list_id:
            messages.error(request, "Invalid saved list ID.")
            response = HttpResponseRedirect(main_url)
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
                pass
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
        response = HttpResponseRedirect(redirect_url)
        response["HX-Push-Url"] = "true"
        return response


# @method_decorator(htmx_required, name="dispatch")
# class EditFieldView(LoginRequiredMixin, View):
#     """
#     View to render an editable field input for a specific object field.
#     """

#     template_name = "partials/edit_field.html"
#     model = None

#     def get_field_info(self, field, obj):
#         """Get field information including type, choices, and current value"""
#         field_info = {
#             "name": field.name,
#             "verbose_name": field.verbose_name,
#             "field_type": "text",  # default
#             "value": getattr(obj, field.name, ""),
#             "choices": [],
#             "display_value": str(getattr(obj, field.name, "")),
#         }
#         if isinstance(field, models.ManyToManyField):
#             field_info["field_type"] = "select"
#             field_info["multiple"] = True  # Indicate multi-select
#             field_info["choices"] = []
#             related_objects = field.related_model.objects.all()
#             field_info["choices"].extend(
#                 [{"value": obj.pk, "label": str(obj)} for obj in related_objects]
#             )
#             current_values = getattr(obj, field.name).values_list("pk", flat=True)
#             field_info["value"] = list(current_values) if current_values else []
#             field_info["display_value"] = (
#                 ", ".join(str(item) for item in getattr(obj, field.name).all())
#                 if getattr(obj, field.name).exists()
#                 else ""
#             )

#         elif isinstance(field, models.ForeignKey):
#             field_info["field_type"] = "select"
#             field_info["choices"] = [{"value": "", "label": "---------"}]
#             related_objects = field.related_model.objects.all()
#             field_info["choices"].extend(
#                 [{"value": obj.pk, "label": str(obj)} for obj in related_objects]
#             )
#             current_obj = getattr(obj, field.name)
#             field_info["value"] = current_obj.pk if current_obj else ""
#             field_info["display_value"] = str(current_obj) if current_obj else ""

#         elif hasattr(field, "choices") and field.choices:
#             field_info["field_type"] = "select"
#             field_info["choices"] = [{"value": "", "label": "---------"}]
#             field_info["choices"].extend(
#                 [{"value": choice[0], "label": choice[1]} for choice in field.choices]
#             )
#             field_info["display_value"] = getattr(obj, f"get_{field.name}_display")()

#         elif isinstance(field, models.BooleanField):
#             field_info["field_type"] = "select"
#             field_info["choices"] = [
#                 {"value": "", "label": "---------"},
#                 {"value": "True", "label": "Yes"},
#                 {"value": "False", "label": "No"},
#             ]
#             current_value = getattr(obj, field.name)
#             field_info["value"] = (
#                 str(current_value) if current_value is not None else ""
#             )
#             field_info["display_value"] = (
#                 "Yes" if current_value else "No" if current_value is False else ""
#             )

#         elif isinstance(field, models.EmailField):
#             field_info["field_type"] = "email"

#         elif isinstance(field, models.URLField):
#             field_info["field_type"] = "url"

#         elif isinstance(
#             field,
#             (models.IntegerField, models.BigIntegerField, models.SmallIntegerField),
#         ):
#             field_info["field_type"] = "number"

#         elif isinstance(field, (models.DecimalField, models.FloatField)):
#             field_info["field_type"] = "number"
#             field_info["step"] = "0.01"

#         elif isinstance(field, models.DateTimeField):
#             field_info["field_type"] = "datetime-local"
#             if field_info["value"]:
#                 field_info["value"] = field_info["value"].strftime("%Y-%m-%dT%H:%M")

#         elif isinstance(field, models.DateField):
#             field_info["field_type"] = "date"
#             if field_info["value"]:
#                 field_info["value"] = field_info["value"].strftime("%Y-%m-%d")

#         elif isinstance(field, models.TextField):
#             field_info["field_type"] = "textarea"

#         return field_info

#     def get(self, request, pk, field_name, app_label, model_name):
#         pipeline_field = request.GET.get("pipeline_field", None)
#         try:
#             if not self.model:
#                 self.model = apps.get_model(app_label, model_name)
#             obj = get_object_or_404(self.model, pk=pk)
#             field = next(
#                 (f for f in obj._meta.get_fields() if f.name == field_name), None
#             )
#         except Exception as e:
#             messages.error(self.request, e)
#             return HttpResponse("<script>$('#reloadButton').click();</script>")

#         field_info = self.get_field_info(field, obj)

#         context = {
#             "object_id": pk,
#             "field_info": field_info,
#             "app_label": app_label,
#             "model_name": model_name,
#             "pipeline_field": pipeline_field,
#         }
#         return render(request, self.template_name, context)


@method_decorator(htmx_required, name="dispatch")
class EditFieldView(LoginRequiredMixin, View):
    """
    View to render an editable field input for a specific object field.
    """

    template_name = "partials/edit_field.html"
    model = None

    def get_field_info(self, field, obj):
        """Get field information including type, choices, and current value"""
        field_info = {
            "name": field.name,
            "verbose_name": field.verbose_name,
            "field_type": "text",  # default
            "value": getattr(obj, field.name, ""),
            "choices": [],
            "display_value": str(getattr(obj, field.name, "")),
            "use_select2": False,  # Default to False
        }

        if isinstance(field, models.ManyToManyField):
            field_info["field_type"] = "select"
            field_info["multiple"] = True
            field_info["use_select2"] = True

            related_model = field.related_model
            field_info["related_app_label"] = related_model._meta.app_label
            field_info["related_model_name"] = related_model._meta.model_name

            # Get current values
            current_values = getattr(obj, field.name).values_list("pk", flat=True)
            field_info["value"] = list(current_values) if current_values else []

            # Get initial choices for selected items only
            field_info["choices"] = []
            if current_values:
                selected_objects = related_model.objects.filter(pk__in=current_values)
                field_info["choices"] = [
                    {"value": obj.pk, "label": str(obj)} for obj in selected_objects
                ]

            field_info["display_value"] = (
                ", ".join(str(item) for item in getattr(obj, field.name).all())
                if getattr(obj, field.name).exists()
                else ""
            )

        elif isinstance(field, models.ForeignKey):
            field_info["field_type"] = "select"
            field_info["use_select2"] = True

            related_model = field.related_model
            field_info["related_app_label"] = related_model._meta.app_label
            field_info["related_model_name"] = related_model._meta.model_name

            # Get current value
            current_obj = getattr(obj, field.name)
            field_info["value"] = current_obj.pk if current_obj else ""

            # Get initial choices - only the selected item if exists
            field_info["choices"] = [{"value": "", "label": "---------"}]
            if current_obj:
                field_info["choices"].append(
                    {"value": current_obj.pk, "label": str(current_obj)}
                )

            field_info["display_value"] = str(current_obj) if current_obj else ""

        elif hasattr(field, "choices") and field.choices:
            field_info["field_type"] = "select"
            field_info["choices"] = [{"value": "", "label": "---------"}]
            field_info["choices"].extend(
                [{"value": choice[0], "label": choice[1]} for choice in field.choices]
            )
            field_info["display_value"] = getattr(obj, f"get_{field.name}_display")()

        elif isinstance(field, models.BooleanField):
            field_info["field_type"] = "select"
            field_info["choices"] = [
                {"value": "", "label": "---------"},
                {"value": "True", "label": "Yes"},
                {"value": "False", "label": "No"},
            ]
            current_value = getattr(obj, field.name)
            field_info["value"] = (
                str(current_value) if current_value is not None else ""
            )
            field_info["display_value"] = (
                "Yes" if current_value else "No" if current_value is False else ""
            )

        elif isinstance(field, models.EmailField):
            field_info["field_type"] = "email"

        elif isinstance(field, models.URLField):
            field_info["field_type"] = "url"

        elif isinstance(
            field,
            (models.IntegerField, models.BigIntegerField, models.SmallIntegerField),
        ):
            field_info["field_type"] = "number"

        elif isinstance(field, (models.DecimalField, models.FloatField)):
            field_info["field_type"] = "number"
            field_info["step"] = "0.01"

        elif isinstance(field, models.DateTimeField):
            field_info["field_type"] = "datetime-local"
            if field_info["value"]:
                field_info["value"] = field_info["value"].strftime("%Y-%m-%dT%H:%M")

        elif isinstance(field, models.DateField):
            field_info["field_type"] = "date"
            if field_info["value"]:
                field_info["value"] = field_info["value"].strftime("%Y-%m-%d")

        elif isinstance(field, models.TextField):
            field_info["field_type"] = "textarea"

        return field_info

    def get(self, request, pk, field_name, app_label, model_name):
        pipeline_field = request.GET.get("pipeline_field", None)
        try:
            if not self.model:
                self.model = apps.get_model(app_label, model_name)
            obj = get_object_or_404(self.model, pk=pk)
            field = next(
                (f for f in obj._meta.get_fields() if f.name == field_name), None
            )
        except Exception as e:
            messages.error(self.request, e)
            return HttpResponse("<script>$('#reloadButton').click();</script>")

        field_info = self.get_field_info(field, obj)

        context = {
            "object_id": pk,
            "field_info": field_info,
            "app_label": app_label,
            "model_name": model_name,
            "pipeline_field": pipeline_field,
        }
        return render(request, self.template_name, context)


@method_decorator(htmx_required, name="dispatch")
class UpdateFieldView(LoginRequiredMixin, View):
    """
    View to handle updating a single field of an object.
    """

    template_name = "partials/field_display.html"
    model = None

    def post(self, request, pk, field_name, app_label, model_name):
        try:
            if not self.model:
                self.model = apps.get_model(app_label, model_name)
            obj = get_object_or_404(self.model, pk=pk)
            field = next(
                (f for f in obj._meta.get_fields() if f.name == field_name), None
            )
        except Exception as e:
            messages.error(self.request, e)
            return HttpResponse("<script>$('#reloadButton').click();</script>")

        if not field:
            return HttpResponse(status=404)

        value = request.POST.get(field_name)

        if value is not None:
            try:
                # Handle different field types
                if isinstance(field, models.ForeignKey):
                    if value == "":
                        setattr(obj, field_name, None)
                    else:
                        related_obj = field.related_model.objects.get(pk=value)
                        setattr(obj, field_name, related_obj)

                elif isinstance(field, models.BooleanField):
                    if value == "":
                        setattr(obj, field_name, None)
                    else:
                        setattr(obj, field_name, value == "True")

                elif isinstance(
                    field,
                    (
                        models.IntegerField,
                        models.BigIntegerField,
                        models.SmallIntegerField,
                    ),
                ):
                    setattr(obj, field_name, int(value) if value else None)

                elif isinstance(field, models.DecimalField):
                    if value:
                        try:
                            setattr(obj, field_name, Decimal(value))
                        except InvalidOperation:
                            return HttpResponse(
                                f"Invalid decimal value: {value}", status=400
                            )
                    else:
                        setattr(obj, field_name, None)

                elif isinstance(field, models.FloatField):
                    setattr(obj, field_name, float(value) if value else None)

                elif isinstance(field, (models.DateField, models.DateTimeField)):
                    if value:
                        try:
                            if isinstance(field, models.DateTimeField):
                                parsed_value = datetime.fromisoformat(value)
                            else:  # DateField
                                parsed_value = datetime.fromisoformat(value).date()
                            setattr(obj, field_name, parsed_value)
                        except ValueError:
                            return HttpResponse(
                                f"Invalid date format: {value}", status=400
                            )
                    else:
                        setattr(obj, field_name, None)

                else:
                    setattr(obj, field_name, value)

                obj.save()

            except Exception as e:
                return HttpResponse(f"Error updating field: {str(e)}", status=400)

        # Get updated field info for display
        edit_view = EditFieldView()
        field_info = edit_view.get_field_info(field, obj)

        context = {
            "field_info": field_info,
            "object_id": pk,
            "app_label": app_label,
            "model_name": model_name,
        }
        return render(request, self.template_name, context)


@method_decorator(htmx_required, name="dispatch")
class CancelEditView(LoginRequiredMixin, View):
    """
    View to cancel editing and return to display mode without saving.
    """

    template_name = "partials/field_display.html"
    model = None

    def get(self, request, pk, field_name, app_label, model_name):
        try:
            if not self.model:
                self.model = apps.get_model(app_label, model_name)
            obj = get_object_or_404(self.model, pk=pk)
            field = next(
                (f for f in obj._meta.get_fields() if f.name == field_name), None
            )
        except Exception as e:
            messages.error(self.request, e)
            return HttpResponse("<script>$('#reloadButton').click();</script>")

        # Use the same field info structure as EditFieldView
        edit_view = EditFieldView()
        field_info = edit_view.get_field_info(field, obj)

        context = {
            "field_info": field_info,
            "object_id": pk,
            "app_label": app_label,
            "model_name": model_name,
        }
        return render(request, self.template_name, context)


@method_decorator(htmx_required, name="dispatch")
class KanbanLoadMoreView(LoginRequiredMixin, View):
    """
    Handle AJAX request to load more items for a specific Kanban column.
    """

    def get(self, request, app_label, model_name, *args, **kwargs):
        """
        Handle GET request to load more items for a specific Kanban column.
        """
        try:
            model = apps.get_model(
                app_label=app_label.split(".")[-1], model_name=model_name
            )
            view_class = HorillaKanbanView._view_registry.get(model)
            if not view_class:
                messages.error(request, f"View class {model_name} not found")
                return HttpResponse("<script>$('#reloadButton').click();")

            view = view_class()
            view.request = request

            return view.load_more_items(request)
        except Exception as e:
            messages.error(request, f"Load More failed")
            return HttpResponse("<script>$('#reloadButton').click();")


class HorillaSelect2DataView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        if not request.headers.get("x-requested-with") == "XMLHttpRequest":
            return render(request, "error/405.html", status=405)
        app_label = kwargs.get("app_label")
        model_name = kwargs.get("model_name")
        field_name = request.GET.get("field_name")

        try:
            model = apps.get_model(app_label=app_label, model_name=model_name)
        except LookupError as e:
            raise HorillaHttp404(e)

        search_term = request.GET.get("q", "").strip()
        ids = request.GET.get("ids", "").strip()
        page = request.GET.get("page", "1")
        dependency_value = request.GET.get("dependency_value", "").strip()
        dependency_model = request.GET.get("dependency_model", "").strip()
        dependency_field = request.GET.get("dependency_field", "").strip()
        try:
            page = int(page)
        except ValueError:
            page = 1
        per_page = 10

        queryset = None
        form_class = self._get_form_class_from_request(request)
        if form_class and field_name:
            try:
                form = form_class(request=request)
                if field_name in form.fields:
                    queryset = form.fields[field_name].queryset
            except Exception as e:
                logger.error(f"[Select2] Could not resolve queryset from form: {e}")

        if queryset is None:
            queryset = model.objects.all()

        # owner filtration
        user_model = get_user_model()

        if model is user_model:
            queryset = self._apply_owner_filter(request.user, queryset)
        elif hasattr(model, "OWNER_FIELDS") and model.OWNER_FIELDS:
            allowed_user_ids = self._get_allowed_user_ids(request.user)
            if allowed_user_ids:
                query = Q()
                for owner_field in model.OWNER_FIELDS:
                    query |= Q(**{f"{owner_field}__id__in": allowed_user_ids})
                queryset = queryset.filter(query)
            else:
                queryset = queryset.none()

        if dependency_value and dependency_model and dependency_field:
            try:
                dep_app_label, dep_model_name = dependency_model.split(".")
                related_model = apps.get_model(
                    app_label=dep_app_label, model_name=dep_model_name
                )

                field = model._meta.get_field(dependency_field)
                if field.related_model != related_model:
                    raise ValueError(
                        f"Field {dependency_field} does not reference {dependency_model}"
                    )

                filter_kwargs = {f"{dependency_field}__pk": dependency_value}
                queryset = queryset.filter(**filter_kwargs)
            except (ValueError, LookupError, AttributeError):
                queryset = queryset.none()

        if ids:
            try:
                id_list = [
                    int(id.strip()) for id in ids.split(",") if id.strip().isdigit()
                ]
                if id_list:
                    queryset = queryset.filter(pk__in=id_list)
                    results = [
                        {
                            "id": obj.pk,
                            "text": str(obj) or f"Unnamed {model_name} {obj.pk}",
                        }
                        for obj in queryset
                    ]
                    return JsonResponse(
                        {"results": results, "pagination": {"more": False}}
                    )
                else:
                    return JsonResponse({"results": [], "pagination": {"more": False}})
            except Exception:
                return JsonResponse({"results": [], "pagination": {"more": False}})

        if search_term:
            search_fields = [
                f.name
                for f in model._meta.fields
                if isinstance(f, (CharField, TextField)) and f.name != "id"
            ]
            if search_fields:
                query = Q()
                for field in search_fields:
                    query |= Q(**{f"{field}__icontains": search_term})
                queryset = queryset.filter(query)
            else:
                queryset = queryset.none()
        else:
            queryset = queryset.order_by("pk")

        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)

        results = [
            {"id": obj.pk, "text": str(obj) or f"Unnamed {model_name} {obj.pk}"}
            for obj in page_obj.object_list
        ]

        return JsonResponse(
            {"results": results, "pagination": {"more": page_obj.has_next()}}
        )

    def _get_form_class_from_request(self, request):
        """
        Optional: resolve which form is being used.
        You can pass it via request.GET or hardcode a mapping per model.
        """
        form_path = request.GET.get("form_class")
        if not form_path:
            return None

        if "DynamicForm" in form_path:
            return None
        try:
            module_path, class_name = form_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except Exception as e:
            logger.error(f"[Select2] Could not import form_class {form_path}: {e}")
            return None

    # owner filtration
    def _get_allowed_user_ids(self, user):
        """
        Get list of allowed user IDs (self + subordinates) for filtering.
        """
        User = get_user_model()
        if not user or not user.is_authenticated:
            return []

        if user.is_superuser:
            return list(User.objects.values_list("id", flat=True))

        user_role = getattr(user, "role", None)
        if not user_role:
            return [user.id]

        def get_subordinate_roles(role):
            sub_roles = role.subroles.all()
            all_sub_roles = []
            for sub_role in sub_roles:
                all_sub_roles.append(sub_role)
                all_sub_roles.extend(get_subordinate_roles(sub_role))
            return all_sub_roles

        subordinate_roles = get_subordinate_roles(user_role)
        subordinate_users = User.objects.filter(role__in=subordinate_roles).distinct()

        allowed_user_ids = [user.id] + list(
            subordinate_users.values_list("id", flat=True)
        )
        return allowed_user_ids

    # owner filtration
    def _apply_owner_filter(self, user, queryset):
        """
        Filter User queryset based on user permissions.
        """
        allowed_user_ids = self._get_allowed_user_ids(user)
        return queryset.filter(id__in=allowed_user_ids)


@method_decorator(htmx_required, name="dispatch")
class RemoveConditionRowView(LoginRequiredMixin, View):
    def delete(self, request, row_id, *args, **kwargs):

        return HttpResponse("")


@method_decorator(htmx_required, name="dispatch")
class GetFieldValueWidgetView(LoginRequiredMixin, View):
    """HTMX view to return dynamic value field widget based on selected field"""

    def get(self, request):
        row_id = request.GET.get("row_id")
        field_name = request.GET.get(f"field_{row_id}", request.GET.get("field", ""))
        model_name = request.GET.get("model_name", "")

        # Try to get existing value from the request
        existing_value = request.GET.get(f"value_{row_id}", "")

        # Get the model field to determine appropriate widget
        widget_html = self._get_value_widget_html(
            field_name, model_name, row_id, existing_value
        )

        return HttpResponse(widget_html)

    def _get_value_widget_html(self, field_name, model_name, row_id, existing_value=""):
        """Generate appropriate widget HTML based on selected field"""

        if not field_name or not model_name:
            # Return default text input
            return self._render_text_input(row_id, existing_value)

        try:
            # Find the model
            model = None
            for app_config in apps.get_app_configs():
                try:
                    model = apps.get_model(
                        app_label=app_config.label, model_name=model_name
                    )
                    break
                except LookupError:
                    continue

            if not model:
                return self._render_text_input(row_id, existing_value)

            # Get the field from the model
            try:
                model_field = model._meta.get_field(field_name)
            except:
                return self._render_text_input(row_id, existing_value)

            # Determine widget type based on field type
            if isinstance(model_field, models.ForeignKey):
                related_model = model_field.related_model
                choices = [(obj.pk, str(obj)) for obj in related_model.objects.all()]
                return self._render_select_input(choices, row_id, existing_value)
            elif hasattr(model_field, "choices") and model_field.choices:
                return self._render_select_input(
                    model_field.choices, row_id, existing_value
                )
            elif isinstance(model_field, models.BooleanField):
                return self._render_boolean_input(row_id, existing_value)
            elif isinstance(model_field, models.DateField):
                return self._render_date_input(row_id, existing_value)
            elif isinstance(model_field, models.DateTimeField):
                return self._render_datetime_input(row_id, existing_value)
            elif isinstance(model_field, models.TimeField):
                return self._render_time_input(row_id, existing_value)
            elif isinstance(model_field, models.IntegerField):
                return self._render_number_input(row_id, existing_value)
            elif isinstance(model_field, models.DecimalField):
                return self._render_number_input(row_id, existing_value, step="0.01")
            elif isinstance(model_field, models.EmailField):
                return self._render_email_input(row_id, existing_value)
            elif isinstance(model_field, models.URLField):
                return self._render_url_input(row_id, existing_value)
            elif isinstance(model_field, models.TextField):
                return self._render_textarea_input(row_id, existing_value)
            else:
                return self._render_text_input(row_id, existing_value)

        except Exception as e:
            logger.error(f"Error generating value widget: {str(e)}")
            return self._render_text_input(row_id, existing_value)

    def _render_text_input(self, row_id, existing_value=""):
        return f"""
        <input type="text"
               name="value_{row_id}"
               id="id_value_{row_id}"
               value="{existing_value}"
               class="text-color-820 p-2 placeholder:text-xs pr-[40px] w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600"
               placeholder="Enter Value">
        """

    def _render_select_input(self, choices, row_id, existing_value=""):
        options = '<option value="">---------</option>'
        for choice_value, choice_label in choices:
            selected = "selected" if str(choice_value) == str(existing_value) else ""
            options += (
                f'<option value="{choice_value}" {selected}>{choice_label}</option>'
            )

        return f"""
        <select name="value_{row_id}"
                id="id_value_{row_id}"
                class="js-example-basic-single headselect">
            {options}
        </select>
        """

    def _render_boolean_input(self, row_id, existing_value=""):
        true_selected = "selected" if existing_value == "True" else ""
        false_selected = "selected" if existing_value == "False" else ""

        return f"""
        <select name="value_{row_id}"
                id="id_value_{row_id}"
                class="text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600">
            <option value="">---------</option>
            <option value="True" {true_selected}>True</option>
            <option value="False" {false_selected}>False</option>
        </select>
        """

    def _render_date_input(self, row_id, existing_value=""):
        return f"""
        <input type="date"
               name="value_{row_id}"
               id="id_value_{row_id}"
               value="{existing_value}"
               class="text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600">
        """

    def _render_datetime_input(self, row_id, existing_value=""):
        return f"""
        <input type="datetime-local"
               name="value_{row_id}"
               id="id_value_{row_id}"
               value="{existing_value}"
               class="text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600">
        """

    def _render_time_input(self, row_id, existing_value=""):
        return f"""
        <input type="time"
               name="value_{row_id}"
               id="id_value_{row_id}"
               value="{existing_value}"
               class="text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600">
        """

    def _render_number_input(self, row_id, existing_value="", step="1"):
        return f"""
        <input type="number"
               name="value_{row_id}"
               id="id_value_{row_id}"
               value="{existing_value}"
               step="{step}"
               class="text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600"
               placeholder="Enter Number">
        """

    def _render_email_input(self, row_id, existing_value=""):
        return f"""
        <input type="email"
               name="value_{row_id}"
               id="id_value_{row_id}"
               value="{existing_value}"
               class="text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600"
               placeholder="Enter Email">
        """

    def _render_url_input(self, row_id, existing_value=""):
        return f"""
        <input type="url"
               name="value_{row_id}"
               id="id_value_{row_id}"
               value="{existing_value}"
               class="text-color-600 p-2 placeholder:text-xs w-full border border-dark-50 rounded-md mt-1 focus-visible:outline-0 placeholder:text-dark-100 text-sm [transition:.3s] focus:border-primary-600"
               placeholder="Enter URL">
        """

    def _render_textarea_input(self, row_id, existing_value=""):
        return f"""
        <textarea name="value_{row_id}"
                  id="id_value_{row_id}"
                  rows="3"
                  class="text-color-600 p-2 w-full border border-dark-50 rounded-md focus-visible:outline-0 text-sm transition focus:border-primary-600"
                  placeholder="Enter Value">{existing_value}</textarea>
        """
