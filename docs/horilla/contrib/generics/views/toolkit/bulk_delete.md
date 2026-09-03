# Bulk delete toolkit (`horilla_generics/views/toolkit/bulk_delete.py`)

## Purpose

`HorillaBulkDeleteMixin` is the multi-step delete workflow engine used by generic list views.
Instead of deleting records in one shot, it walks through modal stages:

1. collect selected IDs,
2. choose hard or soft mode,
3. inspect reverse dependencies,
4. optionally remove dependency rows,
5. confirm final deletion for safe records.

This design lets users resolve blockers interactively, while the backend enforces queryset scope and dependency-aware safety checks.

---

## Core class

## `HorillaBulkDeleteMixin`

Primary entrypoint:

- `handle_bulk_delete_post(request, action, record_ids, delete_type)`

Helper methods:

- `_check_dependencies(record_ids)`
- `_delete_all_dependencies(item_id, selected_data)`
- `_delete_item_with_dependencies(item_id, record_ids, selected_data)`
- `_soft_delete_all_dependencies(item_id, selected_data)`
- `_soft_delete_item_with_dependencies(item_id, record_ids, selected_data)`
- `_perform_soft_delete(record_ids)`

Expected attributes/methods from the consuming view:

- `self.model` (Django model class)
- `self.get_queryset()` (permission-filtered/current list queryset)
- `self.get_context_data()` (context used by delete templates)

The mixin is intentionally view-dependent and relies on list view state for context, permission scope, and template variables.

---

## How it is called from list view

`HorillaListView.post()` delegates relevant POST actions to `handle_bulk_delete_post(...)`.

Control contract:

- returns `HttpResponse` => request fully handled by bulk-delete branch
- returns `None` => caller should continue normal POST routing

This pattern keeps the list view thin while allowing rich action handling inside a dedicated mixin.

---

## Main method signature deep dive

`handle_bulk_delete_post(self, request, action, record_ids, delete_type)`

- `request`: current POST request (HTMX/modal actions)
- `action`: action selector (for example, `bulk_delete`, `delete_all_dependencies`)
- `record_ids`: JSON array string for selected main record IDs (used by confirm/dependency actions)
- `delete_type`: operation mode (`soft`, `hard_non_dependent`, etc.)

Important: even when `record_ids` is passed, branches still re-validate IDs against current queryset before critical operations.

---

## Request branches in `handle_bulk_delete_post`

### 1) Delete mode picker (`delete_mode_form=true`)

Behavior:

- Parses `selected_ids` JSON.
- Casts to integers only.
- Restricts to IDs present in current `self.get_queryset()`.
- Creates context:
  - `selected_ids`
  - `selected_ids_json`
- Renders `partials/delete_mode_form.html`.

If no valid rows:

- adds Django message `"No rows selected for deletion."`
- returns script response to refresh list.

---

### 2) Hard delete pre-check form (`bulk_delete_form=true`)

Behavior:

- Resolves valid IDs from current queryset.
- Calls `_check_dependencies(valid_ids)`.
- Builds full dependency context:
  - `selected_ids`
  - `selected_ids_json`
  - `cannot_delete`
  - `can_delete`
  - `cannot_delete_count`
  - `can_delete_count`
  - `model_verbose_name`
- Renders `partials/bulk_delete_form.html`.

On malformed JSON:

- logs exception
- returns same template with empty lists and `"Invalid selected IDs provided."`.

---

### 3) Soft delete pre-check form (`soft_delete_form=true`)

Same as hard pre-check, but rendered template is `partials/soft_delete_form.html`.
The context schema is the same, so front-end can reuse dependency rendering patterns with different labels/actions.

---

### 4) Confirm bulk delete (`action == "bulk_delete"`)

Flow:

1. parse `record_ids` JSON,
2. compute `cannot_delete` / `can_delete` via `_check_dependencies(...)`,
3. if `confirm_delete=true`, perform deletion only on `can_delete_ids`.

When `confirm_delete=true`:

- `delete_type == "soft"`:
  - uses `_perform_soft_delete(can_delete_ids)`,
  - archives dependency rows + main rows into `RecycleBin`,
  - then deletes rows from source tables.
- `delete_type == "hard_non_dependent"`:
  - executes hard delete directly on safe IDs only.

Success responses are script snippets that trigger:

- list refresh (`#reloadButton`)
- modal close (soft path)
- unselect-all action for the specific list instance (`view_id`).

If not confirmed:

- returns dependency breakdown modal so user can resolve blockers first.

---

### 5) Delete one dependency model for one record (`action == "delete_item_with_dependencies"`)

Use case: a selected main row is blocked by multiple related models; user chooses to clear only one dependency model.

Inputs used:

- `record_id` (main object)
- `dep_model_name` (matched to `related_model._meta.verbose_name_plural`)
- `selected_ids` (full current selection state)
- `delete_type` (`soft` or hard)

- hard path: `_delete_item_with_dependencies(...)`
- soft path: `_soft_delete_item_with_dependencies(...)`

After deletion attempt, dependency state is recomputed and corresponding modal template is re-rendered.

---

### 6) Delete all dependency models for one record (`action == "delete_all_dependencies"`)

Use case: clear every dependency relation for one blocked main row.

- hard path: `_delete_all_dependencies(...)`
- soft path: `_soft_delete_all_dependencies(...)`

Returns refreshed dependency matrix so the user can proceed with final bulk delete.

---

## Dependency inspection logic: `_check_dependencies`

This is the decision engine that separates safe vs blocked records.

Algorithm:

- query selected main records with `.only("id")`
- inspect reverse relations from `self.model._meta.related_objects`
- for each relation:
  - resolve manager (`objects` fallback `all_objects`)
  - build prefetch `manager.all()[:10]` with `to_attr=prefetched_<related_name>`
- iterate main rows and assemble dependency summary objects
- classify each row:
  - `can_delete`: no prefetched dependent rows
  - `cannot_delete`: at least one dependent relation has rows

Output contracts:

- `cannot_delete`: `[{id, name, dependencies:[{model_name, count, records}]}]`
- `can_delete`: `[{id, name}]`
- `dependency_details`: `{id: dependencies}` convenience map

Notes:

- preview list uses first 10 dependent rows per relation
- count shown is the prefetched size (not guaranteed full relation cardinality)
- if a relation has no valid manager, method raises explicit `AttributeError`
- invalid relation lookup in prefetch also raises descriptive `AttributeError`

---

## Hard dependency deletion helpers

### `_delete_all_dependencies(item_id, selected_data)`

- normalizes `selected_data` to list and ensures `item_id` is included
- fetches main record
- iterates all reverse relations and hard-deletes dependent rows relation by relation
- builds user message summarizing models and deleted counts
- re-runs `_check_dependencies(selected_data)` to refresh blocker matrix
- returns context (not `HttpResponse`) for caller template rendering

### `_delete_item_with_dependencies(item_id, record_ids, selected_data)`

- targets only one dependency relation, selected by `dep_model_name`
- deletes all dependent rows of that relation for `item_id`
- re-checks selected rows and returns context with success/error message

---

## Soft dependency deletion helpers

Soft versions mirror hard behavior but archive rows before delete:

- `RecycleBin.create_from_instance(dep_record, user=request.user)`

Methods:

- `_soft_delete_all_dependencies(...)`
- `_soft_delete_item_with_dependencies(...)`

This preserves recoverability while keeping the same UI workflow as hard dependency cleanup.

---

## Full soft delete helper: `_perform_soft_delete`

Used for final confirmation when main records are ready to be removed in soft mode.

For each main object:

1. iterate reverse relations and archive+delete dependent rows,
2. archive+delete main row,
3. increment deleted main-row count.

Returns: number of deleted main rows.

---

## Templates used

- `partials/delete_mode_form.html`
- `partials/bulk_delete_form.html`
- `partials/soft_delete_form.html`

Template responsibilities:

- `partials/delete_mode_form.html`: choose hard vs soft path
- `partials/bulk_delete_form.html`: hard-delete dependency matrix and actions
- `partials/soft_delete_form.html`: soft-delete dependency matrix and actions

All templates rely on stable context keys populated by this mixin.

---

## Error handling strategy

- malformed JSON: caught and rendered as safe modal state
- invalid/missing `record_id`: caught (`ValueError`, `DoesNotExist`) with user message
- manager/relation issues: logged with explicit debug text
- operation exceptions: surfaced as error messages and modal stays interactive

Goal: do not break list UI; keep user in modal with actionable feedback.

---

## Security and data-scope behavior

Critical protection:

- selected IDs are always intersected with `self.get_queryset()`.

So effective delete scope is constrained by all list-level permission and ownership filters already applied in queryset construction. For a `delete_own_<model>`-only user, the confirm-delete branch (`action == "bulk_delete"`) additionally narrows `record_ids` to rows matching `OWNER_FIELDS`, OR'd with `get_granted_access_filter(self.model, user, "delete")` when the model defines it — so a model opting into [granted access](../list.md#granted-access-per-model-opt-in-beyond-owner_fields) (e.g. `Opportunity` team members) is bulk-deletable even without an `OWNER_FIELDS` match.

Additional notes:

- manager fallback (`objects` then `all_objects`) makes dependency traversal work for models with custom managers.
- this mixin itself does not compute permissions; it trusts caller queryset to represent authorized rows.

---

## Full payload examples (practical)

### Open delete mode modal

```text
POST /your-list-url/
delete_mode_form=true
selected_ids=[12,15,29]
```

Response:

- HTML for `delete_mode_form.html` with normalized valid IDs only.

### Render hard dependency matrix

```text
POST /your-list-url/
bulk_delete_form=true
selected_ids=[12,15,29]
```

Response context includes:

- `cannot_delete` (rows with dependency summaries)
- `can_delete` (rows safe for final delete)
- `selected_ids_json` for next modal actions.

### Delete one dependency relation for one record

```text
POST /your-list-url/
action=delete_item_with_dependencies
record_id=12
dep_model_name=Tasks
selected_ids=[12,15,29]
delete_type=soft
```

Response:

- re-rendered `soft_delete_form.html` with updated blocker counts.

### Final confirm soft delete

```text
POST /your-list-url/
action=bulk_delete
record_ids=[12,15,29]
confirm_delete=true
delete_type=soft
view_id=lead_list_1
```

Response:

- script to reload list, close modal, and unselect all.

---

## Example integration in a custom list view

```python
from horilla_generics.views.list import HorillaListView
from horilla_generics.views.toolkit.bulk_delete import HorillaBulkDeleteMixin
from leads.models import Lead


class LeadListView(HorillaBulkDeleteMixin, HorillaListView):
    model = Lead
    bulk_delete_enabled = True
```

In practice, `HorillaListView` already integrates this behavior, so direct mixin usage is mainly for custom list architectures.

---

## End-to-end flow (state-machine view)

1. **Selection stage**: receive raw selected IDs.
2. **Normalization stage**: cast/filter IDs to authorized queryset rows.
3. **Mode stage**: show hard/soft option form.
4. **Inspection stage**: build dependency matrix (`can_delete` vs `cannot_delete`).
5. **Resolution stage** (optional): delete one/all dependency groups for blocked rows.
6. **Confirmation stage**: delete only currently safe main rows.
7. **Refresh stage**: client-side script refreshes list and clears selection.

---

## Practical notes and caveats

- `dep_model_name` matching uses plural verbose label, so translations/custom labels can affect relation targeting.
- `_check_dependencies` shows preview records (first 10), useful for UX but not full relation audit.
- hard mode `hard_non_dependent` intentionally skips blocked rows; it does not force cascading destructive deletes.
- most branch responses are template renders or script snippets, optimized for HTMX modal workflows.
- because this is mixin-level logic, transactional guarantees depend on caller/database setup; operations are not wrapped in explicit atomic blocks in this file.

---

## Summary

`bulk_delete.py` is a dependency-aware bulk-delete orchestrator, not just a delete helper.
It combines authorization scope inheritance (`get_queryset()`), dependency introspection, selective cleanup actions, and soft-delete archival (`RecycleBin`) into one HTMX-friendly modal workflow that balances safety and operator control.
