# Horilla Generic Core Views (`horilla_generics/views/core.py`)

## 🎯 Purpose

`core.py` provides foundational reusable views used throughout Horilla generics:

- page shell view (`HorillaView`)
- HTMX tab container view (`HorillaTabView`)
- object history section with filtering + pagination (`HorillaHistorySectionView`)
- dynamic related-object creation modal (`HorillaDynamicCreateView`)

These are base building blocks that higher-level app views subclass.

---

## 📦 Classes in this file

1. `HorillaView(TemplateView)`
2. `HorillaTabView(TemplateView)` *(HTMX required)*
3. `HorillaHistorySectionView(DetailView)` *(HTMX required)*
4. `HorillaDynamicCreateView(FormView)` *(HTMX required + login required)*

---

## 🔁 `HorillaView`

### Purpose

Simple base page view that passes common navigation/layout URLs to templates.

### Important class attributes

| Attribute | Default |
|---|---|
| `template_name` | `"base.html"` |
| `nav_url` | `""` |
| `list_url` | `""` |
| `kanban_url` | `""` |
| `group_by_url` | `""` |
| `card_url` | `""` |
| `timeline_url` | `""` |
| `split_view_url` | `""` |
| `chart_url` | `""` |
| `view_id` | `""` | Optional root element id for settings shells |

### `get_layout_url()`

Returns the HTMX URL loaded into the main content area. Uses `?layout=` when set (`list`, `kanban`, `group_by`, …); otherwise falls back to `list_url` or the first configured alternate.

### Settings list pages

For **admin Settings** modules:

```python
template_name = "settings/settings_list_shell.html"
view_id = "my-settings-view"
nav_url = reverse_lazy("app:nav_view")
list_url = reverse_lazy("app:list_view")
```

For **My Settings** list pages (sidebar profile area):

```python
template_name = "settings/my_settings_list_shell.html"
```

See [settings list shell](../../core/settings_list_shell.md).

### `get_context_data()` output

Adds:
- `filter_form` only when `HX-Trigger == "filter-form"`
- `nav_url`, `layout_url`, `view_id`, and all layout URL attributes

### Example subclass

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from horilla.urls import reverse_lazy
from horilla_generics.views.core import HorillaView


class LeadView(LoginRequiredMixin, HorillaView):
    template_name = "base.html"
    nav_url = reverse_lazy("leads:leads_nav")
    list_url = reverse_lazy("leads:leads_list")
    kanban_url = reverse_lazy("leads:leads_kanban")
    group_by_url = reverse_lazy("leads:leads_group_by")
    card_url = reverse_lazy("leads:leads_card")
    timeline_url = reverse_lazy("leads:leads_timeline")
    split_view_url = reverse_lazy("leads:leads_split_view")
    chart_url = reverse_lazy("leads:leads_chart")
```

---

## 🧩 `HorillaTabView`

### Decorator

- `@htmx_required` on `dispatch`

### Purpose

Reusable HTMX tab renderer (`tab_view.html`) with persistent active tab support via `ActiveTab`.

### Important attributes

| Attribute | Default |
|---|---|
| `view_id` | `""` |
| `template_name` | `"tab_view.html"` |
| `tabs` | `[]` |
| `background_class` | `""` |
| `background_color` | `""` |
| `tab_class` | `""` |

### Behavior

- In `__init__`, it gets request from thread local (`_thread_local.request`) and sets `self.request`.
- `get_context_data()`:
  - loads saved active tab from `ActiveTab(created_by=user, path=request.path)`
  - sets `active_target` if found
  - passes tab style config + tabs list + view id

### Example `tabs` structure

```python
tabs = [
    {
        "title": "Overview",
        "url": "/leads/42/overview/",
        "target": "tab-overview-content",
        "id": "overview",
    },
    {
        "title": "Notes & Attachments",
        "url": "/leads/42/notes/",
        "target": "tab-notes-attachments-content",
        "id": "notes-attachments",
    },
]
```

---

## 🕘 `HorillaHistorySectionView`

### Decorator

- `@htmx_required` on `dispatch`

### Purpose

Render model history/audit timeline in `history_tab.html` with:
- grouping by date
- filter form (`HorillaHistoryForm`)
- pagination (`paginate_by = 10`)

### Core behavior

#### `dispatch()`

- resolves `self.object = self.get_object()`
- on failure:
  - adds error message
  - returns `RefreshResponse(request)` (**`horilla.web`** — HTMX refresh behavior)

#### `get_context_data()`

Adds:
- `model_name`
- `page_obj` (paginated grouped history)
- `actions` (action names from history entries)
- `filter_form`
- `filter_applied`

It builds `history_by_date` as:
- list of `(date, [entries])` sorted descending by date.

#### `get()`

- normal render by default
- if `show_filter=true` and HTMX request:
  - returns only `partials/history_filter_form.html` as raw `HttpResponse`

### Example subclass

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from horilla_generics.views.core import HorillaHistorySectionView
from horilla_crm.leads.models import Lead


class LeadHistoryView(LoginRequiredMixin, HorillaHistorySectionView):
    model = Lead
```

HTMX filter panel call example:

```text
/leads/history/42/?show_filter=true
```

---

## ➕ `HorillaDynamicCreateView`

### Decorator / mixins

- `@htmx_required` on `dispatch`
- `LoginRequiredMixin`

### Purpose

Generic dynamic modal for creating related model records from another form (for example creating a new FK option without leaving the current page).

Template:
- `dynamic_form_view.html`

---

### Request contract

#### URL kwargs (required)

- `app_label`
- `model_name`

#### GET params (optional but commonly used)

| Param | Meaning | Example |
|---|---|---|
| `fields` | comma-separated fields to include | `name,code,is_active` |
| `permission` | comma-separated custom perms (overrides default add perm) | `leads.add_leadstatus` |
| `target_field` | target `<select name="...">` to receive new option | `lead_status` |
| `full_width_fields` | comma-separated fields that render full width | `description,notes` |
| `initial_<field>` | initial value injection | `initial_name=Hot Lead` |

---

### Main methods

#### `get_model_and_fields()`

- resolves target model via `apps.get_model(app_label, model_name)`
- parses `fields` param to list
- returns `(model, field_names)` or `(None, None)` with message on lookup failure

#### `dispatch()`

Validation sequence:
1. resolve model + fields
2. validate requested field names exist on model
3. compute required permissions:
   - custom from `permission` param OR default `"{app}.add_{model}"`
4. deny:
   - invalid model/fields -> script response closing dynamic modal + reload messages
   - missing permission -> render `403.html` with modal style

#### `get_form_class()`

Builds dynamic `HorillaModelForm` subclass:
- `model = target_model`
- `fields = selected fields or "__all__"`
- excludes system fields:
  - `created_at`, `updated_at`, `created_by`, `updated_by`, `additional_info`
- applies date input widgets for `DateField`

#### `get_context_data()`

Adds:
- `form_title` (`Create <Verbose Name>`)
- `target_field`
- `form_url` (same path + query string)
- `full_width_fields`
- `field_permissions` from `get_field_permissions_for_model(user, model)`

#### `get_form_kwargs()`

Passes to form:
- `full_width_fields`
- `field_permissions`
- `initial` values from `initial_...` query params

#### `form_valid()`

Creates instance and sets:
- `created_by`, `updated_by` = request user
- `company` = form `company` or `request.active_company` or `request.user.company`

Then returns JS that:
- finds `select[name="<target_field>"]`
- appends new `<option>` (`pk`, escaped string label)
- triggers Select2 change if applicable
- closes dynamic modal

#### `form_invalid()`

- sets error message
- re-renders form with validation errors.

---

## 🧪 End-to-end example

### Use-case

From a Lead form, allow creating a new `LeadStatus` in a dynamic modal and auto-selecting it.

### Example request URL

```text
/generics/dynamic-create/leads/leadstatus/?fields=name,color&target_field=lead_status&full_width_fields=name&initial_name=New%20Status
```

### What happens

1. `HorillaDynamicCreateView` resolves model `leads.LeadStatus`.
2. Builds form with `name,color`.
3. On submit success, JS injects option into:
   - `select[name="lead_status"]`
4. Modal closes; parent form keeps user in place.

---

## 📌 Summary

- `HorillaView`: base context wiring for nav/layout endpoints.
- `HorillaTabView`: HTMX tabs + persisted active tab target.
- `HorillaHistorySectionView`: object history timeline with filtering + pagination.
- `HorillaDynamicCreateView`: safe dynamic creation modal with model/field validation, permission checks, and JS select-option injection.

