# Bulk Edit Details helpers (`horilla/contrib/generics/views/helpers/edit_field.py`)

## Purpose

HTMX views behind the **Edit Details** control on the record details tab
(`details_tab.html`). One button switches the whole field grid into edit mode
with a single Save/Cancel pair (replacing the former per-field pencil cycle).

Routes: `generics:edit_all_fields` (GET) and `generics:update_all_fields` (POST).

All composable classes inherit [`horilla.views.generic.View`](../../../../views/generic.md),
so [`_inherit_view`](../../../../extension/view/inherit.md) extensions apply via
`as_view()` / `resolve_view_class()`.

---

## Classes overview

| Class / helper | Role |
|----------------|------|
| `FieldInfoResolver` | Per-field widget metadata (`get_field_info`) and value apply/parse (`apply_field_value`, date hooks). Never dispatched via `as_view()` — instantiated through `get_field_info_resolver()`. |
| `ExtraFieldsProvider` | Seam for non-model fields (e.g. `cf_*`) via `get_extra_fields` / `apply_extra_field`. Use `get_extra_fields_provider()`. |
| `EditAllFieldsView` | GET: render `partials/edit_all_fields.html` for every editable field in the detail `body`. |
| `UpdateAllFieldsView` | POST: apply all submitted fields, run `check_before_save`, then save (or skip when nothing changed). |
| `build_edit_all_fields_context(...)` | Shared context builder for render and re-render after blocked/failed save. |
| `can_edit_all_fields(request, obj)` | Who may use Edit Details on `obj`: the record page's rule, `HorillaDetailView.check_update_permission`. |

---

## `FieldInfoResolver`

```python
from horilla.contrib.generics.views.helpers.edit_field import get_field_info_resolver

resolver = get_field_info_resolver()  # resolve_view_class(FieldInfoResolver)()
```

Common `get_field_info` keys: `name`, `verbose_name`, `field_type`, `value`,
`display_value`, `choices`, `use_select2`, `input_attrs`.

### Field-type mapping (highlights)

- M2M / FK / choices / boolean / phone / email / url / number as before.
- `DateTimeField` → `datetime-local`; display via `format_datetime_value(..., convert_timezone=False)`.
- `DateField` → `date`; same formatter for display.
- State/country CharFields use model `STATE_FIELD_NAME` / `COUNTRY_FIELD_NAME` when set.
- Extensions may set `input_attrs` (e.g. Jalali `data-jdp`) and change `field_type` to `text`.

### Parse hooks (calendar extensions)

```python
def parse_datetime_field_value(self, value, user=None): ...
def parse_date_field_value(self, value, user=None): ...
```

Gregorian defaults use `datetime.fromisoformat`. Override via `_inherit_view` on
`FieldInfoResolver` (Jalali: `JalaliFieldInfoResolverExtension`).

---

## `ExtraFieldsProvider`

Defaults return no extras / ignore unknown POST keys. Extensions (Custom Fields)
override:

- `get_extra_fields(obj, request, can_update)` → list of `{"info": ..., "editable": bool}`
- `apply_extra_field(obj, name, request)` → `True` if handled (saves immediately)

---

## `EditAllFieldsView`

- HTMX-only (`@htmx_required`)
- Template: `partials/edit_all_fields.html`
- Allowed by `can_edit_all_fields(request, obj)` (see [Who may edit](#who-may-edit))
- Builds field list from the detail section `body`, field permissions, and
  `ExtraFieldsProvider`
- Optional query: `pipeline_field`, `return_url` (validated with
  `url_has_allowed_host_and_scheme`)

```python
from horilla.contrib.generics.views.helpers.edit_field import get_edit_all_fields_view

view = get_edit_all_fields_view()
```

---

## `UpdateAllFieldsView`

- HTMX-only; success re-renders `details_tab.html`
- Allowed by `can_edit_all_fields(request, obj)`, like `EditAllFieldsView`
- Two-phase save: apply values in-memory (`save=False` except M2M, which commit
  immediately), then `check_before_save(request, obj, changed_fields)`, then
  `obj.save(force=m2m_changed)` when there is something to persist
- **No-op skip:** if `changed_fields` is empty (and no field errors), skips
  `check_before_save` and `obj.save()` and just re-renders the details tab
- M2M-only changes still bump audit via `force=True` when needed

### Extension seams

| Method | Role |
|--------|------|
| `check_before_save(request, obj, changed_fields)` | Return an `HttpResponse` to block commit (e.g. Duplicates warning); `None` to proceed. |
| `handle_save_error(request, obj, error, app_label, model_name)` | Customize `ValidationError` from `obj.save()` (e.g. Approvals pending-edit guard). |

---

## Who may edit

`can_edit_all_fields(request, obj)` applies the record page's own rule,
`HorillaDetailView.check_update_permission`, which also decides whether the
Edit Details button and the stage bar are offered:

- an owner of the record (an `OWNER_FIELDS` entry names the user or someone
  in a role below theirs, or access was granted) with `change_own_<model>`;
- anyone with `change_<model>`;
- never a locked record (`is_record_locked`): the form and the save answer
  "This record is read-only." first.

Other users get "You do not have permission to edit this." (`403` on save).

---

## Date/time update rules

- `DateTimeField`: `parse_datetime_field_value`, then user-TZ → default TZ for storage.
- `DateField`: `parse_date_field_value`.

---

## Related

- Details tab UI: [`details.md`](../details.md) · template `details_tab.html`
- [`_inherit_view`](../../../../extension/view/inherit.md)
- [`DateTimeFormatter`](../../formatting/datetime.md) / [`_inherit_formatter`](../../../../extension/formatting/inherit.md)
- Consumers: Custom Fields (`ExtraFieldsProvider`), Duplicates / Approvals
  (`UpdateAllFieldsView` hooks), Jalali (`FieldInfoResolver`)

---

## Summary

Bulk Edit Details backend for detail tabs: one form for all editable fields,
extension-aware parse/display/extra fields, pre-save and save-error seams, and
skipped no-op saves when nothing actually changed.
