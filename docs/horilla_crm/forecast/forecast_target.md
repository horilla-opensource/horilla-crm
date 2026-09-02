# Forecast Targets (`horilla_crm.forecast.views.forecast_target`)

## What this module does

Manages **ForecastTarget** records — per-user, per-period targets against a forecast type (e.g. revenue, deal count). Supports bulk creation via condition rows, role-based user filtering, and dynamic conditional fields driven by "same" checkboxes.

---

## View inventory

| View | Base | Purpose |
|------|------|---------|
| `ForecastTargetView` | `HorillaView` | Main shell; validates `forecast_type` and `period` query params, redirects on invalid values |
| `ForecastTargetFiltersView` | `TemplateView` | HTMX partial — returns dynamic filter dropdowns for forecast type and period |
| `ForecastTargetNavbar` | `HorillaNavView` | Navigation bar with "Set Target" action |
| `ForecastTargetListView` | `HorillaListView` | Filtered and sortable target list |
| `ForecastTargetFormView` | `HorillaSingleFormView` | Create/update target; supports condition rows with "same" column collapsing |
| `ToggleRoleBasedView` | `View` | HTMX partial — filters user dropdown by selected role |
| `ToggleConditionFieldsView` | `View` | HTMX partial — shows or hides conditional fields based on checkbox state |
| `UpdateTargetHelpTextView` | `View` | HTMX partial — returns updated help text for target field based on `forecast_type` |
| `UpdateForecastTarget` | `HorillaSingleFormView` | Inline quick-update of a single target value |
| `ForecastTargetDeleteView` | `HorillaSingleDeleteView` | Delete a forecast target |

---

## Key patterns

### Parameter validation in main view

`ForecastTargetView.get()` validates `forecast_type` and `period` query params against allowed choices. Invalid values result in a redirect to the default forecast target URL rather than a 400 or an empty page.

### "Same" checkbox column collapsing

`ForecastTargetFormView` supports three checkboxes: `is_period_same`, `is_target_same`, `is_forecast_type_same`. When checked, the corresponding condition column is hidden and its value is copied from the first row to all rows before save. `process_row_data_before_create()` applies this logic during multi-instance creation.

```
is_period_same=True  → all rows get the same period value from row 0
is_target_same=True  → all rows get the same target value from row 0
is_forecast_type_same=True → all rows get the same forecast type from row 0
```

### Role-based user filtering

`ToggleRoleBasedView` filters the `assigned_to` queryset to users belonging to a selected role. Called via HTMX when the role dropdown changes; returns a replacement `<select>` widget for the user field.

`ToggleConditionFieldsView` does the same for a condition row's user column when working inside the bulk-create condition rows.

### Duplicate check

`ForecastTargetFormView.check_duplicate_instance()` blocks creation of a second target with the same `(assigned_to, period, forecast_type)` triple. Caught both within the same submit (via cache) and against the database.

### Session-based condition row count

The number of open condition rows is tracked in `request.session["condition_row_count"]`. `ForecastTargetView` and `ForecastTargetFormView` read and write this key so the form can expand with the right number of rows on re-render.

### Dynamic help text

`UpdateTargetHelpTextView` returns an HTML snippet with context-sensitive help for the target value field (e.g. currency symbol, unit label) based on the selected `forecast_type`. Called via HTMX when the forecast type dropdown changes.

### Empty states (`forecast_target_view.html`)

The main template uses shared [empty-state partials](../../../templates/components/empty_state.md):

| Condition | Partial |
|-----------|---------|
| `not has_company` | `components/empty_states/activate_company.html` |
| No forecast type configured | `components/empty_state.html` with message “No Forecast Type set. Set it from settings.” (CTA button rendered outside the include when permissions allow) |

The forecast dashboard shell (`forecast_view.html`) uses the same `activate_company.html` preset when `request.active_company` is missing.

---

## Bulk creation flow

1. User opens **Set Target** modal → `ForecastTargetFormView` renders with one condition row.
2. User adds rows → HTMX `add_condition_row` dispatches to `HorillaSingleFormView.dispatch`.
3. User toggles "Same period" → `ToggleConditionFieldsView` hides the period column across all rows.
4. User selects a role → `ToggleRoleBasedView` narrows the user dropdown.
5. User submits → `save_multiple_main_instances` iterates rows; `process_row_data_before_create` injects shared values; `check_duplicate_instance` rejects duplicates.

---

## Related documentation

- Forecast type tab (period table, trends, charts): [forecast_type_tab.md](forecast_type_tab.md)
- Shared empty-state partials: [../../templates/components/empty_state.md](../../templates/components/empty_state.md)
- `HorillaSingleFormView` multi-instance pattern: [../../horilla/contrib/generics/views/single_form.md](../../horilla/contrib/generics/views/single_form.md)
- `HorillaListView`: [../../horilla/contrib/generics/views/list.md](../../horilla/contrib/generics/views/list.md)
