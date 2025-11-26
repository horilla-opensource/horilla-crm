import re
from functools import reduce
from operator import or_
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse

from django.apps import apps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import CharField, ForeignKey, ManyToManyField, Q, TextField
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.views import View

from horilla.registry.feature import FEATURE_REGISTRY
from horilla_generics.views import HorillaListView
from horilla_utils.methods import get_section_info_for_model


class GlobalSearchView(LoginRequiredMixin, View):
    template_name = "global_search.html"
    include_models = FEATURE_REGISTRY.get("global_search_models", [])

    # Standard fields to exclude from column display
    exclude_standard_fields = [
        "is_active",
        "additional_info",
        "company",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by",
        "history",
        "id",
        "password",
    ]

    default_max_results = 3
    default_icons = {
        "bg_color": "bg-blue-100",
        "text_color": "text-blue-600",
        "icon": "fas fa-table",
    }
    default_status_colors = {
        "active": "green",
        "inactive": "red",
        "pending": "yellow",
    }

    def get_first_5_text_columns(self, model):
        """Get FIRST 5 text-based columns (CharField and TextField) for a model."""
        columns = []

        for field in model._meta.fields:
            # Skip auto-created fields, excluded standard fields, and relations
            if (
                field.auto_created
                or field.name in self.exclude_standard_fields
                or field.is_relation
            ):
                continue

            # Only include CharField and TextField
            if isinstance(field, (CharField, TextField)):
                columns.append([str(field.verbose_name), field.name])

                # Limit to first 5 columns
                if len(columns) >= 5:
                    break

        return columns

    def get_dynamic_model_config(self):
        model_config = {}
        all_models = apps.get_models()

        include_models_lower = [
            model._meta.model_name.lower() for model in self.include_models
        ]

        for model in all_models:
            app_label = model._meta.app_label
            model_name = model._meta.model_name.capitalize()
            model_verbose_name = (
                model._meta.verbose_name_plural or model._meta.verbose_name
            )

            if model_name.lower() not in include_models_lower:
                continue

            # Get FIRST 5 searchable fields (CharField and TextField only)
            search_fields = []
            for field in model._meta.fields:
                if (
                    isinstance(field, (CharField, TextField))
                    and field.name not in self.exclude_standard_fields
                    and not field.auto_created
                    and not field.is_relation
                ):
                    search_fields.append(field.name)

                    if len(search_fields) >= 5:
                        break

            if not search_fields:
                continue

            display_columns = self.get_first_5_text_columns(model)

            if not display_columns:
                continue

            display_field_name = search_fields[0] if search_fields else "id"
            display_field = lambda x, field=display_field_name: getattr(
                x, field, str(x)
            )

            summary_fields = search_fields[:3]

            status_field = None
            for field in model._meta.fields:
                if field.name.lower() in [
                    "status",
                    "state",
                    "lead_status",
                    "campaign_status",
                ]:
                    status_field = field.name
                    break

            model_config[model_name] = {
                "app_name": app_label,
                "search_fields": search_fields,
                "display_field": display_field,
                "summary_fields": summary_fields,
                "status_field": status_field,
                "status_colors": self.default_status_colors if status_field else {},
                "icons": self.default_icons,
                "max_results": self.default_max_results,
                "model": model,
                "columns": display_columns,
                "verbose_name": model_verbose_name,
            }

        return model_config

    def get_filtered_queryset(self, model, base_queryset, request):
        """
        Filter queryset based on user permissions.
        If user has full view permission, return all records.
        If user only has view_own permission, return only their records based on OWNER_FIELDS.
        """

        user = request.user
        app_label = model._meta.app_label
        model_name = model._meta.model_name

        full_view_perm = f"{app_label}.view_{model_name}"
        view_own_perm = f"{app_label}.view_own_{model_name}"

        if user.has_perm(full_view_perm):
            return base_queryset

        elif user.has_perm(view_own_perm):
            owner_fields = getattr(model, "OWNER_FIELDS", None)

            if owner_fields:
                queries = []
                for field_name in owner_fields:
                    try:
                        field = model._meta.get_field(field_name)

                        if isinstance(field, ForeignKey):
                            related_model = field.related_model
                            if (
                                related_model._meta.model_name.lower()
                                in ["user", "employee"]
                                or related_model == user.__class__
                                or related_model._meta.label_lower == "auth.user"
                            ):
                                queries.append(Q(**{field_name: user}))
                        elif isinstance(field, ManyToManyField):
                            related_model = field.related_model
                            # Only add if it points to User model
                            if (
                                related_model._meta.model_name.lower()
                                in ["user", "employee"]
                                or related_model == user.__class__
                                or related_model._meta.label_lower == "auth.user"
                            ):
                                queries.append(Q(**{field_name: user}))
                        # Handle direct fields (non-relational)
                        elif not field.is_relation:
                            queries.append(Q(**{field_name: user}))
                    except Exception as e:
                        # Skip fields that cause errors
                        continue

                if queries:
                    # Use reduce with OR to combine multiple ownership fields
                    combined_query = reduce(or_, queries)
                    return base_queryset.filter(combined_query).distinct()

                # If no valid ownership fields, return empty queryset
                return base_queryset.none()
            else:
                # Fallback to common ownership field patterns
                ownership_fields = ["created_by", "user", "owner", "employee_id"]

                queries = []
                for field_name in ownership_fields:
                    try:
                        field = model._meta.get_field(field_name)

                        # Handle ForeignKey fields
                        if isinstance(field, ForeignKey):
                            related_model = field.related_model
                            if (
                                related_model._meta.model_name.lower()
                                in ["user", "employee"]
                                or related_model == user.__class__
                                or related_model._meta.label_lower == "auth.user"
                            ):
                                queries.append(Q(**{field_name: user}))
                        # Handle ManyToManyField
                        elif isinstance(field, ManyToManyField):
                            related_model = field.related_model
                            if (
                                related_model._meta.model_name.lower()
                                in ["user", "employee"]
                                or related_model == user.__class__
                                or related_model._meta.label_lower == "auth.user"
                            ):
                                queries.append(Q(**{field_name: user}))
                        # Handle direct fields
                        elif not field.is_relation:
                            queries.append(Q(**{field_name: user}))
                    except Exception as e:
                        continue

                if queries:
                    # Combine all queries with OR
                    combined_query = reduce(or_, queries)
                    return base_queryset.filter(combined_query).distinct()

                return base_queryset.none()

        return base_queryset.none()

    def get_tab_content(self, request, model_name, query):
        """Generate tab content for a specific model"""
        model_config = self.get_dynamic_model_config()

        if model_name not in model_config:
            return '<div class="p-4">Model not found.</div>'

        config = model_config[model_name]
        model = apps.get_model(config["app_name"], model_name)

        q_objects = Q()
        for field in config["search_fields"]:
            q_objects |= Q(**{f"{field}__icontains": query})

        results = model.objects.filter(q_objects)

        results = self.get_filtered_queryset(model, results, request)

        def highlight_text(text):
            if not text:
                return text
            return mark_safe(
                re.sub(
                    f"({re.escape(query)})",
                    r'<span class="bg-yellow-200">\1</span>',
                    str(text),
                    flags=re.IGNORECASE,
                )
            )

        for item in results:
            item.display_name = highlight_text(config["display_field"](item))
            summary_parts = []

            for field in config["summary_fields"]:
                value = getattr(item, field, None)
                if value is not None and str(value).strip():
                    if field == "amount":
                        value = f"${value:,.0f}"
                    elif field == "close_date":
                        value = (
                            value.strftime("%b %Y")
                            if hasattr(value, "strftime")
                            else value
                        )
                    elif field == "open_rate":
                        value = f"{value}%"
                    summary_parts.append(highlight_text(value))

            item.summary = " • ".join(str(part) for part in summary_parts if part)
            item.status = (
                getattr(item, config["status_field"], None)
                if config["status_field"]
                else None
            )
            item.status_color = (
                config["status_colors"].get(item.status, "gray")
                if item.status
                else None
            )

        list_view = HorillaListView()
        list_view.request = request
        list_view.view_id = f"global-search-{model_name.lower()}"
        list_view.model = model
        list_view.queryset = results
        list_view.kwargs = {}
        list_view.paginate_by = 100
        list_view.object_list = results
        list_view.table_height = False
        list_view.table_height_as_class = "h-[650px]"
        list_view.bulk_select_option = False
        list_view.clear_session_button_enabled = False
        list_view.table_width = False
        list_view.search_url = reverse_lazy("horilla_generics:global_search")
        list_view.list_column_visibility = False
        list_view.columns = config["columns"]

        if config["columns"] and hasattr(model, "get_detail_url"):
            first_column_field = config["columns"][0][1]
            htmx_attrs = self.get_col_attrs_for_model(model_name, request)
            list_view.col_attrs = [
                {
                    first_column_field: {
                        "style": "cursor:pointer",
                        "class": "hover:text-primary-600",
                        **htmx_attrs,
                    }
                }
            ]

        query_params = request.GET.copy()
        if "page" in query_params:
            del query_params["page"]

        table_context = list_view.get_context_data()
        table_context.update(
            {
                "search_params": query_params.urlencode(),
                "model_name": model_name,
                "icons": config["icons"],
                "status_colors": config["status_colors"],
                "status_field": config["status_field"],
                "view_id": f"global-search-{model_name.lower()}",
            }
        )

        return render_to_string("list_view.html", table_context, request)

    def get(self, request):
        query = request.GET.get("q", "").strip()
        filter_type = request.GET.get("filter", "all")
        previous_url = request.GET.get("prev_url", "/")
        search_url_path = str(reverse_lazy("horilla_generics:global_search"))

        if previous_url:
            try:
                previous_url = unquote(unquote(previous_url))

                if "?" in previous_url:

                    parsed = urlparse(previous_url)
                    query_params = parse_qs(parsed.query)

                    if "section" in query_params:
                        del query_params["section"]

                    new_query = urlencode(query_params, doseq=True)
                    previous_url = urlunparse(
                        (
                            parsed.scheme,
                            parsed.netloc,
                            parsed.path,
                            parsed.params,
                            new_query,
                            parsed.fragment,
                        )
                    )

                if (
                    previous_url.startswith(search_url_path)
                    or "global_search" in previous_url
                ):
                    previous_url = request.session.get("pre_search_url", "/")
                else:
                    request.session["pre_search_url"] = previous_url
            except:
                previous_url = request.session.get("pre_search_url", "/")

        if not query:
            section = request.GET.get("section")
            if section:
                # Add section back to previous_url
                if "?" in previous_url:
                    previous_url += f"&section={section}"
                else:
                    previous_url += f"?section={section}"
            if request.headers.get("HX-Request"):
                response = HttpResponse()
                response["HX-Redirect"] = previous_url
                return response
            return redirect(previous_url)

        if request.headers.get("HX-Request"):
            tab_model = request.GET.get("tab_model")
            if tab_model and query:
                return HttpResponse(self.get_tab_content(request, tab_model, query))

        model_config = self.get_dynamic_model_config()

        context = {
            "query": query,
            "filter": filter_type,
            "total_results": 0,
            "model_config": model_config,
            "search_results": {},
            "search_results_with_data": {},
            "first_tab_content": "",
            "previous_url": previous_url,
        }

        if query:
            search_results = {}
            search_results_with_data = {}
            total_results = 0
            first_tab_content = ""
            first_model_name = None

            for model_name, config in model_config.items():
                model = apps.get_model(config["app_name"], model_name)

                q_objects = Q()
                for field in config["search_fields"]:
                    q_objects |= Q(**{f"{field}__icontains": query})

                results = model.objects.filter(q_objects)

                results = self.get_filtered_queryset(model, results, request)

                search_results[model_name] = results

                if results.count() > 0:
                    search_results_with_data[model_name] = results
                    total_results += results.count()

            sorted_search_results_with_data = dict(
                sorted(
                    search_results_with_data.items(),
                    key=lambda x: x[1].count(),
                    reverse=True,
                )
            )

            if sorted_search_results_with_data:
                first_model_name = list(sorted_search_results_with_data.keys())[0]
                first_tab_content = self.get_tab_content(
                    request, first_model_name, query
                )

            if filter_type != "all":
                model_name_filtered = filter_type.capitalize()
                if (
                    model_name_filtered in sorted_search_results_with_data
                    and sorted_search_results_with_data[model_name_filtered].count() > 0
                ):
                    sorted_search_results_with_data = {
                        model_name_filtered: sorted_search_results_with_data[
                            model_name_filtered
                        ]
                    }
                    first_model_name = model_name_filtered
                    first_tab_content = self.get_tab_content(
                        request, first_model_name, query
                    )
                else:
                    sorted_search_results_with_data = {}
                    first_tab_content = ""
                    first_model_name = None

            context.update(
                {
                    "search_results": sorted_search_results_with_data,
                    "search_results_with_data": sorted_search_results_with_data,
                    "total_results": total_results,
                    "first_tab_content": first_tab_content,
                    "first_model_name": first_model_name,
                }
            )

        return render(request, self.template_name, context)

    def get_col_attrs_for_model(self, model_name, request):
        """Generate col_attrs for the first column of each model"""
        query_params = request.GET.dict()
        filtered_params = {}
        if "q" in query_params:
            filtered_params["q"] = query_params["q"]
        if "filter" in query_params:
            filtered_params["filter"] = query_params["filter"]
        if "section" in query_params:

            section = get_section_info_for_model(model_name)
            filtered_params["section"] = section["section"]
        query_string = urlencode(filtered_params)

        htmx_attrs = {
            "hx-get": f"{{get_detail_url}}?{query_string}",
            "hx-target": "#mainContent",
            "hx-swap": "outerHTML",
            "hx-push-url": "true",
            "hx-select": "#mainContent",
            "hx-select-oob": "#sideMenuContainer",
            "hx-on:click": "$('#header-search').val('')",
        }
        return htmx_attrs
