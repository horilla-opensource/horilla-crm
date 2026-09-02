# Horilla Web Utilities

## 📛 Package name

Import path: **`horilla.web`** (on disk: `horilla/web/`).

This module was formerly named **`horilla.http`**. It was renamed to **`horilla.web`** because a directory named `http` inside `horilla/` shadowed Python’s standard-library `http` package when Django added the app folder to `sys.path` — for example when running `python manage.py makemessages` from inside `horilla/`. That caused circular import errors in `django.http`.

**Migration:** replace `from horilla.http import …` with `from horilla.web import …`. Submodule imports use `horilla.web.response` and `horilla.web.url_safety` (for example `from horilla.web.response import RedirectResponse`).

---

## 🎯 Purpose

The `horilla.web` module provides:

- **Centralized HTTP imports** — common Django HTTP types in one place
- **Secure redirect handling** — validation against open redirects (CWE-601)
- **HTMX-compatible responses** — `HX-Redirect` and `HX-Refresh` where appropriate
- **Custom error handling** — `HttpNotFound` with Horilla’s `404.html` / `error.html` stack

It is the preferred entry point for the symbols it re-exports and for Horilla’s redirect/error helpers.

**Note:** Code examples below use **explicit arguments** (including optional ones) so the full call shape is visible at a glance.

---

## 🧠 Core concept

### ❌ Avoid direct Django imports (for what this package exposes)

```python
# Less ideal when horilla.web already exports it
from django.http import HttpResponse, StreamingHttpResponse
```

```python
# ✅ Preferred
from horilla.web import HttpResponse, StreamingHttpResponse
```

**Simple rule:** If a name appears in the **re-export list** below (for example `HttpResponse`, `StreamingHttpResponse`), import it from **`horilla.web`**. If you need something from Django that is **not** in that list, import it from **`django.http`** instead — `horilla.web` does not include every class Django offers, only the ones Horilla chose to forward.

### Import patterns

```python
# Preferred — package entry (matches __all__)
from horilla.web import HttpResponse, RedirectResponse, safe_url

# Submodule — when importing one helper class directly
from horilla.web.response import RedirectResponse
from horilla.web.url_safety import safe_url
```

---

## 📦 Module location

On disk, `horilla/web/` contains the following layout (as in the package directory):

```text
horilla/web/
├── response.py      # HttpNotFound, RedirectResponse, RefreshResponse
├── url_safety.py    # safe_url() — open-redirect safe URL validation (CWE-601)
└── __init__.py      # Package entry: re-exports Django HTTP types + Horilla helpers (__all__)
```

| File / directory | Role |
|------------------|------|
| `response.py` | Custom responses and `HttpNotFound` (`as_response` → Horilla templates). |
| `url_safety.py` | `safe_url(request, next_url, fallback=…)` using `url_has_allowed_host_and_scheme`. |
| `__init__.py` | Re-exports: Django `HttpResponse`, `JsonResponse`, `FileResponse`, redirects, `Http404`, `QueryDict`, plus `safe_url`, `HttpNotFound`, `RedirectResponse`, `RefreshResponse`. See **`__all__`** in `horilla/web/__init__.py` for the authoritative list. |

### Translation workflow (`makemessages`)

You can run **`makemessages` scoped to the platform tree** from inside `horilla/`:

```bash
cd horilla
python ../manage.py makemessages -l ar
```

Django walks the current working directory (`.`) for translatable strings. Output goes to `horilla/locale/` via `LOCALE_PATHS` in settings. This works with the `horilla.web` package name; the old `horilla/http/` path caused stdlib import conflicts when using this workflow.

---

## 🔁 What `horilla.web` provides

### 📍 Re-exported Django classes

- `HttpResponse`
- `JsonResponse`
- `FileResponse`
- `StreamingHttpResponse`
- `HttpResponseRedirect`
- `HttpResponseNotFound`
- `HttpResponseBadRequest`
- `HttpResponseNotAllowed`
- `Http404`
- `QueryDict`

### ➕ Custom utilities

- `safe_url`
- `RedirectResponse`
- `RefreshResponse`
- `HttpNotFound`

---

## 🔐 Safe URL handling

### 📍 Function

```python
safe_url(request, next_url, fallback="/")
```

### 🎯 Purpose

Prevents **open redirect** vulnerabilities (**CWE-601**).

### ✅ Behavior

Validates redirect URLs using Django’s `url_has_allowed_host_and_scheme`. In practice, that means:

- **Same host** as the current request (via `allowed_hosts={request.get_host()}`)
- **Safe scheme** — `require_https` follows `request.is_secure()`

Invalid or empty URLs return `fallback` (default `"/"`).

### 🧪 Example (all parameters explicit)

```python
next_url = safe_url(
    request,
    request.GET.get("next", "/"),
    fallback="/",
)
```

Prevents redirecting users to external malicious sites when `next` is forged or unsafe.

---

## 🔁 `RedirectResponse`

### 📍 Class

```python
class RedirectResponse(HttpResponseRedirect):
    ...
```

### 🎯 Purpose

- Safe redirects (uses `safe_url` internally)
- HTMX-compatible redirects (`HX-Redirect`)
- Prevents open redirects
- Optional Django **messages** via `message=` → `messages.error`
- **Fallback URL** when the target is not safe (`fallback_url`, default `"/"`)
- **HTMX detection** — checks `HX-Request` header

### 🔄 Behavior

| Request type | Result |
|--------------|--------|
| **Normal** | **302** — `Location: <safe-url>` |
| **HTMX** (`HX-Request`) | **200** — `HX-Redirect: <safe-url>` (no `Location`; avoids breaking HTMX flows) |

If `redirect_to` is omitted, the target is taken from **`HTTP_REFERER`**, then validated with `safe_url` against `fallback_url`.

### 🧪 Example

```python
return RedirectResponse(
    request,
    redirect_to="/dashboard/",
    message=None,
    fallback_url="/",
)
```

With a flash message when redirecting after validation failure:

```python
return RedirectResponse(
    request,
    redirect_to="/accounts/profile/",
    message="Please fix the errors below.",
    fallback_url="/",
)
```

---

## 🔄 `RefreshResponse`

### 📍 Class

```python
class RefreshResponse(HttpResponse):
    ...
```

### 🎯 Purpose

Triggers a **full page refresh** safely.

### ⚙️ Behavior

| Request type | Result |
|--------------|--------|
| **HTMX** | **200** — `HX-Refresh: true` |
| **Normal** (with `request`) | **302** — redirect to **safe** current path (`safe_url(request, request.path, fallback_url)`) |

### 🧪 Example

```python
return RefreshResponse(
    request=request,
    fallback_url="/",
)
```

---

## 🧩 `ScriptResponse`

### 📍 Class

```python
class ScriptResponse(HttpResponse):
    ...
```

### 🎯 Purpose

Returns a ``<script>`` payload for common Horilla HTMX UI actions instead of
hardcoding strings like `HttpResponse("<script>closeModal();</script>")`.

### ⚙️ Flags

| Flag | JS emitted |
|------|------------|
| `reload=True` | `$('#reloadButton').click();` |
| `msgs=True` | `$('#reloadMessagesButton').click();` |
| `close=True` | `closeModal();` |
| `extra="..."` | Custom JS (string or list/tuple of strings) |

**Execution order follows keyword argument order at the call site** (Python 3.7+).
Pass `extra` before `close` when the custom trigger must run first, or the reverse when the modal should close first.

### 🧪 Examples

Close modal only:

```python
from horilla.web import ScriptResponse

return ScriptResponse(close=True)
# <script>closeModal();</script>
```

Reload messages then close modal (msgs before close in the call):

```python
return ScriptResponse(msgs=True, close=True)
# <script>$('#reloadMessagesButton').click();closeModal();</script>
```

Close modal then reload messages:

```python
return ScriptResponse(close=True, msgs=True)
# <script>closeModal();$('#reloadMessagesButton').click();</script>
```

HTMX tab trigger, then close modal:

```python
return ScriptResponse(
    extra="htmx.trigger('#tab-contact_relationships-btn','click');",
    close=True,
)
# <script>htmx.trigger('#tab-contact_relationships-btn','click');closeModal();</script>
```

Close modal first, then custom script:

```python
return ScriptResponse(
    close=True,
    extra="htmx.trigger('#tab-fiscal-year-view','click');",
)
```

Reload list + messages + close (order as written):

```python
return ScriptResponse(reload=True, msgs=True, close=True)
# <script>$('#reloadButton').click();$('#reloadMessagesButton').click();closeModal();</script>
```

Multiple extra statements at one position:

```python
return ScriptResponse(
    reload=True,
    extra=[
        "htmx.trigger('#reloadButton','click');",
        "window.scrollTo(0, 0);",
    ],
)
```

---

## ⚡ `HxTriggerResponse`

### 📍 Class

```python
class HxTriggerResponse(HttpResponse):
    ...
```

### 🎯 Purpose

Returns a ``<script>`` that calls ``htmx.trigger(selector, event)`` for one or
more element ids. Bare ids are auto-prefixed with ``#``.

### ⚙️ Arguments

| Arg | Default | Notes |
|-----|---------|--------|
| `id` | `"reloadButton"` | Element id, CSS selector, or list/tuple of ids |
| `event` | `"click"` | Event name passed to `htmx.trigger` |
| `extra` | `None` | Extra JS after the trigger (str or list/tuple of strs) |
| `status` | `200` | HTTP status code |

### 🧪 Examples

Standalone (response is only the HTMX trigger):

```python
from horilla.web import HxTriggerResponse, ScriptResponse

return HxTriggerResponse()
# <script>htmx.trigger('#reloadButton','click');</script>

return HxTriggerResponse(extra="closehorillaModal();")
# <script>htmx.trigger('#reloadButton','click');closehorillaModal();</script>

return HxTriggerResponse(id="tab-splits-btn", extra="closeContentModal();")
# <script>htmx.trigger('#tab-splits-btn','click');closeContentModal();</script>

return HxTriggerResponse(id="tab-currency-view")
# <script>htmx.trigger('#tab-currency-view','click');</script>

return HxTriggerResponse(id=["tab-account_relationships-btn", "tab-contact_relationships-btn"])
# triggers both with click
```

Compose with `ScriptResponse` when you also need `close`, `reload`, `msgs`, etc.
`HxTriggerResponse.build(...)` (alias of `build_js`) returns the bare JS string
for `extra=` (also defaults to `#reloadButton`):

```python
# Trigger a tab and close the modal
return ScriptResponse(
    extra=HxTriggerResponse.build(id="tab-contact_relationships-btn"),
    close=True,
)
# <script>htmx.trigger('#tab-contact_relationships-btn','click');closeModal();</script>

# Multiple extras: trigger + other JS, then reload messages
return ScriptResponse(
    extra=[
        HxTriggerResponse.build(id="tab-currency-view"),
        "window.scrollTo(0, 0);",
    ],
    msgs=True,
)
```

---

## Modal transition after init signals

Some CRM init flows return a **rendered script template** instead of `ScriptResponse` because they must:

1. Close the wizard modal (`closeModal()`)
2. Reload the settings list (`$('#reloadButton').click()`)
3. Open the large content modal (`openContentModal()`)
4. HTMX-load a URL into `#contentModalBox`

Templates:

- `horilla_crm/leads/templates/lead_status/reload_and_load_url_script.html`
- `horilla_crm/opportunities/templates/opportunity_stage/reload_and_load_url_script.html`

Signal receivers: `handle_company_created` (`horilla_crm/leads/signals.py`), `handle_lead_stage_group_created` (`horilla_crm/opportunities/signals.py`). Documented in [initialize_database.md](../contrib/core/initialize_database.md).

### Recommended migration (future)

Compose `ScriptResponse` with `extra=` for steps 3–4:

```python
from horilla.web import ScriptResponse

return ScriptResponse(
    close=True,
    reload=True,
    extra=(
        "openContentModal();"
        f"htmx.ajax('GET', '{load_url}', {{target: '#contentModalBox', swap: 'innerHTML'}});"
    ),
)
```

Until those templates are removed, keep the existing partials in sync with any modal DOM changes.

---

## 🚫 `HttpNotFound` (custom 404)

### 📍 Class

```python
class HttpNotFound(Exception):
    ...
```

Constructor: `HttpNotFound(message=..., context=None, template=None)` — if `template` is omitted, **`404.html`** is used.

### 🎯 Purpose

- Custom 404 **exception** with message, optional `context`, optional `template`
- Renders a Horilla **404** via `as_response(request)` (status **404**, `error_message` in context)

### 🧪 Usage

```python
raise HttpNotFound(
    message="Custom error message",
    context={},
    template=None,
)
```

With extra template context and a specific template path:

```python
raise HttpNotFound(
    message="Resource not available.",
    context={"resource_id": resource_id},
    template="404.html",
)
```

### 🔄 Convert to response

`as_response` takes only the request:

```python
return exception.as_response(request)
```

---


## 🎨 Error templates

### 📍 Base template — `templates/error.html`

Shared layout for error pages: supports **full page**, **modal** (`modal`), and **embedded** (`embed`) modes, **dark mode**, and layout that works with **HTMX** (e.g. modal vs full height).

### 📍 404 template — `templates/404.html`

- **Extends** `error.html`
- Shows **Page Not Found** and `{{ error_message }}` (with a default if missing)

### ✨ Example fragment (conceptual)

```html
<h2>Page Not Found</h2>
<p>{{ error_message }}</p>
```

(Actual markup uses Horilla classes and `{% trans %}` — see `templates/404.html`.)

---

## 🧩 Example usage (login-style `next`)

```python
next_url = safe_url(
    request,
    request.GET.get("next", "/"),
    fallback="/",
)

return render(
    request,
    "login.html",
    {
        "next": next_url,
    },
)
```

Ensures the value you pass into the template (and later into redirects) is safe.

---

## 📬 Real-world example: mail open tracking

`horilla.contrib.mail.views.core.track.TrackOpenView` returns a 1×1 GIF for email open detection:

```python
from horilla.web import HttpResponse

return HttpResponse(_PIXEL_GIF, content_type="image/gif")
```

The pixel URL is built in `horilla.contrib.mail.services` with `horilla.urls.reverse("mail:track_open", kwargs={"uid": …})`. OAuth authorize views in the meeting app use the same module for **`HttpResponseRedirect(provider_auth_url)`**.

---

## ⚠️ Important guidelines

| Avoid | Prefer |
|-------|--------|
| `from django.http import *` | `from horilla.web import ...` for exported names |
| Raw `HttpResponseRedirect(untrusted_url)` | `safe_url(request, url, fallback=...)` or `RedirectResponse` |

**Always validate redirects** with `safe_url` or use `RedirectResponse` / `RefreshResponse`.

---

## 🧩 Benefits

- **Security** — reduces open redirect risk
- **Consistency** — shared HTTP imports (including `StreamingHttpResponse`) and 404 rendering
- **HTMX** — correct `HX-Redirect` / `HX-Refresh` behavior
- **Cleaner imports** — one obvious module for Horilla HTTP patterns

---

## 📌 Summary

| Feature | Django alone | Horilla `horilla.web` |
|---------|----------------|------------------------|
| HTTP imports | Direct, per file | Centralized re-exports + helpers |
| Redirect safety | Manual | Built-in (`safe_url`, response classes) |
| HTMX support | Manual headers | Built into `RedirectResponse` / `RefreshResponse` |
| Custom 404 UX | Varies | `HttpNotFound` + shared templates |
| Streaming responses | `django.http` | Same class via `horilla.web` re-export |

---

## 🏁 Conclusion

The `horilla.web` module:

- Wraps and re-exports selected Django HTTP utilities (including `StreamingHttpResponse`)
- Adds **security** (safe redirects) and **HTMX** behavior
- Standardizes **404** handling through `HttpNotFound` and Horilla error templates
- Replaces the former **`horilla.http`** package (renamed to avoid shadowing Python’s stdlib `http` module)

Use it wherever you would otherwise duplicate redirect validation or HTMX header logic.
