"""
Version and metadata for the horilla.contrib.dashboard app.

Contains the module's version string and descriptive metadata used in the
application registry and UI.
"""

# First party imports (Horilla)
from horilla.utils.translation import gettext_lazy as _

__version__ = "1.11.6"
__module_name__ = "Dashboards"
__release_date__ = ""
__description__ = _("Module for building and customizing interactive dashboards.")
__icon__ = "assets/icons/icon6.svg"

__1_11_6__ = _(
    "Derive list column labels from model verbose_name; mark empty-state no_record_msg "
    "strings for translation; stop forcing form labels to title case; wrap remaining "
    "strings with gettext; add indexes on frequently filtered fields."
)

__1_11_5__ = _(
    "RTL-aware widget reordering on home and dashboard detail. Translate default "
    "KPI and chart titles."
)

__1_11_4__ = _(
    "Store relative referer URLs and fall back to full navigation from dashboard views. "
    "Use the theme primary color for the home dashboard record-count label."
)

__1_11_3__ = _(
    "Handle missing component safely when moving a widget to another dashboard."
)

__1_11_2__ = _(
    "Re-raise HttpNotFound with exception chaining in dashboard detail views to "
    "preserve context."
)

__1_11_1__ = _(
    "Removed redundant fields attributes superseded by form_class on dashboard action "
    "views, and added admin and component view docstrings for pylint compliance."
)

__1_10_1__ = _(
    "Dashboard forms aligned with HorillaModelForm layout: field_order and "
    'Meta.fields = "__all__" with Meta.exclude; component form __init__ unchanged.'
)

__1_10_0__ = _(
    "Release 1.10: dashboards ship under contrib with app label dashboard. "
    "Widget and KPI wiring aligned to short app labels across contrib modules "
    "so filters and lookups resolve consistently."
)

__1_5_0__ = _(
    "Extended dashboard generator to support multiple charts, multiple table "
    "widgets, and custom KPI functions. Added more KPI widgets and improved "
    "charts and reporting components for the dashboard."
)

__1_4_0__ = _(
    "Added configurable Y-axis metrics for charts reusing KPI options, plus new "
    "chart types: Area, Tree Map, Heat Map, Radar, Sankey, and Scatter."
)

__1_3_0__ = _(
    "Added advanced visualization capabilities including multi-series charts, "
    "improved stacked chart rendering, interactive chart previews in dashboard "
    "editor, and enhanced analytics widgets for deeper insights."
)

__1_2_0__ = _(
    "Migrated from Django AppConfig to Horilla AppLauncher and and replaced Django utilities"
    "with horilla.utils.decorators, horilla.utils.translation, and horilla.shortcuts where applicable."
)

__1_1_0__ = _(
    "Added drag and drop reordering from home page, date range filter,"
    "and set to default options for enhanced dashboard customization and data visualization."
)
