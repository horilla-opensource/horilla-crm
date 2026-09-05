"""
Version information for the Process Builder
"""

# First party imports (Horilla)
from horilla.utils.translation import gettext_lazy as _

__version__ = "1.11.7"
__module_name__ = "Process Builder"
__release_date__ = ""
__description__ = _(
    "Module for managing the process, including approval processes and review processes."
)
__icon__ = "assets/icons/process-management.svg"

__1_11_7__ = _(
    "Use the shared is_active toggle column partial for approvals and reviews. Derive "
    "list/detail column labels from model verbose_name; add missing verbose_name on "
    "approval fields; stop forcing labels to title case; indexes on frequently filtered "
    "fields."
)

__1_11_6__ = _(
    "Apply runtime viewport fit on approval/review process lists and approval job/"
    "history detail screens."
)

__1_11_5__ = _(
    "Reviews: cap review process form modal body height with max-h so short forms no "
    "longer reserve a fixed 500px empty area."
)

__1_11_4__ = _(
    "Approvals: scope delegation to ApprovalInstance.delegated_approver instead of mutating "
    "shared process rules; replace alert()-based responses with messages.error and HTMX "
    "reload; register ApprovalInstance for export_data. Wrap approval form placeholders "
    "with gettext_lazy."
)

__1_11_3__ = _(
    "Re-raise HttpNotFound with exception chaining in process detail views to "
    "preserve context."
)

__1_11_2__ = _(
    "Approvals: fixed type mismatch when excluding pending approval objects from list "
    "view; added job detail body template and adjusted tab container height."
)

__1_11_1__ = _(
    'ApprovalRuleForm refactored to fields="__all__" with field_order, dropping the '
    "unused process_config field and the redundant view fields list. Fixed a KeyError on "
    "review-process create by adding keep_on_form for is_active. Migrated signal imports "
    "to the db.models.signals shim and added docstrings for pylint compliance."
)

__1_10_0__ = _(
    "Release 1.10: Process Builder consolidated under contrib.process with approvals "
    "and reviews sub-apps. Django app labels for approvals and reviews are unchanged; "
    "import paths and includes now use the contrib package layout."
)

__1_1_0__ = _(
    "Enhanced approval workflow with delete support in approval history, "
    "standard HTMX modal delete flow, and inline edit enforcement for "
    "pending/rejected records. Improved approval signals cleanup, "
    "review process table viewport handling, and redirect behavior."
)

__1_0_0__ = _(
    "Introduced unified Process Builder combining reviews and approvals "
    "into a flexible, condition-driven workflow engine with configurable "
    "approvers, field-level controls, and per-app process configuration."
)
