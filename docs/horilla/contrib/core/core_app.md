# Horilla Core app — deep dive index (`horilla.contrib.core`)

The **core** app is the largest contrib module: authentication helpers, **multi-company tenancy**, **roles & permissions**, **menus**, **HorillaContentType**, **signals**, **middleware**, **demo data**, and **REST** surface for branches, currencies, users, etc.

This page is an **index and orientation**. Detailed topics live in focused files under `docs/horilla/contrib/core/`.

---

## App startup (`apps.py`)

`CoreConfig` (`AppLauncher`):

| Setting | Value |
|---------|--------|
| `name` | `horilla.contrib.core` |
| `label` | `core` |
| `verbose_name` | Core System |
| `url_prefix` | `""` (empty — routes mount at project root via include) |
| `url_module` | `horilla.contrib.core.urls` |
| `url_namespace` | `core` |
| `auto_import_modules` | `registration`, `signals`, **`scheduler`**, `login_history`, `menu` |
| `celery_schedule_module` | `celery_schedules` |
| `demo_data` | JSON packs: `company.json`, `role.json`, `users.json` with ordering metadata |

`get_api_paths()` exposes multiple `/`-prefixed API includes (read `apps.py` for the authoritative list).

---

## Middleware (high impact)

Registered from **`horilla.contrib.core.middlewares`** in project settings:

- **`TimezoneMiddleware`**, **`ActiveCompanyMiddleware`** — per-request active company + tz.
- **`HorillaExceptionMiddleware`** — maps **`HttpNotFound`** (`horilla.web`) to the custom 404 flow.
- **`Horilla405Middleware`** — when the view returns **405 Method Not Allowed**, renders **`templates/405.html`** (same card layout as other error pages).
- **`SVGSecurityMiddleware`**, **`HTMXRedirectMiddleware`**, **`EnsureSectionMiddleware`** — security + HTMX navigation polish.

Deep behavior belongs next to source; cross-check [settings `base.py`](../../settings/base.md) for middleware order and CSRF settings.

---

## Custom error pages (`templates/` + `views/error_pages.py`)

User-facing errors share **`templates/error.html`** (Tailwind card, dark-mode script). Child templates live at the project **`templates/`** root.

| Template | When it appears | HTTP status |
|----------|-----------------|-------------|
| **`403.html`** | Permission denied (views, decorators, includes with `embed=True`) | 403 |
| **`404.html`** | **`HttpNotFound`** / not found | 404 |
| **`405.html`** | **`Horilla405Middleware`** on disallowed HTTP method | 405 |
| **`csrf_failure.html`** | CSRF verification failed when **`DEBUG=False`** | 403 |

Settings-only embed variant: **`horilla/contrib/core/templates/error/settings_403.html`** (extends the same base).

### CSRF failure (`CSRF_FAILURE_VIEW`)

In **`horilla/settings/base.py`**:

```python
CSRF_FAILURE_VIEW = "horilla.contrib.core.views.error_pages.csrf_failure"
```

Implementation: **`horilla/contrib/core/views/error_pages.py`** → **`csrf_failure(request, reason="")`**.

| `DEBUG` | Behavior |
|---------|----------|
| **`True`** | Delegates to Django’s built-in CSRF failure view (yellow technical help page). |
| **`False`** | Renders **`csrf_failure.html`** with a short user message (`message` context). |

**HTMX POST:** returns **`HX-Redirect`** to `HX-Current-URL`, `Referer`, or `/` so the client reloads and picks up a fresh CSRF token.

**Configuration (common fix):** origin mismatches (e.g. `127.0.0.1` vs `localhost`) require the exact browser origin in **`CSRF_TRUSTED_ORIGINS`** (from `.env`). Example:

```env
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

### Permission 403 vs CSRF 403

Both may return HTTP **403**, but they are different paths:

- **Permission** — view renders **`403.html`** (or modal embed); user lacks access.
- **CSRF** — middleware aborts POST before the view; **`csrf_failure`** runs when **`DEBUG=False`**.

---

## Custom signals (`horilla.contrib.core.signals`)

Platform-wide hooks consumed by theme, currency, login, and installed apps, including:

- **`company_created`** — fired when a new `Company` is created; listeners initialize fiscal year, currency, etc.
- **`company_currency_changed`** — fired after default currency changes; listeners bulk-update `MoneyField` amounts (sent in a background thread so bulk updates do not block the HTTP response)
- **`initialize_database_go_home`** — fired when the init wizard exits early via **Go To Home** (after user + company exist); CRM listeners seed default lead and opportunity stages when none exist for the company. See [initialize_database.md](initialize_database.md).
- **`pre_logout_signal`**, **`pre_login_render_signal`** — theme/login customization
- Product-specific pipeline hooks (e.g. `lead_stage_created`, `opp_stage_created` in `horilla_crm`) connect in their own apps

Theme app listens to **`pre_logout_signal`** / **`pre_login_render_signal`**—see [../theme/theme.md](../theme/theme.md).

### Role-change permission sync (User model receivers)

Two `User` `pre_save` / `post_save` receivers work together to keep `user_permissions` in sync whenever a user's role is changed through any code path (admin, API, bulk update, etc.):

| Receiver | Signal | Behavior |
|----------|--------|----------|
| **`capture_user_old_role`** | `pre_save` | Snapshots `instance.role` onto `instance._previous_role` before the save, so the post-save handler can compare old vs. new role. No-ops for new users. |
| **`sync_role_permissions_on_role_change`** | `post_save` | Skips when `created=True` or when `old_role == new_role`. Otherwise, inside `transaction.on_commit`: removes permissions from the old role (preserving any `view_own_*` defaults), then adds all permissions from the new role. Errors are logged but do not abort the save. |

**Why `transaction.on_commit`?** The sync runs after the transaction commits, so it always reads the fully persisted role state and avoids acting on a partially-committed row.

**`view_own_*` preservation:** Permissions whose `codename` starts with `view_own_` are never removed during role cleanup, even if the old role held them, because they represent per-user defaults that exist independently of role assignment.

---

## Documentation map

| Topic | Doc |
|-------|-----|
| Initialize Database + Go To Home | [initialize_database.md](initialize_database.md) |
| Settings list shell (`#navBar` / `#mainSession`) | [settings_list_shell.md](settings_list_shell.md) |
| Shared empty-state partials (activate company, no-data) | [../../../templates/components/empty_state.md](../../../templates/components/empty_state.md) |
| Base models, `HorillaCoreModel`, managers, `HorillaContentType` | [models.md](models.md) |
| Custom `HorillaUser` | [user_model.md](user_model.md) |
| Menus (floating, main, settings, sub-section, my settings) | [Menu/](Menu/floating_menu.md) |
| Registry (features, permissions, assets, limiters) | [Registry/feature.md](Registry/feature.md) |
| URL helpers (`horilla.urls`) | [Urls/urls.md](Urls/urls.md) |
| Web utilities (`horilla.web`) | [web/web.md](../../web/web.md) |
| Decorators (legacy path name) | [Decorator ( Utils )/decorators.md](Decorator%20(%20Utils%20)/decorators.md) |
| Translation shim | [Translation (Utils )/translation.md](Translation%20(Utils%20)/translation.md) |
| Settings / `horilla_apps` / passwords / `CSRF_FAILURE_VIEW` | [settings `base.py`](../../settings/base.md) |
| Exceptions | [Core/exceptions.md](Core/exceptions.md) |
| Keyboard shortcuts registration (core vs keys) | [Shortcuts/shortcuts.md](Shortcuts/shortcuts.md) |
| Shift hours (`ShiftHour` model + form) | [models.md](models.md) · `horilla/contrib/core/forms/shift_hour.py` |
| Fiscal year settings views | [core_app.md — Fiscal year views](#fiscal-year-views-viewsfiscal_yearpy) · `horilla/contrib/core/views/fiscal_year.py` |

---

## Fiscal year views (`views/fiscal_year.py`)

Class-based views that manage company fiscal year configuration under Settings → Company → Fiscal Year.

| View | Base | HTTP methods | Purpose |
|------|------|--------------|---------|
| `CompanyFiscalYearTab` | `TemplateView` | GET | Fiscal year settings tab shell |
| `FiscalYearFormView` | `HorillaSingleFormView` | GET, POST | Create/update fiscal year configuration (`core:fiscal_year_form` / `_edit`) |
| `FiscalYearFieldsView` | `View` | **GET only** (`head`, `options`) | HTMX partial that re-renders dynamic form fields + preview (`core:fiscal_year_fields`) |
| `CalculateWeekStartDayView` | `View` | GET | Computes week-start day for custom fiscal year setups |
| `FiscalYearCalendarPreviewView` | `View` + mixin | **GET only** (`head`, `options`) | HTMX calendar preview while configuring (`core:fiscal_year_calendar_preview`) |
| `FiscalYearCalendarView` | `DetailView` + mixin | GET | Read-only calendar for an existing fiscal year instance |

### GET-only HTMX endpoints

Both dynamic partials are loaded with **`hx-get`** from `settings/fiscal_year_form.html` / related field templates. They build context from query params and do **not** save the model.

| View | URL name | Permission |
|------|----------|------------|
| `FiscalYearFieldsView` | `core:fiscal_year_fields` | `core.add_fiscalyear` **or** `core.change_fiscalyear` |
| `FiscalYearCalendarPreviewView` | `core:fiscal_year_calendar_preview` | `core.add_fiscalyear` **or** `core.change_fiscalyear` |

| Detail | Value |
|--------|--------|
| Decorator | `@htmx_required` on `dispatch` |
| Allowed methods | `get`, `head`, `options` (`http_method_names`) |
| Disallowed POST | Django returns **405 Method Not Allowed**; **`Horilla405Middleware`** may render `405.html` |

**Why not `FormView`?** Both views previously subclassed `FormView` without `form_class`. A POST then called `FormView.post()` → `get_form()` → `None()`, causing `TypeError: 'NoneType' object is not callable` (HTTP 500). They now subclass `View` and reject POST cleanly.

---

## Business hour views (`views/business_hour.py`)

Ten class-based views manage business hour configuration per company.

| View | Base | Purpose |
|------|------|---------|
| `BusinessHourView` | `View` | Shell template; guarded by `@permission_required` |
| `BusinessHourCardView` | `View` | Single company card summary partial |
| `BusinessHourFormView` | `HorillaSingleFormView` | Create/update business hours; blocks duplicate per company |
| `BusinessHourHolidayListView` | `HorillaListView` | Filtered list of holidays for a business hour config |
| `BusinessHourHolidayPanelView` | `View` | Holiday panel partial (HTMX target) |
| `BusinessHourHolidayToggleView` | `View` | HTMX POST — add or remove a holiday record; re-renders panel via `horilla.shortcuts.render` |
| `BusinessHourHolidayModalView` | `View` | Modal listing all holidays for selection |
| `BusinessHourAddHolidayView` | `HorillaSingleFormView` | Modal form to create a new holiday entry |
| `BusinessHourHolidayReadonlyDetailView` | `HolidayDetailView` | Read-only holiday detail opened from the business-hour holiday list (`core:business_hour_holiday_readonly_detail`); `actions = []` |
| `BusinessHourHolidayRemoveView` | `View` | Remove one holiday from a business hour config |

**Duplicate prevention** — `BusinessHourFormView.get()` checks for an existing `BusinessHour` for the active company before rendering; redirects if one exists rather than allowing creation of a second row.

**Performance** — views use `select_related()` / `prefetch_related()` for company and holiday relations to avoid N+1 queries on the card and list pages.

**HTMX return responses** — success handlers call `return_response` containing a script that reloads the detail view panel and shows a Django messages toast; cross-view reloads are orchestrated without full page refreshes.

---

## View and menu permission gates

### Login history (`views/user_login_history.py` + `menu.py`)

`UserLoginHistoryView` is guarded at dispatch level:

```python
@method_decorator(
    permission_required_or_denied(
        ["login_history.view_loginhistory", "login_history.view_own_loginhistory"]
    ),
    name="dispatch",
)
class UserLoginHistoryView(View): ...
```

The corresponding `LoginHistorySettings` My Settings menu entry declares `perm = ["login_history.view_loginhistory", "login_history.view_own_loginhistory"]` so the sidebar link is hidden for users who lack both permissions.

### Holidays (`views/user_holidays.py` + `menu.py`)

`UserHolidayView` is similarly guarded:

```python
@method_decorator(
    permission_required_or_denied(
        ["core.view_holiday", "core.view_own_holiday"]
    ),
    name="dispatch",
)
class UserHolidayView(View): ...
```

`UserHolidayListView.get_queryset` was also fixed: holders of either `view_holiday` **or** `view_own_holiday` now receive the same filtered queryset (user's own holidays plus all-users holidays), instead of the previous branch that silently excluded `view_holiday` holders from the filtered set.

The `HolidaySettings` My Settings menu entry declares `perm = ["core.view_holiday", "core.view_own_holiday"]` to keep menu visibility consistent with the view guard.

---

## Form queryset mixin (`mixins.py` — `OwnerQuerysetMixin`)

`OwnerQuerysetMixin` (defined in `horilla.contrib.core.mixins`) restricts FK / M2M `User` field choices on any `HorillaModelForm` based on the requesting user's permissions and active company.

### Permission-level queryset

| Condition | Queryset |
|-----------|----------|
| Superuser **or** holds `<app>.change_<model>` / `add_<model>` | All active users |
| Holds `<app>.change_own_<model>` / `add_own_<model>` | Requesting user + recursive subordinates (via `role.subroles`) |
| No matching permission | Requesting user only |

### Company scoping (added)

After the permission-level queryset is built, `OwnerQuerysetMixin` applies a company filter in this priority order:

1. **Edited object's company** — when `instance.pk` exists and the object has a `company` field.
2. **`request.active_company`** — set by `ActiveCompanyMiddleware`.
3. **`request.user.company`** — fallback to the user's own company.

If a company is resolved, `allowed_users = allowed_users.filter(company=company)` is applied, ensuring user-choice dropdowns never cross company boundaries regardless of the user's permission level.

Non-User relation fields whose related model has a `company` field are also filtered by the same resolved company.

---

## Shift hour form (`forms/shift_hour.py`)

**`ShiftHourForm`** (`HorillaModelForm`) — create/update named shifts (main hours + two optional breaks + assigned users).

| Pattern | Value |
|---------|--------|
| **`field_order`** | Full list through `assigned_users` (used by **`reorder_shift_hour_form_fields`**, not `Meta.fields`) |
| **`Meta.fields`** | `"__all__"` |
| **`keep_on_form`** | `("company",)` — field stays on form; **`ShiftHourFormView.hidden_fields`** still hides it in the UI |
| **Runtime** | `__init__` adds per-day break `TimeField`s, hides blocks by `timing_type` / `break*_mode`, HTMX reload on toggles |

See [generics single-step `HorillaModelForm`](../generics/forms/single_step.md) for automatic `HORILLA_FORM_EXCLUDE`.

---

## Regional formatting

**My Settings → Regional Formatting** (`ReginalFormatingView`, `core:regional_formating`).

Users set date/time/language/currency display preferences on their user record. The page is designed so calendar extension apps can add fields (for example a date system) without forking the template.

| Piece | Role |
|-------|------|
| `RegionalFormattingForm` | `HorillaModelForm` with `fieldsets` for Date Time Format, Language and Time Zone, Currency |
| `formating_view.html` | Loops `form.get_fieldsets()` instead of hard-coded `{{ form.date_format }}` |
| `ReginalFormatingView` | Subclasses [`horilla.views.generic.FormView`](../../views/generic.md) and instantiates via `get_form_class()` so `_inherit_form` applies |

To inject a field after `date_format`:

```python
class RegionalFormattingFormExtension(FormExtension):
    _inherit_form = "horilla.contrib.core.forms.base.RegionalFormattingForm"
    fieldsets_insert = [("date_format", "date_system")]

    class Meta:
        fields_append = ("date_system",)
```

Display of those preferences still goes through `DateTimeFormatter` ([`_inherit_formatter`](../../extension/formatting/inherit.md)).

---

## View-driven company and branch detail

Settings detail tabs avoid hard-coded field HTML. Labels come from model `verbose_name`; values use the shared display tag.

### Company details tab (`CompanyDetailsTab`)

| Piece | Role |
|-------|------|
| `body` | Tuple of `(field_name, icon_class)` on the view class |
| `get_context_data()` | Builds `detail_fields` as `(verbose_name, field_name, icon)` |
| `company_details_tab.html` | Loops `detail_fields`; renders with `{% display_field_value obj field %}` |

To add a field, append one tuple to `body` — no template edit required unless layout changes.

### Branch detail (`BranchDetailView`)

Uses **`HorillaDetailView`** with **`fieldsets`** and **`detail_fieldset.html`**:

```python
class BranchDetailView(LoginRequiredMixin, HorillaDetailView):
    template_name = "branches/branch_detail_view.html"
    model = Company
    fieldsets = (
        (_("Branch Information"), {"fields": ("name", "email", ...), "icon": "fas fa-building"}),
        (_("Address"), {"fields": ("city", "state", "country", "zip_code"), ...}),
        (_("Localization"), {"fields": ("time_zone", "language", "currency"), ...}),
    )
```

See [generics detail views — fieldsets](../generics/views/details.md#class-attributes-configuration).

---

## Typical extension tasks

1. **Add a new secured model** — extend `HorillaCoreModel`, add `CompanyFilteredManager`, set `OWNER_FIELDS` / `CURRENCY_FIELDS` as needed, then **`register_model_for_feature`** in your app’s `registration.py`.
2. **Add a settings screen** — `@settings_menu.register` class in your app’s `menu.py` mirroring [Menu/settings_menu.md](Menu/settings_menu.md) patterns.
3. **React to company currency change** — connect receiver to `company_currency_changed` in your `signals.py`.

---

## Related documentation

- Contrib umbrella README: [../README.md](../README.md)
- Cross-app utilities (thread local, queryset helpers): [../utils/utils.md](../utils/utils.md)
- DateTimeFormatter: [../generics/formatting/datetime.md](../generics/formatting/datetime.md)
- Form extensions: [../../extension/forms/inherit.md](../../extension/forms/inherit.md)
