"""CRM module version information."""

from horilla.utils.translation import gettext_lazy as _

__version__ = "1.11.14"
__module_name__ = "CRM"
__release_date__ = ""
__description__ = _("CRM module for managing leads, contacts, and opportunities.")
__icon__ = "assets/icons/icon2.svg"

__1_11_14__ = _(
    "Opportunities: grant team members access via opportunity_access; use "
    "my_settings_list_shell for Team Selling; simplify detail field configuration; fix "
    'split modal width and remove-row for new splits; remove invalid ForeignKey default=""; '
    "shared empty_state and is_active toggle partials. Leads: company-scope custom stage "
    "save/create; Field Requirements registration; assignment-rule and stage column labels "
    "from verbose_name. Forecast: full list view on opportunity pagination; speed period "
    "matching by grouping by owner; empty-state gates; DB indexes. Campaigns/Contacts: "
    "ForeignKey default cleanup, indexes, and gettext on remaining strings. Scoring rules: "
    "shared is_active and empty_state markup."
)

__1_11_13__ = _(
    "Initialize Database: centralize DEFAULT_LEAD_INIT_STAGES and "
    "DEFAULT_OPPORTUNITY_INIT_STAGES; seed stages on Go To Home. Leads: show saved "
    "web-to-lead capture form; preserve legacy state values against subdivision codes; "
    "correct demo fixture regions. Opportunities: big-deal alert empty-state illustration. "
    "Forecast: fix period filter and viewport-fit layout. Campaigns: group default ROI "
    "report by type with sums. Scoring rules: remove navbar reload option."
)

__1_11_12__ = _(
    "Opportunities: auto-calculate Probability from the selected Stage; keep Opportunity "
    "Splits consistent with Team Selling. Forecast: avoid N+1 when computing closed-deals "
    "count. Cadence tab decoupled into the cadences extension. Persian i18n plus bulk-update "
    "and breadcrumb fixes on CRM screens."
)

__1_11_11__ = _(
    "Restore list-view table cell borders and sticky column alignment. Drop the "
    "per-page color-picker script from the lead form builder in favor of the shared "
    "accent-color default. Translate child-account and child-contact removal confirms. "
    "Opportunity name fields use example placeholders."
)

__1_11_10__ = _(
    "Forecast: correct trend formatting and period aggregation; fix navbar stacking above "
    "the sidebar. Opportunities: recognize DRF requests when resolving the team-selling "
    "company. Prioritize the Duplicate list action across accounts, contacts, campaigns, "
    "leads, and opportunities. Seed default CRM reports for accounts, campaigns, leads, "
    "and opportunities."
)

__1_11_9__ = _(
    "Accounts and Contacts: rename phone fields to contact_number (and related secondary/"
    "assistant contact_number fields), updating models, forms, API serializers, list/"
    "kanban/card/detail columns, lead conversion, and convert-success modal. Weekday "
    "selection uses the shared checkbox-grid widget instead of Select2 pills."
)

__1_11_8__ = _(
    "Wrap lead and forecast form placeholders with gettext_lazy. Opportunities approval "
    "detail sections now use messages.error with HTMX reload instead of window.alert. "
    "Normalized lead, contact, and account fixture phone numbers to international format."
)

__1_11_7__ = _(
    "Auto-convert leads when is_convert flips true outside the manual conversion view. "
    "Migrated modal and HTMX trigger script returns to ScriptResponse and HxTriggerResponse."
)

__1_11_6__ = _(
    "Registered Account, Contact, and Lead as callable models for Calls Click-to-Call "
    "(account_number, phone, and contact_number fields)."
)

__1_11_5__ = _(
    "Accounts: corrected lead_source choice key from social media to social_media. "
    "Replaced direct owner checks with subordinate-aware get_allowed_user_ids() filtering "
    "across accounts, contacts, leads, and opportunities related lists and campaign actions. "
    "Moved CRM form permission guards from get() to has_permission() with "
    "check_record_change_access and check_record_delete_access on parent records. "
    "Hierarchy modals now traverse to the root ancestor and highlight the active node for "
    "campaigns, accounts, and contacts. Added circular parent-child validation on Contact, "
    "Account, and Campaign. Forecast: fixed cached_property misuse in type-tab views. "
    "Fixed account hierarchy view_own permission check."
)

__1_11_4__ = _(
    "Contacts: initialize account before conditional relation lookup on model save. "
    "Forecast: avoid constant-test checks when reading cached company access in "
    "forecast-type tab views."
)

__1_11_3__ = _(
    "Forecast: excluded currency and current_amount from ForecastTargetForm; fixed "
    "active-tab detection and wrapped opportunity-type labels with i18n; refactored "
    "forecast-type table period-cell layout and sticky-column sizing; reduced N+1 "
    "queries and cached repeated fiscal-year checks. Normalized contact fixture country "
    "values to ISO 3166-1 alpha-2 codes."
)

__1_11_2__ = _(
    "Refactored leads core views into tab sub-packages and opportunities split and stages "
    "views into sub-packages. Standardized first-party import section headers and migrated "
    "transaction imports to horilla.db. Leads: fixed Go to Leads navigation from convert "
    "success modal; enhanced web-to-lead form with Select2 and improved styling. "
    "Opportunities: fixed team selling and split checks via _resolve_company and all_objects "
    "OpportunitySettings lookups; scoped OpportunityTeamForm user choices to active company."
)

__1_11_1__ = _(
    "Lead and opportunity stage saving now validates first and uses update-or-create "
    "instead of delete-and-recreate, so stages still referenced by leads or opportunities "
    "are no longer deleted (preventing ProtectedError on the PROTECT FKs). CSRF protection "
    "restored on stage-group and custom-stage views with csrf_token added to the HTMX "
    "forms. Fixed KeyError on multi-step create forms by removing direct created_by / "
    "updated_by access stripped by HorillaMultiStepForm. Removed redundant fields "
    "attributes superseded by form_class on forecast, assignment-rule, opportunity-team, "
    "and scoring-rule single-form views, plus docstring coverage for pylint compliance."
)

__1_10_0__ = _(
    "Aligned with platform 1.10: imports and integrations target contrib packages "
    "and short Django app labels (core, generics, mail, activity, and other shared modules). "
    "URL namespaces, static paths, permission strings, and ForeignKey string references "
    "updated where they cross into contrib apps; the CRM module keeps its original app label "
    "and database table prefix."
)

__1_4_0__ = _(
    "Enhanced CRM fixtures with additional fields. Improved UI refinements "
    "including navbar z-index fixes, KPI color consistency, and standardized "
    "template formatting across leads, accounts, campaigns, contacts, "
    "and opportunities modules."
)

__1_3_0__ = _(
    "Introduced advanced CRM visualization capabilities including chart views, "
    "timeline (Gantt-style) views, split layout navigation, and card-based record "
    "views. Improved pipeline data exploration and navigation across Leads, "
    "Accounts, Campaigns, Contacts, and Opportunities."
)

__1_2_0__ = _(
    "Enabled advanced quick filters, improved column selector behavior, "
    "refined CRM list view consistency, and enhanced filtering reliability "
    "across Leads, Accounts, Contacts, Campaigns, and Opportunities."
)

__1_1_0__ = _(
    "Migrated CRM sub-apps to Horilla AppLauncher and replaced Django utilities "
    "with horilla.utils.decorators, horilla.utils.translation, and horilla.shortcuts "
    "where applicable."
)
