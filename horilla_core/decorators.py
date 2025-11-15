from functools import wraps

from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse_lazy


def permission_required_or_denied(
    perms, template_name="error/403.html", require_all=False
):
    """
    Custom decorator for both FBVs and CBVs.
    - `perms`: single permission string or a list/tuple of permissions.
    - `require_all`: if True, user must have ALL permissions; if False, ANY one is enough.
    """

    if isinstance(perms, str):
        perms = [perms]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(*args, **kwargs):

            request = args[0] if hasattr(args[0], "user") else args[1]
            user = request.user

            if not user.is_authenticated:
                login_url = f"{reverse_lazy('horilla_core:login')}?next={request.path}"
                return redirect(login_url)
                # return render(request, "login.html")

            if require_all:
                has_permission = user.has_perms(perms)
            else:
                has_permission = user.has_any_perms(perms)

            if has_permission:
                return view_func(*args, **kwargs)
            return render(request, template_name, {"permissions": perms})

        return _wrapped_view

    return decorator


def permission_required(perms, require_all=False):
    """
    Custom decorator for both FBVs and CBVs.
    Returns 403 if user doesn't have required permission(s).
    """
    if isinstance(perms, str):
        perms = [perms]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(*args, **kwargs):
            request = args[0] if hasattr(args[0], "user") else args[1]
            user = request.user

            if not user.is_authenticated:
                login_url = f"{reverse_lazy('horilla_core:login')}?next={request.path}"
                return redirect(login_url)

            if require_all:
                has_permission = user.has_perms(perms)
            else:
                has_permission = user.has_any_perms(perms)

            if has_permission:
                return view_func(*args, **kwargs)
            return HttpResponse("")

        return _wrapped_view

    return decorator


def htmx_required(view_func, login=True):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if login and not request.user.is_authenticated:
            login_url = f"{reverse_lazy('horilla_core:login')}?next={request.path}"
            return redirect(login_url)
        if not request.headers.get("HX-Request") == "true":
            return render(request, "error/405.html")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def htmx_required(view_func=None, login=True):
    def decorator(func):
        @wraps(func)
        def _wrapped_view(request, *args, **kwargs):
            if login and not request.user.is_authenticated:
                login_url = f"{reverse_lazy('horilla_core:login')}?next={request.path}"
                return redirect(login_url)
            is_export = request.method == "POST" and "export_format" in request.POST
            if is_export:
                return func(request, *args, **kwargs)
            if not request.headers.get("HX-Request") == "true":
                return render(request, "error/405.html")
            return func(request, *args, **kwargs)

        return _wrapped_view

    # If called without arguments: @htmx_required
    if view_func is not None:
        return decorator(view_func)

    # If called with arguments: @htmx_required(login=False)
    return decorator
