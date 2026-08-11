"""
Feature registration for Horilla Core app.
"""

# First party imports (Horilla)
from horilla.auth.models import User
from horilla.registry.asset_registry import register_html
from horilla.registry.feature import register_feature, register_models_for_feature

register_html(
    "inject_html/rtl_assets.html",
    slot="head_end",
    priority=90,
)

register_html(
    "inject_html/rtl_assets.html",
    slot="head_end",
    priority=90,
    page="login",
)

register_html(
    "inject_html/jalali_assets.html",
    slot="body_end",
    priority=85,
)

register_html(
    "inject_html/jalali_assets.html",
    slot="body_end",
    priority=85,
    page="login",
)

# Local imports
from .models import Company, Department, Role

register_models_for_feature(
    models=[
        Company,
        Department,
        Role,
        User,
    ],
    all=True,
    exclude=["dashboard_component", "report_choices"],
)


register_feature(
    "template_reverse",
    "template_reverse_models",
)
