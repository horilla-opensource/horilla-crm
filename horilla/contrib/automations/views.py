"""
Views for the automations app
"""

# Standard library imports
import json
from functools import cached_property

# Third-party imports (Django)
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

from horilla.apps import apps
from horilla.auth.models import User
from horilla.contrib.core.models import HorillaContentType
from horilla.contrib.generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaSingleFormView,
    HorillaView,
)
from horilla.contrib.mail.models import HorillaMailConfiguration, HorillaMailTemplate
from horilla.contrib.notifications.models import NotificationTemplate

# First party imports (Horilla)
from horilla.db import models
from horilla.db.models import Q
from horilla.shortcuts import render
from horilla.urls import reverse_lazy
from horilla.utils.decorators import (
    htmx_required,
    method_decorator,
    permission_required_or_denied,
)
from horilla.utils.html import escape
from horilla.utils.translation import gettext_lazy as _
from horilla.web import ScriptResponse

# Local imports
from .filters import HorillaAutomationFilter
from .forms import HorillaAutomationForm
from .models import AutomationCondition, HorillaAutomation

# Fields that must not appear in condition field choices or in existing conditions (edit form)
AUTOMATION_CONDITION_EXCLUDED_FIELDS = [
    "id",
    "pk",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "company",
    "additional_info",
    "password",
]


@method_decorator(
    permission_required_or_denied(
        ["automations.view_horillaautomation"], wrapper_id="automation-view"
    ),
    name="dispatch",
)
class HorillaAutomationView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for automation page.
    """

    template_name = "settings/settings_list_shell.html"
    view_id = "automation-view"
    nav_url = reverse_lazy("automations:automation_navbar_view")
    list_url = reverse_lazy("automations:automation_list_view")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["automations.view_horillaautomation"]),
    name="dispatch",
)
class HorillaAutomationNavbar(LoginRequiredMixin, HorillaNavView):
    """
    Navbar view for automation
    """

    nav_description = _(
        "Automate mail and notifications based on events in your workflow."
    )
    search_url = reverse_lazy("automations:automation_list_view")
    main_url = reverse_lazy("automations:automation_view")
    model_name = "HorillaAutomation"
    model_app_label = "automations"
    filterset_class = HorillaAutomationFilter
    nav_width = False
    all_view_types = False
    filter_option = False
    reload_option = False
    one_view_only = True
    border_enabled = False
    enable_actions = True

    @cached_property
    def new_button(self):
        """New button configuration for the navbar."""
        if self.request.user.has_perm("automations.add_horillaautomation"):
            return {
                "url": f"""{reverse_lazy("automations:automation_create_view")}?new=true""",
                "attrs": {"id": "automation-create"},
            }
        return None

    @cached_property
    def actions(self):
        """Actions for mail automation"""
        if self.request.user.has_perm("automations.add_horillaautomation"):
            return [
                {
                    "action": _("Load Automation"),
                    "attrs": f"""
                            id="automation-load"
                            hx-get="{reverse_lazy("automations:load_automation")}"
                            hx-on:click="openModal();"
                            hx-target="#modalBox"
                            hx-swap="innerHTML"
                            """,
                },
            ]
        return None


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["automations.view_horillaautomation"]),
    name="dispatch",
)
class HorillaAutomationListView(LoginRequiredMixin, HorillaListView):
    """
    List view of automation
    """

    model = HorillaAutomation
    view_id = "automation-list"
    search_url = reverse_lazy("automations:automation_list_view")
    main_url = reverse_lazy("automations:automation_view")
    filterset_class = HorillaAutomationFilter
    bulk_update_two_column = True
    bulk_delete_enabled = False
    bulk_select_option = False
    list_column_visibility = False

    columns = [
        "title",
        "trigger",
        "model",
        (_("Template"), "get_template"),
        "delivery_channel",
    ]

    def get_queryset(self):
        """Exclude Big Deal Alert automations, which have their own dedicated list."""
        return super().get_queryset().exclude(additional_info__big_deal=True)

    def no_record_add_button(self):
        """Return configuration for the 'no records' Load Automation button when permitted."""
        if self.request.user.has_perm("automations.add_horillaautomation"):
            return {
                "url": f"""{reverse_lazy("automations:load_automation")}?new=true""",
                "attrs": 'id="automation-load"',
                "title": _("Load Automation"),
            }
        return None

    actions = [
        {
            "action": "Edit",
            "src": "assets/icons/edit.svg",
            "img_class": "w-4 h-4",
            "permission": "automations.change_horillaautomation",
            "attrs": """
                        hx-get="{get_edit_url}"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        onclick="openModal()"
                        """,
        },
        {
            "action": "Delete",
            "src": "assets/icons/a4.svg",
            "img_class": "w-4 h-4",
            "permission": "automations.delete_horillaautomation",
            "attrs": """
                    hx-get="{get_delete_url}"
                    hx-target="#deleteModeBox"
                    hx-swap="innerHTML"
                    hx-trigger="click"
                    hx-vals='{{"check_dependencies": "false"}}'
                    onclick="openDeleteModeModal()"
                """,
        },
    ]


@method_decorator(htmx_required, name="dispatch")
class HorillaAutomationFormView(LoginRequiredMixin, HorillaSingleFormView):
    """
    Form view for creating and updating automation
    """

    model = HorillaAutomation
    form_class = HorillaAutomationForm
    modal_height = False
    condition_fields = ["field", "operator", "value", "logical_operator"]
    condition_model = AutomationCondition
    condition_field_title = _("Condition")
    condition_hx_include = "#id_model"
    condition_related_name = "conditions"
    condition_order_by = ["order", "created_at"]
    content_type_field = "model"
    save_and_new = False

    def get_existing_conditions(self):
        """Return existing conditions excluding any that use excluded fields (e.g. password)."""
        qs = super().get_existing_conditions()
        if qs is None:
            return None
        return qs.exclude(field__in=AUTOMATION_CONDITION_EXCLUDED_FIELDS)

    @cached_property
    def form_url(self):
        """Get the URL for the form view."""
        pk = self.kwargs.get("pk") or self.request.GET.get("id")
        if pk:
            return reverse_lazy("automations:automation_update_view", kwargs={"pk": pk})
        return reverse_lazy("automations:automation_create_view")

    def get_initial(self):
        """Preserve filled values on HTMX reload; pass trigger/model for scheduled UI."""
        initial = super().get_initial()
        if self.request.method == "GET":
            # Preserve common form fields (HTMX trigger reload includes closest form)
            preserved_fields = [
                "title",
                "model",
                "mail_to",
                "also_sent_to",
                "trigger",
                "schedule_date_field",
                "schedule_offset_amount",
                "schedule_offset_direction",
                "schedule_offset_unit",
                "schedule_run_time",
                "delivery_channel",
                "mail_template",
                "notification_template",
                "mail_server",
            ]

            for name in preserved_fields:
                if name in self.request.GET:
                    values = self.request.GET.getlist(name)
                    initial[name] = values if len(values) > 1 else values[0]
        return initial

    def get_form_kwargs(self):
        """Pass form_url and HTMX target so trigger dropdown can reload form to show/hide schedule fields."""
        kwargs = super().get_form_kwargs()
        form_url = self.get_form_url()
        if hasattr(form_url, "url"):
            form_url = form_url.url
        kwargs["form_url"] = self.request.build_absolute_uri(form_url)
        view_id = (
            getattr(self, "view_id", None) or f"{self.model._meta.model_name}-form-view"
        )
        kwargs["htmx_trigger_target"] = f"#{view_id}-container"
        return kwargs

    def get_context_data(self, **kwargs):
        """Add form errors to delivery_channel hx-vals so get-template-fields returns them on load."""
        context = super().get_context_data(**kwargs)
        form = context.get("form")
        if (
            form
            and self.request.method == "POST"
            and not form.is_valid()
            and "delivery_channel" in form.fields
        ):
            mail_errors = form.errors.get("mail_template")
            notif_errors = form.errors.get("notification_template")
            mail_server_errors = form.errors.get("mail_server")
            if mail_errors or notif_errors or mail_server_errors:
                vals = {"automation_id": ""}
                if form.instance and form.instance.pk:
                    vals["automation_id"] = str(form.instance.pk)
                if mail_errors:
                    vals["mail_template_errors"] = list(mail_errors)
                if notif_errors:
                    vals["notification_template_errors"] = list(notif_errors)
                if mail_server_errors:
                    vals["mail_server_errors"] = list(mail_server_errors)
                form.fields["delivery_channel"].widget.attrs["hx-vals"] = json.dumps(
                    vals
                )
        return context


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "automations.add_horillaautomation",
            "automations.change_horillaautomation",
        ]
    ),
    name="dispatch",
)
class AutomationFieldChoicesView(LoginRequiredMixin, View):
    """
    Class-based view to return field choices for a selected model via HTMX.
    """

    def get(self, request, *args, **kwargs):
        """
        Handle GET request to return a <select> element with field choices.
        """
        model_id = request.GET.get("model")
        row_id = request.GET.get("row_id", "0")
        if not row_id.isdigit():
            row_id = "0"

        field_name = f"field_{row_id}"
        field_id = f"id_field_{row_id}"

        if model_id and model_id.isdigit():
            try:
                content_type = HorillaContentType.objects.get(pk=model_id)
                model_name = content_type.model
            except HorillaContentType.DoesNotExist:
                model_name = None
        else:
            model_name = None

        if not model_name:
            return render(
                request,
                "partials/field_select_empty.html",
                {"field_name": field_name, "field_id": field_id},
            )

        try:
            model = None
            for app_config in apps.get_app_configs():
                try:
                    model = apps.get_model(
                        app_label=app_config.label, model_name=model_name.lower()
                    )
                    break
                except LookupError:
                    continue
            if not model:
                return render(
                    request,
                    "partials/field_select_empty.html",
                    {"field_name": field_name, "field_id": field_id},
                )
        except Exception:
            return render(
                request,
                "partials/field_select_empty.html",
                {"field_name": field_name, "field_id": field_id},
            )

        model_fields = []
        # Use _meta.fields and _meta.many_to_many to get only forward fields (not reverse relations)
        # This excludes one-to-many and many-to-many reverse relationships
        all_forward_fields = list(model._meta.fields) + list(model._meta.many_to_many)

        for field in all_forward_fields:
            # Skip excluded fields (same list as edit form existing conditions filter)
            if field.name in AUTOMATION_CONDITION_EXCLUDED_FIELDS:
                continue
            # Skip non-editable fields (e.g. editable=False on the model)
            if not getattr(field, "editable", True):
                continue

            verbose_name = (
                getattr(field, "verbose_name", None)
                or field.name.replace("_", " ").title()
            )
            model_fields.append((field.name, verbose_name))

        field_choices = [("", "---------")] + model_fields

        condition_model_str = (
            f"{AutomationCondition._meta.app_label}."
            f"{AutomationCondition._meta.model_name}"
        )
        hx_vals_json = json.dumps(
            {
                "model_name": model_name,
                "row_id": row_id,
                "condition_model": condition_model_str,
            }
        )

        # Also update mail_to field using hx-swap-oob (pure HTMX)
        mail_to_html = self._get_mail_to_select_html(model_name, request)

        return render(
            request,
            "partials/automation_field_select_response.html",
            {
                "field_name": field_name,
                "field_id": field_id,
                "row_id": row_id,
                "hx_get_url": reverse_lazy("generics:get_field_value_widget"),
                "hx_vals_json": hx_vals_json,
                "field_choices": field_choices,
                "mail_to_html": mail_to_html,
            },
        )

    def _get_mail_to_select_html(self, model_name, request):
        """Helper method to generate mail_to select HTML with hx-swap-oob"""

        # Get current selected values if editing
        selected_values = []
        automation_id = request.GET.get("automation_id")
        if automation_id:
            try:
                automation = HorillaAutomation.objects.get(pk=automation_id)
                if automation.mail_to:
                    selected_values = [
                        v.strip() for v in automation.mail_to.split(",") if v.strip()
                    ]
            except HorillaAutomation.DoesNotExist:
                pass

        user_fields = [("self", "Self (User who triggered)")]

        if model_name:
            try:
                model = None
                for app_config in apps.get_app_configs():
                    try:
                        model = apps.get_model(
                            app_label=app_config.label, model_name=model_name.lower()
                        )
                        break
                    except LookupError:
                        continue

                if model:
                    for field in model._meta.get_fields():
                        if not hasattr(field, "name"):
                            continue

                        # Check if it's a ForeignKey to User
                        if isinstance(field, models.ForeignKey):
                            try:
                                related_model = field.related_model
                                is_user_model = False
                                if related_model:
                                    if related_model == User:
                                        is_user_model = True
                                    elif hasattr(related_model, "__bases__"):
                                        try:
                                            is_user_model = issubclass(
                                                related_model, User
                                            )
                                        except (TypeError, AttributeError):
                                            pass
                                    if not is_user_model:
                                        try:
                                            user_content_type = HorillaContentType.objects.get_for_model(
                                                User
                                            )
                                            field_content_type = HorillaContentType.objects.get_for_model(
                                                related_model
                                            )
                                            if user_content_type == field_content_type:
                                                is_user_model = True
                                        except Exception:
                                            pass
                                    if not is_user_model:
                                        user_model_names = ["user", "horillauser"]
                                        if hasattr(settings, "AUTH_USER_MODEL"):
                                            user_model_names.append(
                                                settings.AUTH_USER_MODEL.split(".")[
                                                    -1
                                                ].lower()
                                            )
                                        if (
                                            related_model.__name__.lower()
                                            in user_model_names
                                        ):
                                            is_user_model = True

                                if is_user_model:
                                    verbose_name = (
                                        getattr(field, "verbose_name", None)
                                        or field.name.replace("_", " ").title()
                                    )
                                    user_fields.append(
                                        (f"instance.{field.name}", verbose_name)
                                    )
                            except Exception:
                                continue

                        # Also check for email fields (EmailField or CharField with 'email' in name)
                        elif isinstance(field, (models.EmailField, models.CharField)):
                            if "email" in field.name.lower():
                                verbose_name = (
                                    getattr(field, "verbose_name", None)
                                    or field.name.replace("_", " ").title()
                                )
                                user_fields.append(
                                    (f"instance.{field.name}", verbose_name)
                                )
            except Exception:
                pass

        # Build options HTML
        options_html = ""
        for value, label in user_fields:
            selected = ' selected="selected"' if value in selected_values else ""
            escaped_value = escape(str(value))
            escaped_label = escape(str(label))
            options_html += (
                f'<option value="{escaped_value}"{selected}>{escaped_label}</option>'
            )

        # Return select with hx-swap-oob for out-of-band swap
        # The target selector is #mail_to_container select, so HTMX will find it and swap it
        select_html = f'<select name="mail_to" id="id_mail_to" class="js-example-basic-multiple headselect w-full" multiple="multiple" data-placeholder="{_("Select user fields")}" hx-swap-oob="outerHTML">{options_html}</select>'

        return select_html


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "automations.view_horillaautomation",
            "automations.add_horillaautomation",
        ],
    ),
    name="dispatch",
)
class MailToChoicesView(LoginRequiredMixin, View):
    """
    Class-based view to return User ForeignKey field choices for mail_to field via HTMX.
    """

    def get(self, request, *args, **kwargs):
        """
        Handle GET request to return a <select multiple> element with User ForeignKey field choices.
        """
        model_id = request.GET.get("model")
        if model_id and model_id.isdigit():
            try:
                content_type = HorillaContentType.objects.get(pk=model_id)
                model_name = content_type.model
            except HorillaContentType.DoesNotExist:
                model_name = None
        else:
            model_name = None

        if not model_name:
            # Return empty select with just self option (template renders safely)
            return render(
                request,
                "partials/mail_to_select_response.html",
                {
                    "user_fields": [("self", "Self (User who triggered)")],
                    "selected_values": [],
                    "include_select2_script": True,
                },
            )

        try:
            model = None
            for app_config in apps.get_app_configs():
                try:
                    model = apps.get_model(
                        app_label=app_config.label, model_name=model_name.lower()
                    )
                    break
                except LookupError:
                    continue
            if not model:
                return render(
                    request,
                    "partials/mail_to_select_response.html",
                    {
                        "user_fields": [("self", "Self (User who triggered)")],
                        "selected_values": [],
                        "include_select2_script": True,
                    },
                )
        except Exception:
            return render(
                request,
                "partials/mail_to_select_response.html",
                {
                    "user_fields": [("self", "Self (User who triggered)")],
                    "selected_values": [],
                    "include_select2_script": True,
                },
            )

        # Get User ForeignKey fields
        user_fields = [("self", "Self (User who triggered)")]

        for field in model._meta.get_fields():
            if not hasattr(field, "name"):
                continue
            # Check if it's a ForeignKey to User
            if isinstance(field, models.ForeignKey):
                try:
                    related_model = field.related_model
                    # Check if related_model is User or a subclass
                    is_user_model = False
                    if related_model:
                        # Direct comparison
                        if related_model == User:
                            is_user_model = True
                        # Check if it's a subclass
                        elif hasattr(related_model, "__bases__"):
                            try:
                                is_user_model = issubclass(related_model, User)
                            except (TypeError, AttributeError):
                                pass
                        # Check using HorillaContentType (most reliable method)
                        if not is_user_model:
                            try:
                                user_content_type = (
                                    HorillaContentType.objects.get_for_model(User)
                                )
                                field_content_type = (
                                    HorillaContentType.objects.get_for_model(
                                        related_model
                                    )
                                )
                                if user_content_type == field_content_type:
                                    is_user_model = True
                            except Exception:
                                pass

                        # Also check the model name and AUTH_USER_MODEL as fallback
                        if not is_user_model:
                            user_model_names = ["user", "horillauser"]
                            if hasattr(settings, "AUTH_USER_MODEL"):
                                user_model_names.append(
                                    settings.AUTH_USER_MODEL.split(".")[-1].lower()
                                )
                            if related_model.__name__.lower() in user_model_names:
                                is_user_model = True

                    if is_user_model:
                        verbose_name = (
                            getattr(field, "verbose_name", None)
                            or field.name.replace("_", " ").title()
                        )
                        user_fields.append((f"instance.{field.name}", verbose_name))
                except Exception:
                    # Print error for debugging but continue
                    continue

            # Also check for email fields (EmailField or CharField with 'email' in name)
            elif isinstance(field, (models.EmailField, models.CharField)):
                if "email" in field.name.lower():
                    verbose_name = (
                        getattr(field, "verbose_name", None)
                        or field.name.replace("_", " ").title()
                    )
                    user_fields.append((f"instance.{field.name}", verbose_name))

        # Get current selected values if editing
        selected_values = []
        automation_id = request.GET.get("automation_id")
        if automation_id:
            try:
                automation = HorillaAutomation.objects.get(pk=automation_id)
                if automation.mail_to:
                    selected_values = [
                        v.strip() for v in automation.mail_to.split(",") if v.strip()
                    ]
            except HorillaAutomation.DoesNotExist:
                pass

        if not user_fields:
            user_fields = [("self", "Self (User who triggered)")]

        return render(
            request,
            "partials/mail_to_select_response.html",
            {
                "user_fields": user_fields,
                "selected_values": selected_values,
                "include_select2_script": False,
            },
        )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("automations.delete_horillaautomation", modal=True),
    name="dispatch",
)
class HorillaAutomationDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):
    """
    Delete view for HorillaAutomation
    """

    model = HorillaAutomation

    def get_post_delete_response(self):
        """Return response after successful deletion"""
        return ScriptResponse(reload=True)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "automations.view_horillaautomation",
            "automations.add_horillaautomation",
        ],
    ),
    name="dispatch",
)
class TemplateFieldsView(LoginRequiredMixin, View):
    """
    HTMX view to return template fields based on delivery_channel
    """

    def get(self, request, *args, **kwargs):
        """
        Handle GET request to return template field HTML based on delivery_channel
        """
        delivery_channel = request.GET.get("delivery_channel", "mail")
        automation_id = request.GET.get("automation_id")
        model_id = request.GET.get("model")

        # Pass through form errors when load is triggered after failed submit (so OOB swap keeps them)
        mail_template_errors = []
        notification_template_errors = []
        mail_server_errors = []
        raw_mail = request.GET.get("mail_template_errors")
        raw_notif = request.GET.get("notification_template_errors")
        raw_mail_server = request.GET.get("mail_server_errors")
        if raw_mail is not None:
            if isinstance(raw_mail, str) and raw_mail.startswith("["):
                try:
                    mail_template_errors = json.loads(raw_mail)
                except (ValueError, TypeError):
                    mail_template_errors = [raw_mail]
            else:
                mail_template_errors = request.GET.getlist("mail_template_errors") or [
                    raw_mail
                ]
        if raw_notif is not None:
            if isinstance(raw_notif, str) and raw_notif.startswith("["):
                try:
                    notification_template_errors = json.loads(raw_notif)
                except (ValueError, TypeError):
                    notification_template_errors = [raw_notif]
            else:
                notification_template_errors = request.GET.getlist(
                    "notification_template_errors"
                ) or [raw_notif]
        if raw_mail_server is not None:
            if isinstance(raw_mail_server, str) and raw_mail_server.startswith("["):
                try:
                    mail_server_errors = json.loads(raw_mail_server)
                except (ValueError, TypeError):
                    mail_server_errors = [raw_mail_server]
            else:
                mail_server_errors = request.GET.getlist("mail_server_errors") or [
                    raw_mail_server
                ]

        # Get content_type from model_id if provided
        content_type = None
        if model_id:
            try:
                content_type = HorillaContentType.objects.get(pk=model_id)
            except (HorillaContentType.DoesNotExist, ValueError):
                pass

        # Get current values if editing
        mail_template_id = None
        notification_template_id = None
        mail_server_id = None
        if automation_id:
            try:
                automation = HorillaAutomation.objects.get(pk=automation_id)
                if automation.mail_template:
                    mail_template_id = automation.mail_template.pk
                if automation.notification_template:
                    notification_template_id = automation.notification_template.pk
                if automation.mail_server:
                    mail_server_id = automation.mail_server.pk
                # Get content_type from automation if not in request
                if not content_type and automation.model:
                    content_type = automation.model
            except HorillaAutomation.DoesNotExist:
                pass

        company = request.active_company

        if not company:
            company = request.user.company

        show_mail = delivery_channel in ["mail", "both"]
        show_notification = delivery_channel in ["notification", "both"]

        mail_templates_qs = HorillaMailTemplate.objects.none()
        if show_mail:
            mail_templates_qs = HorillaMailTemplate.objects.all()
            if company:
                mail_templates_qs = mail_templates_qs.filter(company=company)
            if content_type:
                mail_templates_qs = mail_templates_qs.filter(
                    Q(content_type=content_type) | Q(content_type__isnull=True)
                )

        notification_templates_qs = NotificationTemplate.objects.none()
        if show_notification:
            notification_templates_qs = NotificationTemplate.objects.all()
            if company:
                notification_templates_qs = notification_templates_qs.filter(
                    company=company
                )
            if content_type:
                notification_templates_qs = notification_templates_qs.filter(
                    Q(content_type=content_type) | Q(content_type__isnull=True)
                )

        mail_servers_qs = HorillaMailConfiguration.objects.none()
        if show_mail:
            mail_servers_qs = HorillaMailConfiguration.objects.filter(
                mail_channel="outgoing"
            )
            if company:
                mail_servers_qs = mail_servers_qs.filter(company=company)

        # Use model field verbose_name for labels (consistent with form and i18n)
        mail_template_label = HorillaAutomation._meta.get_field(
            "mail_template"
        ).verbose_name
        notification_template_label = HorillaAutomation._meta.get_field(
            "notification_template"
        ).verbose_name
        mail_server_label = HorillaAutomation._meta.get_field(
            "mail_server"
        ).verbose_name

        return render(
            request,
            "partials/template_fields_response.html",
            {
                "show_mail_template": show_mail,
                "show_notification_template": show_notification,
                "show_mail_server": show_mail,
                "mail_templates": mail_templates_qs,
                "notification_templates": notification_templates_qs,
                "mail_servers": mail_servers_qs,
                "mail_template_id": mail_template_id,
                "notification_template_id": notification_template_id,
                "mail_server_id": mail_server_id,
                "mail_template_label": mail_template_label,
                "notification_template_label": notification_template_label,
                "mail_server_label": mail_server_label,
                "mail_template_errors": mail_template_errors,
                "notification_template_errors": notification_template_errors,
                "mail_server_errors": mail_server_errors,
            },
        )
