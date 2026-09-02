# Horilla Generics app — deep dive (`horilla.contrib.generics`)

The **generics** app is the Horilla platform’s **class-based view (CBV) framework**: list/kanban/card/detail/timeline/chart views, filter panels, single/multi-step forms, Select2 endpoints, and template tags that glue HTMX + Tailwind + permission checks.

---

## App startup (`apps.py`)

`GenericsConfig`:

| Setting | Value |
|---------|--------|
| `name` | `horilla.contrib.generics` |
| `label` | `generics` |
| `url_prefix` | `generics/` |
| `url_namespace` | `generics` |
| `auto_import_modules` | **`signals`** only |

There is **no `menu.py`** here—generics is infrastructure, not a user-facing module in the sidebar.

Signals typically wire universal behaviors (audit helpers, cache invalidation—read `signals.py`).

---

## Architectural layers

### Views (`horilla.contrib.generics.views`)

| Layer | Responsibility |
|-------|----------------|
| `HorillaView` | Base shell integration; use with [settings list shell](../core/settings_list_shell.md) (`settings_list_shell.html` or `my_settings_list_shell.html`) for Settings list pages. |
| `HorillaListView`, `HorillaKanbanView`, `HorillaCardView` | Data tables, boards, card grids with export + bulk actions. |
| `HorillaDetailView`, `HorillaDetailTabView`, `HorillaSplitView` | Record detail, tabs, master/detail panes. |
| `HorillaSingleFormView`, `HorillaMultiFormView` | Create/update flows; targeted by **duplicates** `inject.py`. |
| `HorillaChartView`, `HorillaTimelineView`, `HorillaGroupByView` | Analytics visualizations. |
| `helpers/*` | Column builders, edit-field widgets, filter list, Select2, timeline settings. |
| `toolkit/*` | Bulk delete/update/export, form mixin builders. |

Entry index: [views/views_init.md](views/views_init.md).

### Forms (`horilla.contrib.generics.forms`)

- `HorillaModelForm`, `HorillaMultiStepForm`, condition fields, field-permission mixin.
- `HorillaModelForm.get_fieldsets()` for template-driven fieldset rendering (extensions use `fieldsets_insert`).
- Start here: [forms/forms_init.md](forms/forms_init.md).

### Formatting (`horilla.contrib.generics.formatting`)

- `DateTimeFormatter` — Gregorian **format and parse**; composed via [`_inherit_formatter`](../../extension/formatting/inherit.md).
- Details: [formatting/datetime.md](formatting/datetime.md).

### Filters

- `HorillaFilterSet` + `OwnerFiltersetMixin` patterns: [filters.md](filters.md).

### Template tags (`templatetags/horilla_tags`)

- Actions, permissions, navigation, assets, dates, history: [templatetags/horilla_tags/horilla_tag_init.md](templatetags/horilla_tags/horilla_tag_init.md).

### Methods (`methods.py`)

- Server-side helpers shared across views (pagination, export, HTMX fragment selection).

---

## URL surface

`generics/` routes expose:

- Generic CRUD/list endpoints used when apps reuse stock patterns.
- **Select2** JSON endpoints under paths like `/generics/{app}/{model}/select2/` (see `views/helpers/select2.md`).

Reverse names always use namespace **`generics:`**—confirm exact names in `horilla/contrib/generics/urls.py`.

---

## Extension resolution (`horilla.extension`)

List, detail, navbar, card, kanban, form, formatter, and view layers resolve **composed subclasses** at runtime when extension apps register `_inherit_*` specs:

| View / form | Resolution |
|-------------|------------|
| `HorillaListView.as_view()` | `resolve_list_view_class()` / `resolve_filterset_class()` |
| `HorillaDetailView.as_view()` | `resolve_detail_view_class()` |
| `HorillaNavView.as_view()` | `resolve_nav_view_class()` |
| `HorillaSingleFormView` / `HorillaMultiFormView` | `resolve_form_class()` in `get_form_class()` |
| `horilla.views.generic.FormView` | `resolve_form_class()` in `get_form_class()` ([generic.md](../../views/generic.md)) |
| `horilla.views.generic.View.as_view()` | `resolve_view_class()` ([view inherit](../../extension/view/inherit.md)) |
| Template date/time + list/bulk date parse | `get_datetime_formatter()` → composed `DateTimeFormatter` |

Target apps register URLs in `AppLauncher.ready()` before extension apps import `lists.py` / `details.py` / `navbars.py`; `bootstrap_extensions()` in `horilla/urls/project.py` composes all layers after `apps.ready`. See [../../extension/inherit.md](../../extension/inherit.md).

Platform code comments and tests use **core** examples (`UserFilter`, `UserFormSingle`, `UserListView`); CRM modules use the same APIs with `horilla_crm.*` targets.

---

## Monkey patches / cross-app integration

Other apps patch generics at import time:

- **`horilla.contrib.duplicates.inject`** wraps `form_valid`, `_prepare_detail_tabs`, and `UpdateFieldView.post`.
- **`horilla.contrib.cadences.inject`** wraps `_prepare_detail_tabs` to hide empty cadence tabs.

When debugging odd form behavior, inspect whether these patches applied (look for `_original_*` attributes on view classes).

---

## How to build a new screen (checklist)

1. Subclass the narrowest Horilla view (`HorillaListView`, …).
2. Set `model`, `filterset_class`, `form_class`, `template_name` (or rely on conventions).
3. Register URL under **your** app’s `urls.py` with `LoginRequiredMixin`.
4. Register model for features + permissions in **your** app’s `registration.py`.
5. Add menu item pointing at your named URL with `MAIN_CONTENT_HX_ATTRS` when embedding in shell.

---

## Documentation map (existing deep files)

- List / detail / kanban / chart / timeline: [views/](views/list.md)
- Toolkit (bulk ops): [views/toolkit/toolkit_init.md](views/toolkit/toolkit_init.md)
- Forms: [forms/](forms/generics.md)
- Date/time formatter: [formatting/datetime.md](formatting/datetime.md)
- Filters: [filters.md](filters.md)

---

## Related documentation

- Core permissions & models: [../core/core_app.md](../core/core_app.md)
- Duplicates integration: [../duplicates/duplicates.md](../duplicates/duplicates.md)
