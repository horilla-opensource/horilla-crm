"""Dashboard utilities for contacts module."""

# First party imports (Horilla)
from horilla.contrib.dashboard.utils import DefaultDashboardGenerator
from horilla.utils.choices import TABLE_FALLBACK_FIELD_TYPES
from horilla.utils.translation import gettext_lazy as _

# Local imports
from .models import Contact


def contact_table_fields(model_class):
    """Return list of {name, verbose_name} for contact table columns."""

    priority = ["title", "first_name", "email", "contact_source"]
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


def contact_table_func(generator, model_info):
    """Generate table context for all contacts."""
    return generator.build_table_context(
        model_info=model_info,
        title=_("Contacts"),
        filter_kwargs={},
        no_found_img="assets/img/not-found-list.svg",
        no_record_msg=_("No contacts found."),
        view_id="contacts_dashboard_list",
    )


DefaultDashboardGenerator.extra_models.append(
    {
        "model": Contact,
        "name": _("Contacts"),
        "icon": "fa-address-book",
        "color": "green",
        "include_kpi": True,
        "table_func": contact_table_func,
        "table_fields_func": contact_table_fields,
    }
)
