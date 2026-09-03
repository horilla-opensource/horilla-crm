"""Dashboard utilities for campaigns module."""

# Standard library imports
import logging

# Third-party imports (Django)
from django.utils.http import urlencode

from horilla.contrib.dashboard.utils import DefaultDashboardGenerator
from horilla.contrib.utils.methods import get_section_info_for_model

# First party imports (Horilla)
from horilla.db.models import Count
from horilla.utils.choices import TABLE_FALLBACK_FIELD_TYPES
from horilla.utils.translation import gettext_lazy as _

# Local imports
from .models import Campaign

logger = logging.getLogger(__name__)


def campaign_table_fields(model_class):
    """Return list of {name, verbose_name} for campaign table columns."""

    priority = ["campaign_name", "campaign_type", "status", "expected_revenue"]
    fields = []
    for name in priority:
        try:
            f = model_class._meta.get_field(name)
            fields.append(
                {
                    "name": name,
                    "verbose_name": f.verbose_name or name.replace("_", " ").title(),
                }
            )
        except Exception:
            continue
    if len(fields) < 4:
        for f in model_class._meta.fields:
            if len(fields) >= 4:
                break
            if (
                f.name not in [x["name"] for x in fields]
                and f.get_internal_type() in TABLE_FALLBACK_FIELD_TYPES
            ):
                fields.append(
                    {
                        "name": f.name,
                        "verbose_name": f.verbose_name
                        or f.name.replace("_", " ").title(),
                    }
                )
    return fields


def create_campaign_charts(self, queryset, model_info):
    """Create campaign-specific charts"""
    try:
        if hasattr(queryset.model, "campaign_type") or hasattr(queryset.model, "type"):
            type_field = (
                "campaign_type" if hasattr(queryset.model, "campaign_type") else "type"
            )
            type_data = (
                queryset.values(type_field)
                .annotate(count=Count("id"))
                .order_by("-count")
            )

            if type_data.exists():
                labels = [item[type_field] or "Unknown" for item in type_data]
                data = [item["count"] for item in type_data]

                section_info = get_section_info_for_model(queryset.model)
                urls = []
                for item in type_data:
                    value = item[type_field] or "Unknown"
                    query = urlencode(
                        {
                            "section": section_info["section"],
                            "apply_filter": "true",
                            "field": type_field,
                            "operator": "exact",
                            "value": value,
                        }
                    )
                    urls.append(f"{section_info['url']}?{query}")

                return {
                    "title": _("Campaigns by Type"),
                    "type": "donut",
                    "data": {
                        "labels": labels,
                        "data": data,
                        "urls": urls,
                        "labelField": "Campaign Type",
                    },
                }

        if hasattr(queryset.model, "status"):
            status_data = (
                queryset.values("status").annotate(count=Count("id")).order_by("-count")
            )

            if status_data.exists():
                labels = [item["status"] or "No Status" for item in status_data]
                data = [item["count"] for item in status_data]

                return {
                    "title": _("Campaigns by Status"),
                    "type": "column",
                    "data": {
                        "labels": labels,
                        "data": data,
                        "labelField": "Status",
                    },
                }

        if hasattr(queryset.model, "is_active"):
            active_data = queryset.values("is_active").annotate(count=Count("id"))

            if active_data.exists():
                labels = []
                data = []
                for item in active_data:
                    status = "Active" if item["is_active"] else "Inactive"
                    labels.append(status)
                    data.append(item["count"])

                return {
                    "title": _("Campaign Activity Status"),
                    "type": "column",
                    "data": {
                        "labels": labels,
                        "data": data,
                        "labelField": "Activity",
                    },
                }

    except Exception as e:
        logger.warning("Error creating campaign chart: %s", e)

    return None


def campaign_table_func(generator, model_info):
    """Generate table context for all campaigns."""
    return generator.build_table_context(
        model_info=model_info,
        title=_("Campaigns"),
        filter_kwargs={},
        no_found_img="assets/img/not-found-list.svg",
        no_record_msg=_("No campaigns found."),
        view_id="campaigns_dashboard_list",
    )


DefaultDashboardGenerator.extra_models.append(
    {
        "model": Campaign,
        "name": _("Campaigns"),
        "icon": "fa-bullhorn",
        "color": "orange",
        "include_kpi": True,
        "chart_func": create_campaign_charts,
        "table_func": campaign_table_func,
        "table_fields_func": campaign_table_fields,
    }
)
