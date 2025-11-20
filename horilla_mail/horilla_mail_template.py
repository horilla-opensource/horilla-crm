from functools import cached_property

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, FormView, TemplateView

from horilla.exceptions import HorillaHttp404
from horilla_core.decorators import htmx_required, permission_required_or_denied
from horilla_generics.views import (
    HorillaListView,
    HorillaNavView,
    HorillaSingleDeleteView,
    HorillaView,
)
from horilla_mail.filters import HorillaMailTemplateFilter
from horilla_mail.forms import (
    HorillaMailTemplateForm,
    MailTemplateSelectForm,
    SaveAsMailTemplateForm,
)
from horilla_mail.models import HorillaMailTemplate
from horilla_utils.middlewares import _thread_local


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailtemplate"]),
    name="dispatch",
)
class MailTemplateView(LoginRequiredMixin, HorillaView):
    """
    TemplateView for mail server page.
    """

    template_name = "mail_template/mail_template_view.html"
    nav_url = reverse_lazy("horilla_mail:mail_template_navbar_view")
    list_url = reverse_lazy("horilla_mail:mail_template_list_view")


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailtemplate"]),
    name="dispatch",
)
class MailTemplateNavbar(LoginRequiredMixin, HorillaNavView):
    """
    navbar view for mail server
    """

    nav_title = HorillaMailTemplate._meta.verbose_name_plural
    search_url = reverse_lazy("horilla_mail:mail_template_list_view")
    main_url = reverse_lazy("horilla_mail:mail_template_view")
    model_name = "HorillaMailTemplate"
    model_app_label = "horilla_mail"
    nav_width = False
    gap_enabled = False
    all_view_types = False
    one_view_only = True
    filter_option = False
    reload_option = False

    @cached_property
    def new_button(self):
        if self.request.user.has_perm("horilla_mail.add_horillamailtemplate"):
            return {
                "url": f"""{ reverse_lazy('horilla_mail:mail_template_create_view')}""",
                "target": "#horillaModalBox",
                "onclick": "openhorillaModal();",
                "attrs": {"id": "mail-template-create"},
            }


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailtemplate"]),
    name="dispatch",
)
class MailTemplateListView(LoginRequiredMixin, HorillaListView):
    """
    List view of mail server
    """

    model = HorillaMailTemplate
    view_id = "mail-template-list"
    search_url = reverse_lazy("horilla_mail:mail_template_list_view")
    main_url = reverse_lazy("horilla_mail:mail_template_view")
    bulk_update_two_column = True
    table_width = False
    bulk_delete_enabled = False
    table_height_as_class = "h-[500px]"
    bulk_select_option = False
    list_column_visibility = False
    filterset_class = HorillaMailTemplateFilter

    def no_record_add_button(self):
        if self.request.user.has_perm("horilla_mail.add_horillamailtemplate"):
            return {
                "url": f"""{ reverse_lazy('horilla_mail:mail_template_create_view')}""",
                "target": "#horillaModalBox",
                "onclick": "openhorillaModal();",
                "attrs": {"id": "mail-template-create"},
            }

    columns = ["title", (_("Related Model"), "get_related_model")]

    @cached_property
    def actions(self):
        instance = self.model()
        actions = []
        if self.request.user.has_perm("horilla_mail.change_horillaemailconfiguration"):
            actions.append(
                {
                    "action": "Edit",
                    "src": "assets/icons/edit.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                            hx-get="{get_edit_url}"
                            hx-target="#horillaModalBox"
                            hx-swap="innerHTML"
                            onclick="openhorillaModal()"
                            """,
                },
            )
        if self.request.user.has_perm("horilla_mail.delete_horillaemailconfiguration"):
            actions.append(
                {
                    "action": "Delete",
                    "src": "assets/icons/a4.svg",
                    "img_class": "w-4 h-4",
                    "attrs": """
                        hx-post="{get_delete_url}"
                        hx-target="#modalBox"
                        hx-swap="innerHTML"
                        hx-trigger="click"
                        hx-vals='{{"check_dependencies": "false"}}'
                        onclick="openModal()"
                    """,
                }
            )
        return actions

    @cached_property
    def raw_attrs(self):
        if self.request.user.has_perm("horilla_mail.view_horillamailtemplate"):
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
    permission_required_or_denied(["horilla_mail.add_horillamailtemplate"]),
    name="dispatch",
)
class MailTemplateCreateUpdateView(LoginRequiredMixin, FormView):
    """
    FormView for creating and updating Horilla Mail Template
    """

    form_class = HorillaMailTemplateForm
    template_name = "mail_template/mail_template_form.html"

    def dispatch(self, request, *args, **kwargs):

        self.template_id = kwargs.get("pk")
        if self.template_id:
            try:
                self.object = get_object_or_404(
                    HorillaMailTemplate, pk=self.template_id
                )
            except:
                messages.error(
                    request,
                    f"{HorillaMailTemplate._meta.verbose_name.title()} not found or no longer exists.",
                )
                return HttpResponse(
                    "<script>$('#reloadButton').click();closeModal();</script>"
                )
        else:
            self.object = None
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.object:
            kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object:
            context["form_title"] = _("Update Mail Template")
            context["submit_text"] = _("Update Template")

        else:
            context["form_title"] = _("Create Mail Template")
            context["submit_text"] = _("Save Template")

        context["action_url"] = self.get_form_action_url()
        return context

    def get_form_action_url(self):
        """Get the appropriate URL for form submission"""
        if self.object:
            return reverse(
                "horilla_mail:mail_template_update_view", kwargs={"pk": self.object.pk}
            )
        return reverse("horilla_mail:mail_template_create_view")

    def form_valid(self, form):
        try:
            mail_template = form.save(commit=False)
            mail_template.company = (
                getattr(_thread_local, "request", None).active_company
                if hasattr(_thread_local, "request")
                else self.request.user.company
            )
            mail_template.save()
            if self.object:
                messages.success(
                    self.request,
                    _('Mail template "{}" updated successfully.').format(
                        mail_template.title
                    ),
                )
            else:
                messages.success(
                    self.request,
                    _('Mail template "{}" created successfully.').format(
                        mail_template.title
                    ),
                )

            return HttpResponse(
                "<script>$('#reloadButton').click();closehorillaModal();</script>"
            )

        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Please correct the errors below."))
        return super().form_invalid(form)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailtemplate"]),
    name="dispatch",
)
class MailTemplatePreviewView(LoginRequiredMixin, TemplateView):
    """
    View for previewing mail template body content via HTMX
    """

    template_name = "mail_template/template_preview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        """Handle POST for large body content"""
        context = self.get_context_data(**kwargs)
        body_content = request.POST.get("body")
        if body_content:
            context["body"] = mark_safe(body_content)
        return self.render_to_response(context)


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailtemplate"]),
    name="dispatch",
)
class TemplateContentView(LoginRequiredMixin, View):
    """Get template content by ID via AJAX"""

    def get(self, request, *args, **kwargs):
        template_id = request.GET.get("template_id")

        if not template_id:
            return JsonResponse(
                {
                    "success": False,
                }
            )

        try:
            queryset = HorillaMailTemplate.objects.all()
            template = get_object_or_404(queryset, id=template_id)

            return JsonResponse(
                {"success": True, "body": template.body, "title": template.title}
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailtemplate"]),
    name="dispatch",
)
class MailTemplateSelectView(LoginRequiredMixin, View):
    template_name = "mail_template/select_mail_template.html"

    def get(self, request, *args, **kwargs):
        model_name = request.GET.get("model_name")
        form = MailTemplateSelectForm(model_name=model_name)
        return render(
            request, self.template_name, {"form": form, "model_name": model_name}
        )


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailtemplate"]),
    name="dispatch",
)
class SaveAsMailTemplateView(LoginRequiredMixin, View):
    template_name = "mail_template/save_mail_template.html"

    def post(self, request, *args, **kwargs):
        model_name = request.GET.get("model_name", "") or request.POST.get(
            "model_name", ""
        )
        message_content = request.POST.get("message_content", "")

        csrf_token = request.POST.get("csrfmiddlewaretoken")

        if not csrf_token:
            form = SaveAsMailTemplateForm()
            empty_body_error = None

            if (
                not message_content
                or message_content.strip() == ""
                or message_content == "<p><br></p>"
            ):
                empty_body_error = "Message content cannot be empty"

            context = {
                "form": form,
                "model_name": model_name,
                "message_content": message_content,
                "errors": form.errors,
                "empty_body_error": empty_body_error,
            }
            return render(request, self.template_name, context)

        # Form submission with title - validate everything
        data = request.POST.copy()
        if message_content:
            data["body"] = message_content

        form = SaveAsMailTemplateForm(data)

        # Check for empty body
        empty_body_error = None
        if (
            not message_content
            or message_content.strip() == ""
            or message_content == "<p><br></p>"
        ):
            empty_body_error = "Message content cannot be empty"

        # Only proceed if form is valid AND no empty body error
        if form.is_valid() and not empty_body_error:
            try:
                instance = form.save(commit=False)
                model_name = request.POST.get("model_name")
                instance.content_type = ContentType.objects.get(
                    model=model_name.lower()
                )
                instance.company = (
                    getattr(_thread_local, "request", None).active_company
                    if hasattr(_thread_local, "request")
                    else self.request.user.company
                )
                instance.save()
                messages.success(
                    self.request,
                    _('Mail template "{}" created successfully.').format(
                        instance.title
                    ),
                )
                return HttpResponse(
                    "<script>closeModal();$('#reloadMessagesButton').click();</script>"
                )

            except IntegrityError:
                form.add_error(
                    None, "A template with this title already exists for this company."
                )
            except Exception as e:
                form.add_error(None, "A database error occurred. Please try again.")

        context = {
            "form": form,
            "model_name": request.POST.get("model_name", ""),
            "message_content": message_content,
            "errors": form.errors,
            "empty_body_error": empty_body_error,
        }
        return render(request, self.template_name, context)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(["horilla_mail.delete_horillamailtemplate"]),
    name="dispatch",
)
class MailTemplateDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):

    model = HorillaMailTemplate

    def get_post_delete_response(self):
        return HttpResponse("<script>$('#reloadButton').click();</script>")


@method_decorator(
    permission_required_or_denied(["horilla_mail.view_horillamailtemplate"]),
    name="dispatch",
)
class MailTemplateDetailView(LoginRequiredMixin, DetailView):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        try:
            self.object = self.get_object()
        except Exception as e:
            if request.headers.get("HX-Request") == "true":
                messages.error(self.request, e)
                return HttpResponse(headers={"HX-Refresh": "true"})
            raise HorillaHttp404(e)
        return super().dispatch(request, *args, **kwargs)

    model = HorillaMailTemplate
    template_name = "mail_template/mail_template_detail.html"
    context_object_name = "mail_template"
