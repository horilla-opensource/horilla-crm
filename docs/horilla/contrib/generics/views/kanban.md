# Kanban view (`horilla/contrib/generics/views/kanban.py`)

## Purpose

`HorillaKanbanView` is the generic HTMX kanban board view built on top of `HorillaListView`.

It provides:

- grouping into columns by a selected field (Choice or ForeignKey),
- per-user persisted group-by preference via `KanbanGroupBy` (`view_type="kanban"`),
- drag/drop item move across columns with permission checks,
- optional drag/drop column reorder (ForeignKey groups with related `order` field),
- column-level pagination ("load more"),
- consistent filtering/search behavior by reusing `get_queryset()`.

---

## Class: `HorillaKanbanView`

- Decorator: `@method_decorator(htmx_required, name="dispatch")`
- Base: `HorillaListView`
- Template: `kanban_view.html`

### Core attributes

| Attribute | Default | Meaning |
|-----------|---------|---------|
| `group_by_field` | `None` | Fallback group field if user has no saved setting. |
| `paginate_by` | `30` | Items per column page. |
| `filterset_module` | `filters` | Filter module convention used by list base class. |
| `kanban_attrs` | `None` | Per-card HTMX attrs (often includes `{get_detail_url}` patterns). |
| `height_kanban` | `None` | Optional board height class/style passed to template. |
| `kanban_order_by` | `-updated_at` | Item order inside each column; falls back to `-id` if model has no `updated_at`. |

### View registry

`__init_subclass__` auto-registers subclasses:

- `HorillaKanbanView._view_registry[model] = subclass`

This powers helper endpoints like `kanban_load_more` and update routes that need to instantiate the model-specific view class.

---

## Dispatch and model resolution

`dispatch()`:

1. Redirects anonymous users to login.
2. Resolves `self.model` from URL kwargs (`app_label`, `model_name`) or POST `model_name`.
3. Validates model exists; raises **`HttpNotFound`** (`horilla.web`) for invalid pair.
4. Raises `ImproperlyConfigured` if no model is available.

This allows one generic update endpoint to work across many model-specific kanban subclasses.

---

## Permissions for drag/drop

`can_user_modify_item(item)` allows move when:

- user has `change_<model>` permission, or
- user has `change_own_<model>` and matches any model `OWNER_FIELDS` FK value, or
- user has `change_own_<model>` and `user_has_granted_access(item, user, "change")` returns `True` — the per-instance [granted-access hook](list.md#granted-access-per-model-opt-in-beyond-owner_fields) (e.g. an `Opportunity` team member with sufficient `opportunity_access`), checked after the `OWNER_FIELDS` loop fails to match.

If not allowed, move/update endpoints return a reload script with an error message.

---

## POST operations

`post()` routes based on payload:

- `item_id` + `new_column` -> `update_kanban_item()`
- `column_order` -> `update_kanban_column_order()`
- else -> parent `post()`

### 1) `update_kanban_item`

Used when dragging a card to another column.

Required POST fields:

- `item_id`, `new_column`, `app_label`, `model_name`, `class_name`

Flow:

1. Recreate model-specific view instance from `_view_registry`.
2. Resolve model via **`horilla.apps.apps.get_model()`** (kanban base and overrides such as `AcivityKanbanView` use the Horilla re-export, not `django.apps`).
3. Resolve effective group field via `get_group_by_field()`.
4. Permission check with `can_user_modify_item`.
5. Update group field:
   - **Choice**: accepts raw choice key or label (label reverse-mapped),
   - **ForeignKey**: accepts related pk or `"none"` for nullable; type checks use **`horilla.db.models.ForeignKey`** where needed.
6. Save item.
7. Rebuild query params from POST (excluding control fields/CSRF), assign to `view.request.GET`.
8. Recompute `view.object_list = view.get_queryset()` (important: preserves all list filters/search).
9. Render `partials/kanban_blocks.html` — **unless** the registered view overrides `update_kanban_item()` (see Activity kanban below).
10. Set `HX-Push-Url` to `main_url` + reconstructed query string.

### Activity kanban override

`AcivityKanbanView` (activity app) overrides step 9: after saving a drag-drop status change it returns a reload script (`$('#reloadButton').click()`) instead of re-rendering kanban blocks, because one registry entry serves all activity types while tabbed UIs filter to a single type. See [activity.md — Kanban views](../activity/activity.md#kanban-views-viewscorepy).

### 2) `update_kanban_column_order`

Used when reordering columns themselves (not cards).

Works only when:

- current group field is `ForeignKey`, and
- related model has an `order` field.

Flow:

1. Parse `column_order` JSON list.
2. Use `transaction.atomic()` with temporary offset (`max(order)+1000`) to avoid unique order collisions. In `kanban.py`: `from horilla.db import transaction` under `# First party imports (Horilla)`; `IntegrityError` stays `from django.db` in the Django block.
3. Assign temporary order, then compact to 0..N in requested order.
4. Recompute queryset/context and render `partials/kanban_blocks.html`.
5. Return with `HX-Push-Url`.

Returns 400 for invalid shape or unsupported field type, 500 for server errors.

---

## Group-by field selection

Same pattern as group-by view, but scoped to kanban settings (`view_type="kanban"`):

- `_get_kanban_exclude_include_fields()`
- `_get_allowed_group_by_fields()`
- `_is_field_visible_for_group_by()`
- `get_group_by_field()`

Priority:

1. saved `KanbanGroupBy` value for current user/model/app with `view_type="kanban"`;
2. class fallback `group_by_field`;
3. first allowed visible field.

Never returns a hidden field.

---

## Board context (`get_context_data`)

Main responsibilities:

- validate group field type (Choice/FK only),
- build grouped columns + paginated cards,
- prepare display fields for cards from filtered columns,
- add per-card flags for drag permission.

### Column metadata

Always includes:

- `group_by_field`, `group_by_label`
- `allow_column_reorder` (FK with related `order`)
- `class_name`, `kanban_attrs`, `height_kanban`
- `app_label`, `apps_label`, `model_name`

### Grouping behavior

- **Choice fields**: columns follow declared choice order; unknown DB values become `Unknown (...)` columns.
- **ForeignKey fields**:
  - column order by related model `order` when present else `pk`,
  - nullable FK can include `"None"` column,
  - optional related `color` field is used for column color; default hex `#f39022` maps to `"primary-600"`.

### Card display fields

`filtered_columns = self._get_columns()` (already field-permission filtered by list base).

For each card:

- `item.can_drag` set by `can_user_modify_item`.
- `item.display_columns` built excluding the current group field.
- Supports:
  - direct field values,
  - `get_<field>_display()` for choice fields,
  - explicit method names already in `get_*_display` form.
- Missing values rendered as `"N/A"`.

---

## Column "load more" (`load_more_items`)

Used by helper route:

- `horilla_generics:kanban_load_more`
- URL pattern: `kanban-load-more/<str:app_label>/<str:model_name>/`

GET params:

- `column_key` (choice value, FK pk, or `"None"`)
- `page`

Flow:

1. Resolve group field and normalize `column_key`.
2. Reuse `get_queryset()` to preserve search/filter logic.
3. Filter only the requested column, order by `get_kanban_order_by()`.
4. Paginate and render `partials/kanban_items.html`.

Returns empty body when no further pages, and 400/500 on errors.

---

## Related routes and templates

Routes in `horilla_generics/urls.py`:

- `update-kanban-item/<app_label>/<model_name>/` -> `update_kanban_item`
- `update-kanban-column-order/<app_label>/<model_name>/` -> `update_kanban_column_order`
- `kanban-load-more/<app_label>/<model_name>/` -> helper view delegating to `load_more_items`
- `create-kanban-group/` -> kanban/group-by settings form (`HorillaKanbanGroupByView`)

Templates:

- `kanban_view.html`
- `partials/kanban_blocks.html`
- `partials/kanban_items.html`
- `kanban_settings_form.html`

---

## Real subclass example (`LeadKanbanView`)

```python
class LeadKanbanView(LoginRequiredMixin, HorillaKanbanView):
    model = Lead
    view_id = "Lead_Kanban"
    filterset_class = LeadFilter
    search_url = reverse_lazy("leads:leads_list")
    main_url = reverse_lazy("leads:leads_view")
    group_by_field = "lead_status"
    exclude_kanban_fields = "lead_owner"
    columns = ["title", "first_name", "email", "lead_source", "industry"]
    actions = LeadListView.actions
```

Route example:

```python
path("leads-kanban/", views.LeadKanbanView.as_view(), name="leads_kanban")
```

---

## Notes

- `kanban_order_by` accepts a string or tuple/list; useful for stable secondary ordering.
- Item updates and column reordering both rebuild board HTML and set `HX-Push-Url` so browser URL stays in sync with active filters.
- Group-by preferences are shared infrastructure with GroupBy view but separated by `view_type` (`kanban` vs `group_by`).
