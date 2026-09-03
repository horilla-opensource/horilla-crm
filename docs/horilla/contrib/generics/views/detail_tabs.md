# Horilla detail tabs (`horilla_generics/views/detail_tabs.py`)

## Purpose

This module provides:

1. **`HorillaDetailTabView`** — HTMX tab strip for **detail pages**: builds a list of tab definitions (Details, Activity, Related Lists, Notes & Attachments, History) from a **`urls` map** and **`object_id`**.
2. **`HorillaDetailSectionView`** — **`DetailView`** that renders the **main “Details” tab body**: model fields in a grid, optional **per-user field visibility**, **field-level permissions**, and **inline edit** hooks.

Both views are decorated with **`@method_decorator(htmx_required, name="dispatch")`** — they expect HTMX requests.

---

## Dependencies (read before subclassing)

| Piece | Role |
|-------|------|
| `HorillaTabView` (`horilla_generics.views.core`) | Base for tab UI; template `tab_view.html`, `ActiveTab` for remembered tab, context: `tabs`, `view_id`, `tab_class`. |
| `HorillaDetailView` (`horilla_generics.views.details`) | `base_excluded_fields`, `check_update_permission()` used for `can_update` context. |
| `DetailFieldVisibility` (`horilla_core.models`) | Optional per-user, per-URL field list for the details body. |
| `get_field_permissions_for_model` (`horilla_core.utils`) | Per-field read/write/hide for template. |

---

## `HorillaDetailTabView`

### Role

Subclass of **`HorillaTabView`** that **populates `self.tabs` in `__init__`** when `object_id` is set. Each entry is a dict: `title`, `url`, `target` (HTMX swap target id), `id`.

### Class attributes

| Attribute | Default | Meaning |
|-----------|---------|---------|
| `view_id` | `"generic-details-tab-view"` | Passed to `tab_view.html` context. |
| `object_id` | `None` | Primary key of the object; if falsy, **no tabs are added**. |
| `urls` | `{}` | Map of **named URL patterns** → Django URL name strings (see below). |
| `tab_class` | Tailwind height class | Overridden in `__init__` when `pipeline_field` is absent (shorter vs taller pane). |

### `urls` keys

Only keys **present** in `urls` get a tab. Supported keys:

| Key | Tab title | `target` id | Notes |
|-----|-----------|-------------|--------|
| `details` | Details | `tab-details-content` | URL includes optional query: `pipeline_field`, `detail_url_name`. |
| `activity` | Activity | `tab-activity-content` | `reverse_lazy` with `pk=object_id`. |
| `related_lists` | Related Lists | `tab-related-lists-content` | |
| `notes_attachments` | Notes & Attachments | `tab-notes-attachments-content` | Only if user has `horilla_core.view_horillaattachment` **or** `horilla_core.view_own_horillaattachment`. |
| `history` | History | `tab-history-content` | |

### Extension tabs (added by other contrib apps)

`HorillaDetailTabView` itself has **no knowledge of feature-specific tabs** like Cadence or Potential Duplicates. Those contrib apps (`horilla.contrib.cadences`, `horilla.contrib.duplicates`) each wrap `_prepare_detail_tabs` from their own `inject.py` at import time, call the original implementation, then conditionally `self.tabs.append(...)` their own tab dict (same `title` / `url` / `target` / `id` shape as above). See [Cadences — runtime injection](../cadences/cadences.md#runtime-injection-injectpy) and [Duplicates — runtime injection](../duplicates/duplicates.md#runtime-injection-injectpy) for the exact pattern to follow when adding a new extension tab.

### GET parameters affecting the Details tab URL

When `details` is in `urls`:

- **`pipeline_field`** — appended to the details URL as `?pipeline_field=...` (and used elsewhere for layout height).
- **`detail_url_name`** — appended as `detail_url_name=...` so the details section can resolve `DetailFieldVisibility` for that view.

### Height / layout (`tab_class`)

In `__init__`:

- If **`pipeline_field`** is absent → `tab_class = "h-[calc(_100vh_-_390px_)] overflow-hidden"`.
- If **`pipeline_field`** is present → default class from the class body: `h-[calc(_100vh_-_475px_)] overflow-hidden`.

This keeps the tab panel height consistent with pipeline vs non-pipeline detail layouts.

### Example (conceptual)

```python
class MyRecordDetailTabsView(HorillaDetailTabView):
    object_id = None  # set in as_view or dispatch in real apps

    urls = {
        "details": "myapp:record_detail_section",
        "activity": "myapp:record_activity",
        "related_lists": "myapp:record_related_lists",
        "notes_attachments": "myapp:record_notes",
        "history": "myapp:record_history",
    }
```

Wire `object_id` from the parent detail view (e.g. pass `pk` into the view that renders the tab strip).

---

## `HorillaDetailSectionView`

### Role

Renders **`template_name = "details_tab.html"`** with **`context_object_name = "obj"`**: a responsive grid of **read-only inputs** showing field values, with optional **edit** buttons that HTMX-load `horilla_generics:edit_field` (see template).

### Class attributes

| Attribute | Default | Meaning |
|-----------|---------|---------|
| `template_name` | `"details_tab.html"` | Details tab body. |
| `context_object_name` | `"obj"` | Main model instance. |
| `body` | `[]` | If non-empty, used as list of `(verbose_name, field_name)` tuples; else from `get_default_body()`. |
| `edit_field` | `True` | Show inline edit when permissions allow. |
| `non_editable_fields` | `[]` | Field names that never show the edit control. |
| `base_excluded_fields` | `HorillaDetailView.base_excluded_fields` | Starting exclude list for auto body. |
| `excluded_fields` | `[]` | Extra fields excluded from the default body (merged in `get_excluded_fields()`). |
| `include_fields` | `[]` | If set, only these field **names** are shown (still respecting excludes and `pipeline_field` exclude). |

### `get_excluded_fields()`

Returns **`base_excluded_fields` + `excluded_fields`** (no duplicate base entries).

### `check_object_permission(request, obj)`

Default behavior:

- **`view_{model_name}`** on `app_label` → allow.
- Else, if model defines **`OWNER_FIELDS`**, check whether `obj` is “owned” by `request.user` via those FKs.
- If owner → require **`view_own_{model_name}`**.
- Else, if `request.user` has **`view_own_{model_name}`**, fall back to the per-instance **granted access** hook: **`user_has_granted_access(obj, user, "view")`** (see [list.md — Granted access](list.md#granted-access-per-model-opt-in-beyond-owner_fields)) → allow when the model grants access some other way (e.g. `Opportunity` team membership).
- Otherwise → deny.

Override for stricter or custom rules.

### `get(request, ...)`

- Loads object with `get_object()`; on exception → flash error + script to click `#reloadButton`.
- If `check_object_permission` fails → **`403.html`** with status 403.
- Else → normal render with `get_context_data`.

### `get_default_body()`

Builds `(verbose_name, name)` from `model._meta.get_fields()`:

- Skips names in `get_excluded_fields()`.
- If **`pipeline_field`** is in GET, that field name is also excluded.
- If **`include_fields`** is non-empty, only listed names are included (still filtered).

### `get_context_data(**kwargs)`

Adds:

| Key | Source |
|-----|--------|
| `body` | `self.body` or `get_default_body()`, optionally **replaced** by `DetailFieldVisibility` (see below). |
| `model_name`, `app_label` | Model `_meta`. |
| `edit_field`, `non_editable_fields` | Class attrs. |
| `field_permissions` | `get_field_permissions_for_model(user, self.model)`. |
| `can_update` | `HorillaDetailView.check_update_permission(self)`. |
| `pipeline_field` | From GET if present. |

### `DetailFieldVisibility` integration

If **`detail_url_name`** is present in **`request.GET`**:

- Loads first matching `DetailFieldVisibility` for `user`, `app_label`, `model_name`, `url_name=detail_url_name`.
- If `visibility.details_fields` is set, **`body`** is rebuilt**: each entry is either a field name or a `(…, name)` tuple; only fields that exist on the model are kept (`FieldDoesNotExist` skipped).

This lets the same model show different columns per route or saved layout.

### Template behavior (`details_tab.html`)

- Iterates **`body`**; uses **`field_permissions`** (`hidden` skips the row).
- Values via **`display_field_value`** (`horilla_tags`).
- If **`edit_field`**, field not in **`non_editable_fields`**, permission **`readwrite`**, and **`can_update`**: edit button **`hx-get`** to `horilla_generics:edit_field` with `pk`, `field_name`, `app_label`, `model_name`, and `pipeline_field` query param.

---

## Summary

| Class | Use when |
|-------|----------|
| `HorillaDetailTabView` | You need the **tab bar** + HTMX targets for details / activity / related / notes / history. |
| `HorillaDetailSectionView` | You need the **Details tab content** with field visibility, permissions, and optional **DetailFieldVisibility** by `detail_url_name`. |

For the shared **`HorillaTabView`** / history section patterns, see `horilla_generics/views/core.md`.
