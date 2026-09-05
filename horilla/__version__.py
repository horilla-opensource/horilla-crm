"""Module containing package metadata used by Horilla (version, name, icons)."""

from django.utils.translation import gettext_lazy as _

__version__ = "1.13.8"
__module_name__ = _("Core System")
__release_date__ = ""
__description__ = _(
    "Core system providing authentication, configuration, utilities, and platform-level services."
)
__icon__ = "assets/icons/logo.png"

__1_13_8__ = _(
    "Generics: granted (non-owner) record access across list, detail, kanban, search, and "
    "bulk flows; derive list/detail column labels from model verbose_name without extra DB "
    "fetches; shared empty_state and activate_company partials; my_settings_list_shell for "
    "My Settings lists; shared is_active toggle column; stop forcing verbose names to title "
    "case; quieter generic history/audit display with model names and safer non-date diffs; "
    "related-list header restyle; wrap long note text; cursor-pointer on more clickable "
    "controls. Core: cache available companies in the context processor; stream export "
    "generation; indexes on frequently filtered fields; register Field Requirements in "
    "INSTALLED_APPS. UI: reposition overflowing Summernote toolbar dropdowns; history and "
    "layout CSS tweaks."
)

__1_13_7__ = _(
    "Generics: stretch list columns on wide viewports; collapsible day-accordion history tab "
    "with cleaned rich-text and long values in diffs; Add button on empty-state list views; "
    "fix column sort in tab and related-list fragments; show and edit state as subdivision "
    "name not code; fix drag-handle visibility on permissioned columns. Core: shared "
    "settings_list_shell for settings list pages; Initialize Database Go To Home with "
    "default lead and opportunity stages via initialize_database_go_home; view-driven company "
    "and branch detail fields; normalize Title Case verbose_name labels; exclude extension "
    "model classes from permission listings; fix Role init Next Step button wrap; "
    "horilla.views.generic View/FormView/ListView/DetailView re-exports; f-strings in "
    "get_object_or_404. UI: dark-mode contrast fixes in history and detail surfaces; keep "
    "multi-select dropdowns open after selection; djangofmt on shared layout and template "
    "partials."
)

__1_13_6__ = _(
    "Generics: nested multi-level group-by with lazy-loaded subtrees; distinguish empty "
    "list vs no filter matches; restore empty groups, company-scope FK groups, and Group By "
    "Settings; reuse list empty-state markup in chart/split views; restrict quick filters to "
    "plain list layout; viewport-fit list and detail tables; open-in-new-tab only for "
    "previewable attachments; delete-modal Cancel contrast; navbar second_button font size. "
    "Core: Horilla DetailView wrapper and package re-export; TemplateView fieldsets for My "
    "Profile; settings fieldsets via shared includes; user number_format drives currency/"
    "number display; gate Regional Formatting behind can_change_profile; company-scope User "
    "Kanban/Group-By; avoid N+1 in permission utils and role hierarchy; scope import/export "
    "and settings-search spinners; stepper theming and Excel sample-data fixes; demo user "
    "departments; SHORT_TO_DAY_PREFIX in BusinessHourForm. UI: full-page Connection Lost on "
    "HTMX sendError / ERR_CONNECTION_REFUSED with Retry; runtime viewport fit for settings "
    "lists; center read-only field lock icon. I18N: Persian catalog expansion with bulk-update "
    "and RTL breadcrumb fixes."
)

__1_13_5__ = _(
    "Extension: DateTimeFormatter with _inherit_formatter; _inherit_view composition "
    "for View/ListView (including EditFieldView); FormView applies _inherit_form; "
    "fieldsets_insert on _inherit_detail; form fieldsets merge so extensions can "
    "inject fields. Generics: parse edit/list/bulk dates through DateTimeFormatter; "
    "preserve image uploads across single-step validation errors; scope list-view "
    "navigation session keys per model with opt-out; populate Available Fields for "
    "mixed-column views; list-cell-border CSS classes; user detail sections driven "
    "by HorillaDetailView fieldsets. Core: demo fixtures for contrib and CRM apps "
    "(batched password derivation, roles, country-coded phones); AuditlogMiddleware; "
    "Add Column to List on branches; regional formatting rendered from form fieldsets; "
    "shared accent-color default for color inputs; rename Update to Edit; remove "
    "settings-search spinner; fix duplicate Core System version card and Export Data "
    "after Esc or HTMX tab navigation. API: enforce HorillaModelPermissions on "
    "main-table endpoints. UI: RTL foundation and main-shell mirroring."
)

__1_13_4__ = _(
    "Generics: multi-select choice and foreign-key filters; permission-gated user chips for "
    "User FK fields (without leaking raw HTML into the details tab); live avatar preview on "
    "image fields; navbar descriptions; prioritize the full-detail action; deny bulk update "
    "and hard-delete when the user lacks change/delete permission; refine navbar, tab, and "
    "settings layouts. Utils: add horilla.utils.html, text, and functional shims. API: move "
    "shared docs, mixins, and permissions to horilla.api. Core: require permission before "
    "toggling cross-company visibility; prefer profile image in get_avatar; store relative "
    "referer URLs with full-nav fallback; extract template BUILTINS and LOADERS. UI: "
    "mask-image nav/sidebar icons and restore theme-colored hover states in dark mode. "
    "Added Persian (fa) language support."
)

__1_13_3__ = _(
    "Generics: AND/OR logic between filter rows; default new-record time zone to the user's "
    "zone; CheckboxGridSelect for weekday/multi-option grids; stop hidden multi-step fields "
    "from reappearing on other steps; cap form modal body height with max-h instead of fixed "
    "h-[500px]. Settings: content search over the Settings sidebar; fiscal year modal body "
    "can shrink below its max height; Business Hour per-day times grouped into day cards. "
    "UI: move header notification/theme script into global.js; stop Select2 multi-select "
    "clipping of wrapped choices; realign viewport-height offsets with the 60px header."
)

__1_13_2__ = _(
    "Export: added export/export_own permissions with optional column selection for one-off and "
    "scheduled exports, plus get_export_queryset and is_exportable_field helpers used by core, "
    "bulk, list, and report export paths. Generics: relative date filter operators (Today, "
    "Yesterday, This Week, This Month); PhoneField validation; inline edit validation errors; "
    "preserve export modal content on Escape; keep MultiWidget structure on hidden multi-step "
    "fields; replace delete-view alert() with the message framework; fix related-list "
    "no-else-continue; update split-view detail tab width. UI: compact header to 60px with "
    "refined search and action buttons; replace dots.svg menus with consistent SVG icons. "
    "Core: wrap form placeholders with gettext_lazy."
)

__1_13_1__ = _(
    "Added ScriptResponse and HxTriggerResponse for shared HTMX modal, reload, and "
    "htmx.trigger script returns. Generics: show a loading spinner on the Save & New button. "
    "Core: guard missing model on field-permission save, validate recycle-bin retention days, "
    "and return 405 for POST on fiscal-year HTMX field endpoints."
)

__1_13_0__ = _(
    "Registered the Calls app in INSTALLED_APPS and wired calls WebSocket routes into ASGI. "
    "Generics: inline edit supports phone fields with the country-code widget. "
    "Trusted X-Forwarded-Proto and X-Forwarded-Host so request.is_secure() and "
    "build_absolute_uri() work behind reverse proxies and dev tunnels."
)

__1_12_4__ = _(
    "Core: added get_allowed_user_ids() for subordinate-aware ownership and fixed "
    "sync_role_permissions_on_role_change to assign role permissions to new users via "
    "transaction.on_commit. Generics: unified record-level access with check_record_access(), "
    "check_record_change_access(), and check_record_delete_access(); extended view_own "
    "filtering to global search, detail tabs, mail compose and drafts, notes and attachments, "
    "related lists, and activity sections. Parent-record change and delete access now gates tab "
    "actions, add buttons, and col_attr row links; callable action labels, icons, and hidden_if "
    "supported in render_action_button. HorillaModelForm skips ownership filtering when the user "
    "has global view permission. Fixed HorillaSingleDeleteView model resolution, "
    "ColumnSelectionForm self.data access, sanitize_html font-colour passthrough, and "
    "related-list add-column permission and URL handling."
)

__1_12_3__ = _(
    "Redesigned sidebar to a fixed-width icon-nav with text labels and corrected the "
    "sub-sidebar toggle button position when collapsed. Extension framework: renamed "
    "model _inherit to _inherit_model across metaclass, registry, and migration ops. "
    "Core: auto-sync user permissions when a role changes via signals; filter "
    "allowed_users by active company in OwnerQuerysetMixin. Generics: fixed Add Column "
    "to List in tabbed list views."
)

__1_12_2__ = _(
    "Added IP-based brute-force lockout on login and uniform forgot-password responses to "
    "prevent user enumeration. Fixed local settings to apply after app extensions. "
    "Generics: fixed filter-panel toggle in tabbed views with duplicate element IDs; "
    "sanitized notes-and-attachments fields against XSS and updated delete-button styling "
    "with themed icons. Menu: improved sub-sidebar active-link detection and unique item IDs."
)

__1_12_1__ = _(
    "Extension tests now use contrib.core examples instead of CRM-specific modules. Added "
    "centralized sanitize_html and sanitize_plain_text helpers with bleach CSS allowlisting, "
    "Summernote DOMPurify mirroring, CSV/XLSX cell sanitization against formula injection, "
    "and notification template XSS sanitization with validation-error field clearing. Fixed "
    "generics Select2 edit-mode FK filtering by loading parent instances via all_objects and "
    "scoping request.active_company to the record tenant; fixed navbar search losing focus by "
    "removing hx-select-oob/hx-preserve. Core: restricted login history to the current user, "
    "improved role empty state, refined User and RegionalFormatting forms, showed company on "
    "ChangeUserCompanyForm, debounced saveActiveTab for SQLite, and rendered readable user-agent "
    "details in login history. Registered static, i18n, and horilla_tags as template builtins."
)

__1_12_0__ = _(
    "Expanded extension framework with _inherit_form, _inherit_list, _inherit_card, "
    "_inherit_filter, _inherit_nav, _inherit_kanban, and _inherit_detail composition with "
    "caching and per-request resolution. Introduced PhoneWidget and PhoneField for "
    "international phone numbers. Fixed generics bulk-delete Prefetch slicing, action button "
    "text wrapping, and HolidayForm user-selection defaults. Centralized horilla.db "
    "transaction and connection imports and standardized first-party import groups."
)

__1_11_1__ = _(
    "Custom CSRF failure view and csrf_failure.html for DEBUG=False. CSRF protection "
    "restored on state-mutating stage and calendar-preference views. FiscalYear, "
    'RegionalFormatting, Company, and User forms switched to fields="__all__" with '
    "field_order and keep_on_form so HorillaModelForm base fields are no longer dropped, "
    "with sensitive user fields excluded. Business Hour add-button hides without reload, "
    "and BusinessHourHolidayModalView is guarded for deleted records. Generics skip M2M "
    "relations in bulk-delete to avoid ProtectedError and add cursor-pointer to note, "
    "attachment, and related-list actions. Added horilla.utils.timezone and "
    "horilla.db.models.signals shims, standardized first-party import groups, and broad "
    "docstring coverage for pylint compliance."
)

__1_11_0__ = _(
    "Workflow automation engine (rules, conditions, actions, Celery time triggers, "
    "execution history). Public booking platform with slots, public pages, reminders, "
    "and booking/activity integration. ERP-style _inherit model extensions with "
    "InjectField and extension-owned migrations. ShiftHour scheduling and BusinessHour "
    "enhancements with holiday support. HTMX-first UX, multi-step form refactors, "
    "django-countries subdivisions, permission inheritance fixes, activity/booking mail "
    "templates, and Django 6.0 generics stability improvements."
)

__1_10_1__ = _(
    "Meeting Integration contrib app (Zoom/Teams OAuth, meeting links, activity hooks). "
    "Generics export and JSONField display improvements. My Profile panel scrolls within "
    "a fixed viewport. Calendar Google settings respect active company on POST. "
    "Scheduled automations use corrected Celery task paths."
)

__1_10_0__ = _(
    "Major platform 1.10 layout: support apps consolidated under the contrib namespace with "
    "short Django app labels (activity, core, mail, theme, and related modules). "
    "AppLauncher configs, imports, URL namespaces, static paths, and permission "
    "or content-type strings updated to match the new labels. "
    "Added sync tooling to align migration records, content types, audit "
    "log references, and related data when upgrading existing databases."
)


__1_9_0__ = _(
    "Added Google Calendar integration with sync, service, and settings support. "
    "Implemented cadence signals for runtime activities. Centralized HorillaView "
    "layout resolution with get_layout_url() for backend-driven layout selection."
)


__1_8_1__ = _(
    "Switched Channels backend from InMemoryChannelLayer to RedisChannelLayer. "
    "Moved Holiday model to dedicated holidays.py. Improved branch list layout, "
    "business hour and holiday bulk select, and viewport-based table heights. "
    "Added SECURITY.md documentation."
)


__1_8_0__ = _(
    "Introduced unified Process Builder system combining reviews and approvals. "
    "Added async notification and mail handling with background thread execution. "
    "Improved health check endpoint and version changelog modal system. "
    "Updated assign_first_company_to_all_users signal to use User model directly."
)


__1_7_0__ = _(
    "Strengthened core validation with strict enforcement of include_models during "
    "feature registration, validation of subsection-to-section mappings, and export "
    "of StreamingHttpResponse via Horilla HTTP utilities."
)


__1_6_0__ = _(
    "Added health check endpoint, synced fiscal year and period logic, "
    "improved version changelog modal system, and switched Django Channels "
    "backend to Redis for better performance and reliability."
)


__1_5_0__ = _(
    "Improved global search model registry loading, standardized error handling "
    "with dedicated 403, 404, 405, and 500 templates, strengthened authentication "
    "flow using Django authenticate(), and applied multiple security and "
    "stability improvements across internal views."
)


__1_4_0__ = _(
    "Introduced the Horilla AppLauncher system for dynamic application "
    "registration. Added horilla.shortcuts, horilla.urls, and horilla.utils "
    "utilities. Refactored project URL handling and improved internal "
    "framework architecture for modular applications."
)


__1_2_0__ = _(
    "Improved system configuration handling, strengthened dashboard layout "
    "validation, enhanced filter processing reliability, and added multiple "
    "defensive validation improvements across core components."
)


__1_1_0__ = _(
    "Added an 'All Companies' option to the company dropdown, allowing users "
    "to view data irrespective of company selection."
)
