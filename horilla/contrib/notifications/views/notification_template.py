"""Notification Template Views"""

# Standard library imports
import logging
from functools import cached_property

from django.contrib import messages

# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.forms import ValidationError

# First party imports (Horilla)
from horilla.apps import apps
from horilla.contrib.core.methods import get_template_reverse_models
from horilla.contrib.core.models import HorillaContentType
from horilla.contrib.generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaView,
)
from horilla.contrib.utils.middlewares import _thread_local
from horilla.shortcuts import get_object_or_404
from horilla.urls import reverse, reverse_lazy
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from horilla.utils.translation import gettext_lazy as _
from horilla.views.generic import DetailView, FormView, TemplateView
from horilla.web import HttpNotFound, RefreshResponse, ScriptResponse

from ..filters import NotificationTemplateFilter
from ..forms import NotificationTemplateForm

# Local imports
from ..models import NotificationTemplate

logger = logging.getLogger(__name__)


@method_decorator(
    permission_required_or_denied(
        "notifications.view_notificationtemplate",
        wrapper_id="notification-template-view",
    ),
    name="dispatch",
)
class NotificationTemplateView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for notification template view
    """

    template_name = "settings/settings_list_shell.html"
    view_id = "notification-template-view"
    nav_url = reverse_lazy("notifications:notification_template_nav_view")
    list_url = reverse_lazy("notifications:notification_template_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["notifications.view_notificationtemplate"]),
    name="dispatch",
)
class NotificationTemplateNavbar(LoginRequiredMixin, HorillaNavView):
    """Navbar for Notification Template"""

    nav_description = _("Customize the content of notifications sent to your users.")
    search_url = reverse_lazy("notifications:notification_template_list_view")
    main_url = reverse_lazy("notifications:notification_template_view")
    model_name = "NotificationTemplate"
    model_app_label = "notifications"
    nav_width = False
    all_view_types = False
    recently_viewed_option = False
    filter_option = False
    one_view_only = True
    reload_option = False
    border_enabled = False

    @cached_property
    def new_button(self):
        """New button configuration"""
        if self.request.user.has_perm("notifications.add_notificationtemplate"):
            return {
                "url": f"""{reverse_lazy("notifications:notification_template_create_view")}?new=true""",
                "attrs": 'id="notification-template-create"',
            }
        return None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["notifications.view_notificationtemplate"]),
    name="dispatch",
)
class NotificationTemplateListView(LoginRequiredMixin, HorillaListView):
    """
    Notification Template List view
    """

    model = NotificationTemplate
    view_id = "notification-template-list"
    search_url = reverse_lazy("notifications:notification_template_list_view")
    main_url = reverse_lazy("notifications:notification_template_view")
    save_to_list_option = False
    bulk_select_option = False
    enable_sorting = False
    filterset_class = NotificationTemplateFilter

    columns = ["title", ("content_type", "get_related_model")]

    def no_record_add_button(self):
        """Button to show when no records exist"""
        if self.request.user.has_perm("notifications.add_notificationtemplate"):
            return {
                "url": f"""{reverse_lazy("notifications:notification_template_create_view")}?new=true""",
                "attrs": 'id="notification-template-create"',
            }
        return None

    actions = [
        {
            "action": "Edit",
            "src": "assets/icons/edit.svg",
            "img_class": "w-4 h-4",
            "permission": "notifications.change_notificationtemplate",
            "attrs": """
                        hx-get="{get_edit_url}?new=true"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal()"
                        """,
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "notifications.delete_notificationtemplate",
            "attrs": """
                    hx-post="{get_delete_url}"
                    hx-target="#deleteModeBox"
                    hx-swap="innerHTML"
                    hx-trigger="click"
                    hx-vals='{{"check_dependencies": "true"}}'
                    onclick="openDeleteModeModal()"
                """,
        },
    ]

    @cached_property
    def raw_attrs(self):
        """Get row attributes for HTMX detail view loading"""
        if self.request.user.has_perm("notifications.view_notificationtemplate"):
            return {
                "hx-get": "{get_detail_view_url}",
                "hx-target": "#contentModalBox",
                "hx-swap": "innerHTML",
                "hx-on:click": "openContentModal();",
                "style": "cursor:pointer",
                "class": "hover:text-primary-600",
            }
        return ""


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["notifications.add_notificationtemplate"]),
    name="dispatch",
)
class NotificationTemplateCreateUpdateView(LoginRequiredMixin, FormView):
    """
    FormView for creating and updating Horilla Notification Template
    """

    form_class = NotificationTemplateForm
    template_name = "notification_template/template_form.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template_id = None
        self.object = None

    def dispatch(self, request, *args, **kwargs):
        """Resolve template by pk and set self.object; handle errors with modal close."""
        self.template_id = kwargs.get("pk")
        if self.template_id:
            try:
                self.object = get_object_or_404(
                    NotificationTemplate, pk=self.template_id
                )
            except Exception as e:
                messages.error(
                    request,
                    e,
                )
                return ScriptResponse(reload=True, close=True)
        else:
            self.object = None
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass current template instance to the form when editing."""
        kwargs = super().get_form_kwargs()
        if self.object:
            kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        """Add form title, submit text, and action URL for create/update template form."""
        context = super().get_context_data(**kwargs)
        if self.object:
            context["form_title"] = _("Edit Notification Template")
            context["submit_text"] = _("Edit Template")

        else:
            context["form_title"] = _("Create Notification Template")
            context["submit_text"] = _("Save Template")

        context["action_url"] = self.get_form_action_url()
        return context

    def get_form_action_url(self):
        """Get the appropriate URL for form submission"""
        if self.object:
            return reverse(
                "notifications:notification_template_update_view",
                kwargs={"pk": self.object.pk},
            )
        return reverse("notifications:notification_template_create_view")

    def form_valid(self, form):
        """Save template with company, show success message, and return modal-close script."""
        try:
            mail_template = form.save(commit=False)
            mail_template.company = (
                getattr(_thread_local, "request", None).active_company
                if hasattr(_thread_local, "request")
                else self.request.user.company
            )
            if not self.object:
                mail_template.created_by = self.request.user
            mail_template.updated_by = self.request.user
            mail_template.save()
            if self.object:
                messages.success(
                    self.request,
                    _('Notification template "{}" updated successfully.').format(
                        mail_template.title
                    ),
                )
            else:
                messages.success(
                    self.request,
                    _('Notification template "{}" created successfully.').format(
                        mail_template.title
                    ),
                )

            return ScriptResponse(reload=True, close=True)

        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        "notifications.delete_notificationtemplate", modal=True
    ),
    name="dispatch",
)
class NotificationTemplateDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """View to delete a notification template"""

    model = NotificationTemplate

    def get_post_delete_response(self):
        """Return script to reload and close modal after template deletion."""
        return ScriptResponse(reload=True)


@method_decorator(
    permission_required_or_denied(["notifications.view_notificationtemplate"]),
    name="dispatch",
)
class NotificationTemplateDetailView(LoginRequiredMixin, DetailView):
    """ " View to display mail template details"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object = None

    def dispatch(self, request, *args, **kwargs):
        """Ensure user is authenticated, load object, and handle HTMX errors with refresh."""
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        try:
            self.object = self.get_object()
        except Exception as e:
            if request.headers.get("HX-Request") == "true":
                messages.error(self.request, e)
                return RefreshResponse(request)
            raise HttpNotFound(e) from e
        return super().dispatch(request, *args, **kwargs)

    model = NotificationTemplate
    template_name = "notification_template/template_detail.html"
    context_object_name = "notification_template"


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "notifications.change_notificationtemplate",
            "notifications.view_notificationtemplate",
        ]
    ),
    name="dispatch",
)
class NotificationTemplateFieldSelectionView(LoginRequiredMixin, TemplateView):
    """
    View to show all fields of the related model for insertion into email templates
    """

    template_name = "field_selection_modal.html"

    def get_context_data(self, **kwargs):
        """Add model/instance field data for template variable insertion (model_name, object_id, etc.)."""
        context = super().get_context_data(**kwargs)

        model_name = self.request.GET.get("model_name")
        object_id = self.request.GET.get("object_id")
        content_type_id = self.request.GET.get("content_type")

        if model_name or content_type_id:
            tab_type = self.request.GET.get(
                "tab_type", "instance"
            )  # Default to instance if model exists
        else:
            tab_type = self.request.GET.get(
                "tab_type", "user"
            )  # Default to user if no model

        excluded_fields = {
            "is_active",
            "additional_info",
            "history",
            "password",
            "user_permissions",
            "groups",
            "last_login",
            "date_joined",
            "is_staff",
            "is_superuser",
            "recycle_bin_policy",
        }

        try:
            if tab_type == "instance" and model_name or content_type_id:
                if model_name:
                    content_type = HorillaContentType.objects.get(
                        model=model_name.lower()
                    )
                else:
                    content_type = HorillaContentType.objects.get(id=content_type_id)
                    # Use content_type.model (e.g. 'employee') for URLs, not verbose_name,
                    # so tab links send a value that HorillaContentType.objects.get(model=...) can find
                    model_name = content_type.model
                model_class = apps.get_model(
                    app_label=content_type.app_label, model_name=content_type.model
                )
                related_object = None
                if object_id and object_id != "None":
                    related_object = model_class.objects.get(pk=object_id)

                model_fields = []

                # Get regular fields (skip editable=False)
                for field in model_class._meta.get_fields():
                    if field.name in excluded_fields:
                        continue
                    if not getattr(field, "editable", True):
                        continue

                    if not field.many_to_many and not field.one_to_many:
                        field_info = {
                            "name": field.name,
                            "verbose_name": getattr(field, "verbose_name", field.name),
                            "field_type": field.__class__.__name__,
                            "template_syntax": f"{{{{ instance.{field.name} }}}}",
                            "is_foreign_key": (
                                field.many_to_one
                                if hasattr(field, "many_to_one")
                                else False
                            ),
                            "is_relation": hasattr(field, "related_model"),
                        }

                        model_fields.append(field_info)

                foreign_key_fields = []
                for field in model_class._meta.get_fields():
                    # Skip excluded fields
                    if field.name in excluded_fields:
                        continue
                    if not getattr(field, "editable", True):
                        continue

                    if field.many_to_one and hasattr(field, "related_model"):
                        # Get fields from the related model without needing object instance
                        for related_field in field.related_model._meta.get_fields():
                            # Skip excluded fields in related model too
                            if related_field.name in excluded_fields:
                                continue
                            if not getattr(related_field, "editable", True):
                                continue

                            if (
                                not related_field.many_to_many
                                and not related_field.one_to_many
                            ):
                                fk_field_info = {
                                    "name": (f"{field.name}.{related_field.name}"),
                                    "verbose_name": (
                                        getattr(
                                            related_field,
                                            "verbose_name",
                                            related_field.name,
                                        )
                                    ),
                                    "header": field.verbose_name,
                                    "field_type": (
                                        f"{field.__class__.__name__} -> "
                                        f"{related_field.__class__.__name__}"
                                    ),
                                    "template_syntax": (
                                        f"{{{{ instance.{field.name}."
                                        f"{related_field.name} }}}}"
                                    ),
                                    "parent_field": field.name,
                                    "is_foreign_key": True,
                                }

                                foreign_key_fields.append(fk_field_info)

                reverse_relation_fields = []

                # Models allowed as reverse relations in Insert field (feature registry)
                allowed_reverse_models = get_template_reverse_models()

                # Models already shown in Related Fields (forward FKs) - don't show again in Reverse
                related_models_in_forward = set()
                for f in model_class._meta.get_fields():
                    if (
                        f.many_to_one
                        and hasattr(f, "related_model")
                        and f.related_model
                    ):
                        related_models_in_forward.add(f.related_model)

                # Get all reverse relations
                for field in model_class._meta.get_fields():
                    if field.one_to_many or field.many_to_many:
                        # Skip fields that don't have get_accessor_name method
                        # (e.g., AuditlogHistoryField)
                        if not hasattr(field, "get_accessor_name"):
                            continue
                        try:
                            # Get the accessor name (like 'employee_set' or custom related_name)
                            accessor_name = field.get_accessor_name()

                            related_model = field.related_model

                            # Skip reverse relation if this model is already in Related Fields
                            if (
                                related_model
                                and related_model in related_models_in_forward
                            ):
                                continue

                            # Include only models in template_reverse registry when feature is registered
                            if (
                                allowed_reverse_models is not None
                                and related_model not in allowed_reverse_models
                            ):
                                continue

                            if related_model:
                                for reverse_field in related_model._meta.get_fields():
                                    if (
                                        reverse_field.name in excluded_fields
                                        or reverse_field.many_to_many
                                        or reverse_field.one_to_many
                                    ):
                                        continue
                                    if not getattr(reverse_field, "editable", True):
                                        continue

                                    if (
                                        hasattr(reverse_field, "related_model")
                                        and reverse_field.related_model == model_class
                                    ):
                                        continue

                                    reverse_field_info = {
                                        "name": (
                                            f"{accessor_name}.first."
                                            f"{reverse_field.name}"
                                        ),
                                        "verbose_name": (
                                            getattr(
                                                reverse_field,
                                                "verbose_name",
                                                reverse_field.name,
                                            )
                                        ),
                                        "header": field.related_model._meta.verbose_name,
                                        "field_type": (
                                            f"Reverse {field.__class__.__name__} -> "
                                            f"{reverse_field.__class__.__name__}"
                                        ),
                                        "template_syntax": (
                                            f"{{{{ instance.{accessor_name}|join_attr:"
                                            f"'{reverse_field.name}' }}}}"
                                        ),
                                        "parent_field": accessor_name,
                                        "is_reverse_relation": True,
                                    }

                                    reverse_relation_fields.append(reverse_field_info)
                        except Exception as e:
                            logger.error(
                                "Error processing reverse relation splits: %s",
                                e,
                            )
                            continue

                context["model_fields"] = model_fields
                context["foreign_key_fields"] = foreign_key_fields
                context["reverse_relation_fields"] = reverse_relation_fields
                context["related_object"] = related_object

            elif tab_type == "user":
                user = self.request.user
                model_fields = []

                for field in user._meta.get_fields():
                    if field.name in excluded_fields:
                        continue
                    if not getattr(field, "editable", True):
                        continue

                    if not field.many_to_many and not field.one_to_many:
                        field_info = {
                            "name": field.name,
                            "verbose_name": getattr(field, "verbose_name", field.name),
                            "field_type": field.__class__.__name__,
                            "template_syntax": f"{{{{ request.user.{field.name} }}}}",
                            "is_foreign_key": (
                                field.many_to_one
                                if hasattr(field, "many_to_one")
                                else False
                            ),
                            "is_relation": hasattr(field, "related_model"),
                        }

                        model_fields.append(field_info)

                context["model_fields"] = model_fields
                context["foreign_key_fields"] = []
                context["reverse_relation_fields"] = []
                context["related_object"] = user

            elif tab_type == "company":
                # Get current active company fields
                company = getattr(self.request, "active_company", None)

                if company:
                    model_fields = []

                    for field in company._meta.get_fields():
                        if field.name in excluded_fields:
                            continue
                        if not getattr(field, "editable", True):
                            continue

                        if not field.many_to_many and not field.one_to_many:
                            field_info = {
                                "name": field.name,
                                "verbose_name": getattr(
                                    field, "verbose_name", field.name
                                ),
                                "field_type": field.__class__.__name__,
                                "template_syntax": f"{{{{ request.active_company.{field.name} }}}}",
                                "is_foreign_key": (
                                    field.many_to_one
                                    if hasattr(field, "many_to_one")
                                    else False
                                ),
                                "is_relation": hasattr(field, "related_model"),
                            }

                            model_fields.append(field_info)

                    context["model_fields"] = model_fields
                    context["foreign_key_fields"] = []
                    context["reverse_relation_fields"] = []
                    context["related_object"] = company
                else:
                    context["error"] = "No active company found"

            elif tab_type == "request":
                # Get request object fields (commonly used request attributes)
                request_fields = [
                    {
                        "name": "get_host",
                        "verbose_name": "Host",
                        "template_syntax": "{{ request.get_host }}",
                    },
                    {
                        "name": "scheme",
                        "verbose_name": "Scheme",
                        "template_syntax": "{{ request.scheme }}",
                    },
                ]

                model_fields = []
                for field_data in request_fields:
                    field_info = {
                        "name": field_data["name"],
                        "verbose_name": field_data["verbose_name"],
                        "field_type": "RequestAttribute",
                        "template_syntax": field_data["template_syntax"],
                        "is_foreign_key": False,
                        "is_relation": False,
                    }

                    model_fields.append(field_info)

                context["model_fields"] = model_fields
                context["foreign_key_fields"] = []
                context["reverse_relation_fields"] = []
                context["related_object"] = self.request

            context["has_model_name"] = bool(model_name) or bool(content_type_id)
            context["model_name"] = model_name
            context["object_id"] = object_id
            context["tab_type"] = tab_type

        except Exception as e:
            context["error"] = f"Error loading fields: {str(e)}"
        return context
