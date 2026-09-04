"""
Shared permission-checking mixin for activity create/update form views.
"""

from horilla.apps import apps
from horilla.contrib.generics.views.details import check_record_access
from horilla.shortcuts import get_object_or_404, render
from horilla.web import Http404, ScriptResponse

from ...models import Activity


class ActivityOwnerPermissionMixin:
    """
    Mixin that gates GET requests on owner-field membership or the
    ``activity.add_activity`` / ``activity.change_activity`` permissions.

    Subclasses must set ``model = Activity`` and define ``get()``.
    Call ``_check_owner_permission(request, object_id, model_name, app_label, pk)``
    and return the result immediately if it is not ``None``.
    """

    def has_permission(self):
        """Allow if user has add_activity, add_own_activity, or can write to the parent record."""
        user = self.request.user
        if user.is_superuser:
            return True
        if user.has_perm("activity.add_activity") or user.has_perm(
            "activity.add_own_activity"
        ):
            return True
        # Allow if user can access the parent record (view OR owner+view_own)
        object_id = self.request.GET.get("object_id")
        model_name = self.request.GET.get("model_name")
        app_label = self.request.GET.get("app_label")
        if object_id and model_name and app_label:
            try:
                model_class = apps.get_model(app_label=app_label, model_name=model_name)
                instance = model_class.objects.get(pk=object_id)
                return check_record_access(user, instance)
            except Exception:
                pass
        return False

    def _check_owner_permission(self, request, object_id, model_name, app_label, pk):
        """
        Return an HttpResponse if access is denied, or None to continue.

        Logic:
        - If object_id + model_name are provided, verify the user owns (via
          OWNER_FIELDS) or has add_activity permission on the parent object.
        - If only pk is provided (edit path), verify the user owns the activity
          or has change_activity permission.
        - Otherwise, deny with a 403 render.
        """
        if object_id and model_name:
            try:
                model_class = apps.get_model(app_label=app_label, model_name=model_name)
                try:
                    instance = get_object_or_404(model_class, pk=object_id)
                except Http404:
                    from django.contrib import messages

                    messages.error(
                        request,
                        f"{self.model._meta.verbose_name} not found or no longer exists.",
                    )
                    return ScriptResponse(
                        reload=True,
                        close=True,
                    )

                if not check_record_access(
                    request.user, instance
                ) and not request.user.has_perm("activity.add_activity"):
                    return render(request, "403.html")

                return None  # access granted

            except LookupError:
                return render(request, "403.html")

        if pk:
            if Activity.objects.filter(
                owner_id=request.user, pk=pk
            ).first() or request.user.has_perm("activity.change_activity"):
                return None  # access granted
            return None  # original code fell through to super() here too

        return render(request, "403.html")
