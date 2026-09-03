# Global search (`horilla_generics/views/global_search.py`)

## Purpose

`GlobalSearchView` is a **login-required** cross-model search UI. It:

- reads **which models** participate from the **feature registry** (`global_search_models`);
- builds **per-model search field lists** and **display columns** from model metadata (first five **CharField** / **TextField** fields);
- applies **`view_*` / `view_own_*`** filtering with **`OWNER_FIELDS`** (or common ownership heuristics);
- renders **`global_search.html`** with **tabs** (by model) and **result tables** via **`HorillaListView`** + **`list_view.html`**;
- supports **HTMX** for **tab switching** and **empty-query redirect** back to the previous page.

URL name: **`horilla_generics:global_search`** — path **`search/`** under the horilla_generics URL config.

---

## Registration: which models appear

Models are **not** hard-coded in this file. They come from:

```python
FEATURE_REGISTRY.get("global_search_models", [])
```

Populated at runtime via **`horilla.registry.feature`** (e.g. **`register_model_for_feature(..., features=["global_search"])`** or **`register_models_for_feature(..., features=["global_search"])`**). Apps often do this in **`registration.py`** loaded from **`AppConfig.ready()`**.

**Important:** `get_include_models()` **must** read the registry **at request time** (as implemented). Caching model lists on the class at **import** time would stay **empty**, because registration runs **after** imports during **`AppConfig.ready()`**.

---

## Class: `GlobalSearchView`

- **Base:** `LoginRequiredMixin`, Django **`View`** (not `TemplateView`).
- **Template:** `template_name = "global_search.html"`.

### Class-level defaults

| Name | Role |
|------|------|
| `exclude_standard_fields` | Field names skipped for search and column picking (`id`, `company`, audit fields, etc.). |
| `default_max_results` | Stored in per-model config (`3`); available to templates / future limits (full queryset is still built for counts in the current flow—see source). |
| `default_icons` | Default Tailwind / Font Awesome keys for tab UI (`bg_color`, `text_color`, `icon`). |
| `default_status_colors` | Defined on the class; **not referenced** in `global_search.py` (reserved or legacy). |

---

## Dynamic model configuration — `get_dynamic_model_config()`

For each **installed** model whose **`model_name`** (capitalized class name, e.g. `Lead`) matches an entry from `get_include_models()` (matched by **lowercase** `model_name`):

1. Collect up to **five** **CharField** / **TextField** names → **`search_fields`** (used in `__icontains` OR queries).
2. **`columns`** — first five text columns for **`HorillaListView`** (verbose name + field name pairs).
3. Skip the model if either list ends up empty.

Each entry in the returned dict is keyed by **`model_name`** (e.g. `"Lead"`) with:

| Key | Meaning |
|-----|---------|
| `app_name` | `app_label` |
| `search_fields` | Up to 5 field names |
| `display_field` | Callable: first search field’s value, or `str(instance)` |
| `summary_fields` | First three `search_fields` (snippet line under title) |
| `icons`, `max_results`, `verbose_name`, `model`, `columns` | As built above |

---

## Permission filtering — `get_filtered_queryset(model, base_queryset, request)`

- **`view_{model_name}`** → return **full** `base_queryset`.
- Else **`view_own_{model_name}`** → restrict using **`OWNER_FIELDS`**:
  - **ForeignKey** / **ManyToMany** to **user** / **employee** / **`auth.user`**: filter with `Q(...)` combined with **OR** across fields.
  - Non-relation fields: `Q(field_name=user)` when applicable.
  - **`get_granted_access_filter(model, user, "view")`** (see [list.md — Granted access](list.md#granted-access-per-model-opt-in-beyond-owner_fields)) is called and, if it returns a `Q`, **OR'd** into the same combined query — so a model opting into granted access (e.g. `Opportunity` team members) surfaces matching records in search results even without an `OWNER_FIELDS` match.
- If **`OWNER_FIELDS`** is missing or yields no queries, falls back to trying common names: **`created_by`**, **`user`**, **`owner`**, **`employee_id`** (same FK/M2M rules).
- If user has **neither** permission → **empty** queryset.

---

## Tab / table HTML — `get_tab_content(request, model_name, query)`

1. Resolves **`model_config[model_name]`**; otherwise returns a small “Model not found” HTML fragment.
2. Builds `Q(field__icontains=query)` across **`search_fields`**, **`filter`**, applies **`get_filtered_queryset`**.
3. **Highlights** query substring in **`display_field`** and summary values (regex + `<span class="bg-yellow-200">`).
4. Special-case formatting in summaries: **`amount`**, **`close_date`**, **`open_rate`** (project-specific).
5. Configures a **`HorillaListView`** instance: **`queryset`**, **`columns`**, **`paginate_by=100`**, **`search_url`** → **`horilla_generics:global_search`**, **`view_id`** `global-search-{model}`, etc.
6. If the model defines **`get_detail_url`**, sets **`col_attrs`** on the **first column** with **`get_col_attrs_for_model`** (HTMX navigation into main content).

Returns **`render_to_string("list_view.html", ...)`**.

---

## HTMX column navigation — `get_col_attrs_for_model(model_name, request)`

Builds **`hx-*`** attrs for the first column so clicking a row loads the object’s detail:

- **`hx-get`**: `{get_detail_url}` placeholder plus **`q`**, **`filter`**, and **`section`** (from **`get_section_info_for_model(model_name)`** when `section` is in the request).
- **`hx-target`**: `#mainContent`, **`hx-push-url`**, **`hx-select`**, **`hx-select-oob`** for `#sideMenuContainer`.
- Clears header search on click: **`hx-on:click`**: `$('#header-search').val('')`.

The template/list layer substitutes **`{get_detail_url}`** per row with each instance’s detail URL.

---

## GET handler — `get(request)`

### Query parameters

| GET | Role |
|-----|------|
| `q` | Search string (trimmed). **Empty** → see below. |
| `filter` | `all` (default) or a **capitalized** model name (e.g. `Lead`) to show **only** that model’s tab/results. |
| `prev_url` | Where to go when **`q`** is empty; **sanitized** with **`safe_url`** from **`horilla.web`**, `section` may be stripped from query, and nested global-search URLs fall back to **`session["pre_search_url"]`**. |
| `section` | Passed through when redirecting; used in close button and tab links. |
| `tab_model` | With **HTMX** + non-empty **`q`**, returns **only** `get_tab_content(...)` HTML for that model (tab switch). |

### Empty query (`q` missing/blank)

- Optionally appends **`section`** to **`previous_url`**.
- If **`HX-Request`**: **`HttpResponse`** with **`HX-Redirect`** → **`previous_url`**.
- Else: **`redirect(previous_url)`**.

### Full page (non-tab HTMX)

Builds **`model_config`**, runs search per model, counts results, **sorts** models by **result count** descending, pre-renders **`first_tab_content`** for the **first** model with hits (respecting **`filter`**).

Renders **`global_search.html`** with:

- `query`, `filter`, `total_results`, `model_config`, `search_results`, `search_results_with_data`, `first_tab_content`, `first_model_name`, `previous_url`, etc.

---

## Integration points

| Piece | Location |
|-------|----------|
| Header search link | `templates/components/header.html` — `hx-get` to **`global_search`** with **`prev_url`**. |
| Template | `horilla_generics/templates/global_search.html` — tabs, `first_tab_content`, close button. |
| URL | `horilla_generics/urls.py` — `path("search/", ..., name="global_search")`. |
| Feature registry | `horilla/registry/feature.py` — **`FEATURE_CONFIG["global_search"]`** → **`global_search_models`**. |

---

## Example: register a model for global search

In your app’s **`registration.py`** (loaded from **`AppConfig`**):

```python
from horilla.registry.feature import register_model_for_feature

register_model_for_feature(
    app_label="myapp",
    model_name="Ticket",
    features=["global_search"],
)
```

Or bulk:

```python
from horilla.registry.feature import register_models_for_feature

register_models_for_feature(
    models=[("myapp", "Ticket"), ("myapp", "Tag")],
    features=["global_search"],
)
```

Ensure the model has at least one **CharField** / **TextField** that is not in **`exclude_standard_fields`**, or it will be skipped by **`get_dynamic_model_config()`**.

---

## Summary

| Topic | Behavior |
|-------|----------|
| **Scope** | Only models in **`FEATURE_REGISTRY["global_search_models"]`**. |
| **Search** | OR of **`__icontains`** on up to five text fields per model. |
| **Security** | **`view_*` / `view_own_*`** + ownership filters. |
| **UI** | Full page + HTMX tabs; list rows may open detail via **`get_detail_url`**. |

For registry API details, see **`horilla/registry/feature.md`**.
