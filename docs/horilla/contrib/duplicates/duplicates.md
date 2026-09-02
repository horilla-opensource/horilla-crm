# Horilla Clone Management (Duplicates) — deep dive (`horilla.contrib.duplicates`)

## What this app does

- **MatchingRule** / **MatchingRuleCriteria** — declarative “how to compare two records” (fields, fuzzy options) for duplicate detection.
- **DuplicateRule** / **DuplicateRuleCondition** — when to run detection, thresholds, and which models merge together.
- **Runtime injection** (`inject.py`) patches **generics** class-based views so duplicate checks run on **create/update** flows and a **Potential Duplicates** tab appears on **detail** views; inline **UpdateFieldView** also warns after save.

---

## App startup (`apps.py`)

`DuplicatesConfig`:

| Setting | Value |
|---------|--------|
| `url_prefix` | `duplicates/` |
| `url_module` | `horilla.contrib.duplicates.urls` |
| `auto_import_modules` | `menu`, `registration`, **`inject`** |

`app_name` in `urls.py` is **`duplicates`**. App config does not set `url_namespace` explicitly; URL reversing uses `duplicates:` from `urls.py`.

---

## Menu (`menu.py`)

Registers settings or admin entries for **Matching rules** and **Duplicate rules** list views (`matching_rule_view`, `duplicate_rule_view`, etc.). Icons and permissions are defined alongside each item.

---

## Feature registration (`registration.py`)

```text
register_feature("duplicate_data", "duplicate_models", auto_register_all=False)
```

Models registered under **`duplicate_models`** participate in duplicate detection and merge UIs.

---

## Runtime injection (`inject.py`)

Executed at import when **`inject`** is auto-imported.

| Patch | Target | Effect |
|-------|--------|--------|
| `inject_duplicate_checking` | `HorillaSingleFormView`, `HorillaMultiStepFormView` | Wraps `form_valid` to run duplicate detection before redirect. |
| `inject_duplicate_tab` | `HorillaDetailTabView` | Wraps `_prepare_detail_tabs` to append **Potential Duplicates** tab. |
| `inject_inline_edit_duplicate_checking` | `UpdateFieldView` | Wraps `post` to re-scan duplicates after inline field save; HTMX snippets can show modal + tab refresh. |

Original methods are stored on the class as `_original_form_valid`, `_original_prepare_detail_tabs`, `_original_post` to avoid double-wrapping.

---

## Models — roles

### `MatchingRule` / `MatchingRuleCriteria`

- Defines **similarity** logic (exact, fuzzy, concatenated fields).
- Criteria rows are ordered; evaluation code lives in duplicate engine modules (see `methods.py` / services next to views).

### `DuplicateRule` / `DuplicateRuleCondition`

- Business rules: which model, auto-merge vs suggest, minimum score, etc.
- Conditions narrow **when** the rule runs (same pattern as automations/cadences).

All extend **`HorillaCoreModel`** — company-scoped.

---

## Forms (`forms.py`)

Both rule forms use **`HorillaModelForm`** with **`fields = "__all__"`** and explicit **`field_order`** (model has no extra columns beyond those lists). Criteria rows use **`condition_fields`** on the views, not extra model fields on these forms.

### `MatchingRuleForm`

- **`field_order`**: `name`, `content_type`, `description`
- **Conditions**: `MatchingRuleCriteria` — `field_name`, `matching_method`, `match_blank_fields` (dynamic choices in **`__init__`**)
- **`clean()`**: requires at least one valid criterion row; no duplicate `field_name` across rows

### `DuplicateRuleForm`

- **`field_order`**: `name`, `content_type`, `description`, `matching_rule`, `action_on_create`, `action_on_edit`, `alert_title`, `alert_message`, `show_duplicate_records`
- **`__init__`**: HTMX on `content_type` filters `matching_rule` queryset; **`clean()`** enforces matching rule / content type alignment

---

## Typical flows

1. Admin defines a **matching rule** for Lead email + phone.
2. User creates a lead via **HorillaSingleFormView** → injection runs → modal warns if high-confidence duplicate exists.
3. User opens lead detail → **Potential Duplicates** tab lists side-by-side candidates → merge action uses rule configuration.

---

## Empty states (v1.13.8)

Matching rules accordion and potential-duplicates list use [empty_state.html](../../../templates/components/empty_state.md) instead of inline SVG blocks:

| Template | Message |
|----------|---------|
| `matching_rule_accordion.html` | “Nothing to show yet. Please add your Matching Rules.” |
| `potential_duplicates_list_view.html` | “No potential duplicates found.” |

---

## Related documentation

- Generics forms and detail tabs: [../generics/views/single_form.md](../generics/views/single_form.md), [../generics/views/detail_tabs.md](../generics/views/detail_tabs.md)
- Core content types: [../core/models.md](../core/models.md)
- Empty-state partials: [../../../templates/components/empty_state.md](../../../templates/components/empty_state.md)
