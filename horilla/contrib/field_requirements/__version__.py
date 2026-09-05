"""
Version information for the field requirements app.
"""

# First party imports (Horilla)
from horilla.utils.translation import gettext_lazy as _

__version__ = "1.0.1"
__module_name__ = "Field Requirements"
__release_date__ = ""
__description__ = _(
    "Configure which fields are required or optional on opted-in models, per company."
)
__icon__ = ""

__1_0_1__ = _(
    "Stop forcing verbose names into title case on forms and models. Drop the bundled "
    "initial migration so the app ships migration-free with the current registry."
)

__1_0_0__ = _(
    "Register field requirements as a self-contained contrib feature. Lead and "
    "Opportunity opt in through the feature registry; models that cannot store "
    "an empty value cannot be relaxed. Per-company FieldRequirement rows "
    "resolve through get_field_requirements_for_model. Admins configure "
    "overrides on a dedicated settings page. Opted-in create and edit forms "
    "pick up those overrides through FormExtension discovery."
)
