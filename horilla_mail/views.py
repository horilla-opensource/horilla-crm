import base64
import html
import logging
import re
from datetime import datetime

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils import timezone as django_timezone
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from horilla_core.decorators import htmx_required, permission_required_or_denied
from horilla_generics.views import HorillaSingleDeleteView
from horilla_mail.models import (
    HorillaMail,
    HorillaMailAttachment,
    HorillaMailConfiguration,
)
from horilla_mail.services import HorillaMailManager
from horilla_utils.middlewares import _thread_local

logger = logging.getLogger(__name__)


def parse_email_pills_context(email_string, field_type):
    """
    Helper function to parse email strings into pills context
    """
    email_list = []
    if email_string:
        email_list = [e.strip() for e in email_string.split(",") if e.strip()]

    return {
        "email_list": email_list,
        "email_string": email_string or "",
        "field_type": field_type,
        "current_search": "",
    }


def extract_inline_images_with_cid(html_content):
    """Extract base64 inline images and replace with CID references."""
    if not html_content:
        return html_content, []

    inline_images = []
    img_pattern = (
        r'<img([^>]*)src=["\']data:image/([^;]+);base64,([^"\']+)["\']([^>]*)>'
    )

    def replace_img(match):
        before_src = match.group(1)
        image_format = match.group(2)
        base64_data = match.group(3)
        after_src = match.group(4)

        try:
            image_data = base64.b64decode(base64_data)
            cid = f"inline_image_{len(inline_images) + 1}"
            filename = f"{cid}.{image_format}"
            content_file = ContentFile(image_data, name=filename)
            inline_images.append((content_file, cid))
            return f'<img{before_src}src="cid:{cid}"{after_src}>'
        except Exception as e:
            logger.error(f"Error processing inline image: {e}")
            return match.group(0)

    cleaned_html = re.sub(img_pattern, replace_img, html_content, flags=re.IGNORECASE)
    return cleaned_html, inline_images


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.view_horillamailconfiguration",
            "horilla_mail.add_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class HorillaMailFormView(LoginRequiredMixin, TemplateView):
    """
    Send mail form view - automatically creates a draft mail
    """

    template_name = "mail_form.html"

    def get(self, request, *args, **kwargs):
        pk = kwargs.get("pk") or request.GET.get("pk")
        cancel = self.request.GET.get("cancel") == "true"
        if pk:
            try:
                draft_mail = HorillaMail.objects.get(pk=pk)
                if cancel:
                    draft_mail.mail_status = "draft"
                    draft_mail.save()
            except Exception as e:
                messages.error(self.request, e)
                return HttpResponse(
                    "<script>$('reloadButton').click();closeModal();</script>"
                )

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        try:

            to_email = request.POST.get("to_email", "")
            cc_email = request.POST.get("cc_email", "")
            bcc_email = request.POST.get("bcc_email", "")
            subject = request.POST.get("subject", "")
            message_content = request.POST.get("message_content", "")
            from_mail_id = request.POST.get("from_mail")
            uploaded_files = request.FILES.getlist("attachments")
            model_name = request.GET.get("model_name")
            object_id = request.GET.get("object_id")
            pk = request.GET.get("pk")

            company = getattr(request, "active_company", None)
            setattr(_thread_local, "from_mail_id", from_mail_id)
            missing_fields = []
            if not to_email:
                missing_fields.append("To email")
            if not from_mail_id:
                missing_fields.append("From mail configuration")

            if missing_fields:
                messages.error(
                    request, _("Missing required fields: ") + ", ".join(missing_fields)
                )
                return HttpResponse(
                    "<script>closehorillaModal();htmx.trigger('#reloadButton','click');</script>"
                )

            validation_errors = {}
            if message_content and HorillaMail.has_xss(message_content):
                validation_errors["body"] = _(
                    "Message body contains potentially dangerous content (XSS detected). Please remove any scripts or malicious code."
                )

            if validation_errors:
                context = self.get_context_data(**kwargs)

                context["validation_errors"] = validation_errors
                context["subject"] = subject
                context["message_content"] = message_content
                context["form_data"] = {
                    "to_email": to_email,
                    "cc_email": cc_email,
                    "bcc_email": bcc_email,
                    "subject": subject,
                    "message_content": message_content,
                    "from_mail_id": from_mail_id,
                }

                context["to_pills"] = parse_email_pills_context(to_email or "", "to")
                context["cc_pills"] = parse_email_pills_context(cc_email or "", "cc")
                context["bcc_pills"] = parse_email_pills_context(bcc_email or "", "bcc")
                response = self.render_to_response(context)
                response["HX-Select"] = "#send-mail-container"
                return response

            try:
                from_mail_config = HorillaMailConfiguration.objects.get(id=from_mail_id)
            except HorillaMailConfiguration.DoesNotExist:
                return JsonResponse(
                    {"success": False, "message": "Invalid mail configuration selected"}
                )

            content_type = None
            if model_name and object_id:
                try:
                    content_type = ContentType.objects.get(model=model_name.lower())
                except ContentType.DoesNotExist:
                    messages.error(request, f"Invalid model name: {model_name}")
                    return HttpResponse(
                        "<script>closehorillaModal();htmx.trigger('#reloadButton','click');</script>"
                    )

            draft_mail = None
            if content_type and object_id:
                try:
                    draft_mail = HorillaMail.objects.filter(
                        pk=pk,
                        content_type=content_type,
                        object_id=object_id,
                        mail_status="draft",
                        created_by=request.user,
                    ).first()
                except Exception as e:
                    logger.error(f"Error finding draft: {e}")

            if not draft_mail:
                draft_mail = HorillaMail.objects.create(
                    content_type=content_type,
                    object_id=object_id or 0,
                    mail_status="draft",
                    created_by=request.user,
                    sender=from_mail_config,
                    company=company,
                )

            cleaned_message_content, inline_images = extract_inline_images_with_cid(
                message_content
            )

            draft_mail.sender = from_mail_config
            draft_mail.to = to_email
            draft_mail.cc = cc_email if cc_email else None
            draft_mail.bcc = bcc_email if bcc_email else None
            draft_mail.subject = subject if subject else None
            draft_mail.body = (
                cleaned_message_content if cleaned_message_content else None
            )
            draft_mail.save()

            if draft_mail.pk:
                for f in uploaded_files:
                    attachment = HorillaMailAttachment(
                        mail=draft_mail, file=f, company=company
                    )
                    attachment.save()

                for img_file, cid in inline_images:
                    attachment = HorillaMailAttachment(
                        mail=draft_mail,
                        file=img_file,
                        company=company,
                        is_inline=True,
                        content_id=cid,
                    )
                    attachment.save()

            template_context = {}

            template_context["user"] = request.user
            template_context["request"] = request

            if hasattr(request, "active_company") and request.active_company:
                template_context["active_company"] = (request.active_company,)

            if content_type and object_id:
                try:
                    model_class = apps.get_model(
                        app_label=content_type.app_label, model_name=content_type.model
                    )
                    related_object = model_class.objects.get(pk=object_id)
                    template_context["instance"] = related_object
                except Exception as e:
                    logger.error(f"Error getting related object: {e}")

            HorillaMailManager.send_mail(draft_mail, template_context)
            draft_mail.refresh_from_db()
            if draft_mail.mail_status == "sent":
                messages.success(request, _("Mail sent successfully"))
                return HttpResponse(
                    "<script>closehorillaModal();htmx.trigger('#sent-email-tab','click');</script>"
                )
            else:
                messages.error(
                    request, _("Failed to send mail: ") + draft_mail.mail_status_message
                )
                return HttpResponse(
                    "<script>closehorillaModal();htmx.trigger('#sent-email-tab','click');</script>"
                )

        except Exception as e:
            import traceback

            logger.error(traceback.format_exc())

            messages.error(request, _("Error sending mail: ") + str(e))
            return HttpResponse(
                "<script>closehorillaModal();htmx.trigger('#reloadButton','click');</script>"
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        draft_mail = None

        model_name = self.request.GET.get("model_name")
        object_id = self.request.GET.get("object_id")
        pk = kwargs.get("pk")
        primary_mail_config = HorillaMailConfiguration.objects.filter(
            is_primary=True
        ).first()
        if not primary_mail_config:
            primary_mail_config = HorillaMailConfiguration.objects.first()
        all_mail_configs = HorillaMailConfiguration.objects.filter(
            mail_channel="outgoing"
        )

        if pk:
            draft_mail = HorillaMail.objects.filter(pk=pk).first()

        else:
            if model_name and object_id:
                try:
                    content_type = ContentType.objects.get(model=model_name.lower())

                    company = getattr(self.request, "active_company", None)

                    try:
                        draft_mail = HorillaMail.objects.create(
                            content_type=content_type,
                            created_by=self.request.user,
                            object_id=object_id,
                            mail_status="draft",
                            sender=primary_mail_config,
                            company=company,
                        )
                        created = True

                        if created:
                            try:
                                model_class = apps.get_model(
                                    app_label=content_type.app_label,
                                    model_name=content_type.model,
                                )
                                related_object = model_class.objects.get(pk=object_id)

                                # Try to find an email field in the related object
                                email_value = None
                                for field in related_object._meta.get_fields():
                                    if (
                                        "email" in field.name.lower()
                                        or field.__class__.__name__ == "EmailField"
                                    ):
                                        email_value = getattr(
                                            related_object, field.name, None
                                        )
                                        if email_value:
                                            break

                                # If we found an email, set it in the draft
                                if email_value:
                                    draft_mail.to = email_value
                                    draft_mail.save()

                            except Exception as e:
                                logger.error(f"Error setting related object email: {e}")

                    except Exception as e:
                        logger.error(str(e))

                    try:
                        model_class = apps.get_model(
                            app_label=content_type.app_label,
                            model_name=content_type.model,
                        )
                        related_object = model_class.objects.get(pk=object_id)
                        context["related_object"] = related_object
                    except Exception as e:
                        context["related_object"] = None

                except ContentType.DoesNotExist:
                    pass
                except Exception as e:
                    pass
        existing_attachments = draft_mail.attachments.all() if draft_mail else []
        context["existing_attachments"] = existing_attachments
        context["message_content"] = draft_mail.body if draft_mail.body else ""
        context["subject"] = draft_mail.subject if draft_mail.subject else ""
        model_name = None
        model_name = draft_mail.content_type if draft_mail else None
        if draft_mail:
            model_name = model_name.model.capitalize()
        context["model_name"] = model_name
        context["object_id"] = draft_mail.object_id if draft_mail else None
        context["pk"] = draft_mail.pk if draft_mail else None
        context["draft_mail"] = draft_mail
        context["primary_mail_config"] = primary_mail_config
        context["all_mail_configs"] = all_mail_configs
        context["model_name"] = model_name
        context["to_pills"] = parse_email_pills_context(
            draft_mail.to if draft_mail else "", "to"
        )
        context["cc_pills"] = parse_email_pills_context(
            draft_mail.cc if draft_mail else "", "cc"
        )
        context["bcc_pills"] = parse_email_pills_context(
            draft_mail.bcc if draft_mail else "", "bcc"
        )
        return context


@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.change_horillamailconfiguration",
            "horilla_mail.add_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class AddEmailView(LoginRequiredMixin, View):
    """
    View to add email as a pill and clear search input
    """

    def post(self, request, *args, **kwargs):
        email = request.POST.get("email", "").strip()
        field_type = request.POST.get("field_type", "to")
        current_email_list = request.POST.get(f"{field_type}_email_list", "")

        if current_email_list:
            email_list = [e.strip() for e in current_email_list.split(",") if e.strip()]
        else:
            email_list = []

        if email and email not in email_list:
            email_list.append(email)

        email_string = ", ".join(email_list)

        context = {
            "email_list": email_list,
            "email_string": email_string,
            "field_type": field_type,
            "current_search": "",
        }

        return render(request, "email_pills_field.html", context)


@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.change_horillamailconfiguration",
            "horilla_mail.add_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class RemoveEmailView(LoginRequiredMixin, View):
    """
    View to remove specific email pill
    """

    def post(self, request, *args, **kwargs):
        email_to_remove = request.POST.get("email_to_remove", "").strip()
        field_type = request.POST.get("field_type", "to")
        current_email_list = request.POST.get(f"{field_type}_email_list", "")

        if current_email_list:
            email_list = [e.strip() for e in current_email_list.split(",") if e.strip()]
        else:
            email_list = []

        if email_to_remove in email_list:
            email_list.remove(email_to_remove)

        email_string = ", ".join(email_list)

        context = {
            "email_list": email_list,
            "email_string": email_string,
            "field_type": field_type,
            "current_search": "",
        }

        return render(request, "email_pills_field.html", context)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.change_horillamailconfiguration",
            "horilla_mail.view_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class EmailSuggestionView(LoginRequiredMixin, View):
    """
    View to get email suggestions (updated to work with pills)
    """

    def get_all_emails_from_models(self):
        """
        Extract all email addresses from all models in the project
        """
        all_emails = set()

        for model in apps.get_models():
            model_name = model._meta.model_name.lower()
            if model_name in [
                "session",
                "contenttype",
                "permission",
                "group",
                "logentry",
            ]:
                continue

            for field in model._meta.get_fields():
                if (
                    "email" in field.name.lower()
                    or field.__class__.__name__ == "EmailField"
                ):

                    try:
                        values = model.objects.values_list(
                            field.name, flat=True
                        ).distinct()
                        for value in values:
                            if value and "@" in str(value):
                                self._extract_emails_from_string(str(value), all_emails)
                    except Exception as e:
                        continue

        try:
            from .models import HorillaMail

            for field_name in ["to", "cc", "bcc"]:
                try:
                    email_values = HorillaMail.objects.values_list(
                        field_name, flat=True
                    ).distinct()
                    for email_string in email_values:
                        if email_string:
                            self._extract_emails_from_string(email_string, all_emails)
                except Exception:
                    continue

        except ImportError:
            pass

        valid_emails = []
        for email in all_emails:
            if self._is_valid_email(email):
                valid_emails.append(email.lower())

        return sorted(list(set(valid_emails)))

    def _extract_emails_from_string(self, email_string, email_set):
        """
        Extract individual emails from a string that might contain multiple emails
        """
        if "," in email_string:
            emails = [email.strip() for email in email_string.split(",")]
            email_set.update(emails)
        elif ";" in email_string:
            emails = [email.strip() for email in email_string.split(";")]
            email_set.update(emails)
        else:
            email_set.add(email_string.strip())

    def _is_valid_email(self, email):
        """
        Basic email validation
        """
        if not email or len(email) < 5:
            return False
        if "@" not in email:
            return False
        parts = email.split("@")
        if len(parts) != 2:
            return False
        if "." not in parts[1]:
            return False
        return True

    def get(self, request, *args, **kwargs):
        """
        Return email suggestions based on search query
        """
        field_type = request.GET.get("field", "to")
        current_input = request.GET.get(f"{field_type}_email_input", "").strip()
        current_email_list = request.GET.get(f"{field_type}_email_list", "")

        existing_emails = []
        if current_email_list:
            existing_emails = [
                e.strip().lower() for e in current_email_list.split(",") if e.strip()
            ]

        all_emails = self.get_all_emails_from_models()

        available_emails = [
            email for email in all_emails if email.lower() not in existing_emails
        ]

        if current_input:
            search_lower = current_input.lower()
            filtered_emails = [
                email for email in available_emails if search_lower in email.lower()
            ]
            exact_matches = [e for e in filtered_emails if e.lower() == search_lower]
            starts_with = [
                e
                for e in filtered_emails
                if e.lower().startswith(search_lower) and e not in exact_matches
            ]
            contains = [
                e
                for e in filtered_emails
                if search_lower in e.lower()
                and e not in exact_matches
                and e not in starts_with
            ]

            filtered_emails = exact_matches + starts_with + contains
        else:
            filtered_emails = available_emails[:10]

        filtered_emails = filtered_emails[:15]

        context = {
            "emails": filtered_emails,
            "field_type": field_type,
            "query": current_input,
        }

        return render(request, "email_suggestions.html", context)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.change_horillamailconfiguration",
            "horilla_mail.view_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class HorillaMailFieldSelectionView(LoginRequiredMixin, TemplateView):
    """
    View to show all fields of the related model for insertion into email templates
    """

    template_name = "field_selection_modal.html"

    def get_context_data(self, **kwargs):
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
            "company",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
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
                    content_type = ContentType.objects.get(model=model_name.lower())
                else:
                    content_type = ContentType.objects.get(id=content_type_id)
                    model_name = content_type.model_class()._meta.verbose_name
                model_class = apps.get_model(
                    app_label=content_type.app_label, model_name=content_type.model
                )
                related_object = None
                if object_id and object_id != "None":
                    related_object = model_class.objects.get(pk=object_id)

                model_fields = []

                # Get regular fields
                for field in model_class._meta.get_fields():
                    if field.name in excluded_fields:
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

                    if field.many_to_one and hasattr(field, "related_model"):
                        # Get fields from the related model without needing object instance
                        for related_field in field.related_model._meta.get_fields():
                            # Skip excluded fields in related model too
                            if related_field.name in excluded_fields:
                                continue

                            if (
                                not related_field.many_to_many
                                and not related_field.one_to_many
                            ):
                                fk_field_info = {
                                    "name": f"{field.name}.{related_field.name}",
                                    "verbose_name": f'{getattr(related_field, "verbose_name", related_field.name)}',
                                    "header": field.verbose_name,
                                    "field_type": f"{field.__class__.__name__} -> {related_field.__class__.__name__}",
                                    "template_syntax": f"{{{{ instance.{field.name}.{related_field.name} }}}}",
                                    "parent_field": field.name,
                                    "is_foreign_key": True,
                                }

                                foreign_key_fields.append(fk_field_info)

                reverse_relation_fields = []

                # Get all reverse relations
                for field in model_class._meta.get_fields():
                    if field.one_to_many or field.many_to_many:
                        try:
                            # Get the accessor name (like 'employee_set' or custom related_name)
                            accessor_name = field.get_accessor_name()

                            related_model = field.related_model

                            if related_model:
                                for reverse_field in related_model._meta.get_fields():
                                    if (
                                        reverse_field.name in excluded_fields
                                        or reverse_field.many_to_many
                                        or reverse_field.one_to_many
                                    ):
                                        continue

                                    if (
                                        hasattr(reverse_field, "related_model")
                                        and reverse_field.related_model == model_class
                                    ):
                                        continue

                                    reverse_field_info = {
                                        "name": f"{accessor_name}.first.{reverse_field.name}",
                                        "verbose_name": f'{getattr(reverse_field, "verbose_name", reverse_field.name)}',
                                        "header": field.related_model._meta.verbose_name,
                                        "field_type": f"Reverse {field.__class__.__name__} -> {reverse_field.__class__.__name__}",
                                        "template_syntax": f"{{{{ instance.{accessor_name}.first.{reverse_field.name} }}}}",
                                        "parent_field": accessor_name,
                                        "is_reverse_relation": True,
                                    }

                                    reverse_relation_fields.append(reverse_field_info)
                        except Exception as e:
                            logger.error(
                                f"Error processing reverse relation {accessor_name}: {str(e)}"
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


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.change_horillamailconfiguration",
            "horilla_mail.view_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class HorillaMailPreviewView(LoginRequiredMixin, View):
    """
    Preview mail content using existing draft mail object and its render methods
    """

    def get(self, request, *args, **kwargs):

        pk = self.kwargs.get("pk")
        draft_mail = HorillaMail.objects.filter(pk=pk).first()
        try:
            from_mail_config = HorillaMailConfiguration.objects.get(
                id=draft_mail.sender.id
            )
        except Exception as e:
            messages.error(self.request, e)
            return HttpResponse(
                "<script>$('reloadButton').click();closeContentModal();</script>"
            )

        attachments = []
        inline_attachments = {}

        existing_attachments = HorillaMailAttachment.objects.filter(
            mail=draft_mail.pk,
        )
        for attachment in existing_attachments:
            if attachment.is_inline:
                # Store inline attachments by their content_id for replacement
                if attachment.content_id:
                    inline_attachments[attachment.content_id] = attachment
                # Also store by filename as fallback
                inline_attachments[attachment.file_name()] = attachment
            else:
                attachments.append(attachment)

        # Render subject and body
        rendered_subject = draft_mail.render_subject()
        rendered_body = draft_mail.render_body()

        # Replace cid: references with actual file URLs for inline attachments
        import re

        # Pattern to find cid: in src attributes and capture data-filename if present
        cid_pattern = re.compile(
            r'<img\s+([^>]*?)src=["\']cid:([^"\']+)["\']([^>]*?)>', re.IGNORECASE
        )

        def replace_cid(match):
            before_src = match.group(1)
            content_id = match.group(2)
            after_src = match.group(3)

            # Try to find by content_id first
            if content_id in inline_attachments:
                attachment = inline_attachments[content_id]
                return f'<img {before_src}src="{attachment.file.url}"{after_src}>'

            # Try to find by filename from data-filename attribute
            filename_match = re.search(
                r'data-filename=["\']([^"\']+)["\']', before_src + after_src
            )
            if filename_match:
                filename = filename_match.group(1)
                if filename in inline_attachments:
                    attachment = inline_attachments[filename]
                    return f'<img {before_src}src="{attachment.file.url}"{after_src}>'

            return match.group(0)  # Return original if not found

        rendered_body = cid_pattern.sub(replace_cid, rendered_body)
        rendered_body = mark_safe(rendered_body)

        preview_context = {
            "draft_mail": draft_mail,
            "to_email": draft_mail.to,
            "cc_email": draft_mail.cc,
            "bcc_email": draft_mail.bcc,
            "subject": rendered_subject,
            "message_content": rendered_body,
            "from_mail_config": from_mail_config,
            "attachments": attachments,
            "draft": False,
        }

        html_content = render_to_string(
            "mail_preview_modal.html", preview_context, request
        )
        return HttpResponse(html_content)

    def post(self, request, *args, **kwargs):
        try:
            # Get form data
            to_email = request.POST.get("to_email", "")
            cc_email = request.POST.get("cc_email", "")
            bcc_email = request.POST.get("bcc_email", "")
            subject = request.POST.get("subject", "")
            message_content = request.POST.get("message_content", "")
            from_mail_id = request.POST.get("from_mail")
            uploaded_files = request.FILES.getlist("attachments")

            model_name = request.GET.get("model_name")
            pk = request.GET.get("pk")
            object_id = request.GET.get("object_id")

            from_mail_config = None
            if from_mail_id:
                try:
                    from_mail_config = HorillaMailConfiguration.objects.get(
                        id=from_mail_id
                    )
                except HorillaMailConfiguration.DoesNotExist:
                    pass

            draft_mail = None
            content_type = None

            if model_name and object_id:
                try:
                    content_type = ContentType.objects.get(model=model_name.lower())
                    draft_mail = HorillaMail.objects.filter(pk=pk).first()
                except Exception as e:
                    logger.error(f"Error finding draft mail: {e}")

            if not draft_mail:
                company = getattr(request, "active_company", None)
                draft_mail = HorillaMail(
                    content_type=content_type,
                    object_id=object_id or 0,
                    mail_status="draft",
                    created_by=request.user,
                    sender=from_mail_config,
                    company=company,
                )

            draft_mail.sender = from_mail_config
            draft_mail.to = to_email
            draft_mail.cc = cc_email if cc_email else None
            draft_mail.bcc = bcc_email if bcc_email else None
            draft_mail.subject = subject
            draft_mail.body = message_content

            template_context = {
                "request": request,
                "user": request.user,
            }

            if hasattr(request, "active_company") and request.active_company:
                template_context["active_company"] = (
                    request.active_company
                    if request.active_company
                    else request.user.company
                )

            if content_type and object_id:
                try:
                    model_class = apps.get_model(
                        app_label=content_type.app_label, model_name=content_type.model
                    )
                    related_object = model_class.objects.get(pk=object_id)
                    template_context["instance"] = related_object
                    draft_mail.related_to = related_object
                except Exception as e:
                    logger.error(f"Error getting related object: {e}")

            rendered_subject = ""
            rendered_content = ""

            try:
                rendered_subject = draft_mail.render_subject(template_context)
            except Exception as e:
                rendered_subject = f"[Template Error in Subject: {str(e)}] {subject}"

            try:
                rendered_content = draft_mail.render_body(template_context)
            except Exception as e:
                rendered_content = f"<div class='alert alert-danger'>[Template Error: {str(e)}]</div>{message_content}"

            attachments = []
            if draft_mail.pk:
                existing_attachments = HorillaMailAttachment.objects.filter(
                    mail=draft_mail.pk,
                )
                for attachment in existing_attachments:
                    attachments.append(attachment)
                for f in uploaded_files:

                    attachment = HorillaMailAttachment(
                        mail=draft_mail, file=f  # each file individually
                    )
                    attachment.save()
                    attachments.append(attachment)

            preview_context = {
                "draft_mail": draft_mail,
                "to_email": to_email,
                "cc_email": cc_email,
                "bcc_email": bcc_email,
                "subject": rendered_subject,
                "message_content": rendered_content,
                "from_mail_config": from_mail_config,
                "template_context": template_context,
                "attachments": attachments,
            }

            # Render preview template
            html_content = render_to_string(
                "mail_preview_modal.html", preview_context, request
            )
            return HttpResponse(html_content)

        except Exception as e:
            error_html = f"""
            <div class="p-5">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-lg font-semibold text-red-600">Preview Error</h2>
                    <button onclick="closeContentModal()" class="text-gray-500 hover:text-red-500">
                        <img src="assets/icons/close.svg" alt="Close" />
                    </button>
                </div>
                <div class="bg-red-50 border border-red-200 rounded-md p-4">
                    <p class="text-red-800">Error generating preview: {html.escape(str(e))}</p>
                </div>
            </div>
            """
            return HttpResponse(error_html)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.change_horillamailconfiguration",
            "horilla_mail.view_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class CheckDraftChangesView(LoginRequiredMixin, View):
    """
    Check if there are changes to save and return appropriate modal content
    """

    def post(self, request, *args, **kwargs):
        model_name = request.GET.get("model_name")
        pk = request.GET.get("pk")
        object_id = request.GET.get("object_id")
        uploaded_files = request.FILES.getlist("attachments")
        to_email = request.POST.get("to_email", "")
        cc_email = request.POST.get("cc_email", "")
        bcc_email = request.POST.get("bcc_email", "")
        subject = request.POST.get("subject", "")
        message_content = request.POST.get("message_content", "")
        has_content = any([to_email, cc_email, bcc_email, subject, message_content])
        if not has_content:
            return HttpResponse(
                "<script>closehorillaModal();htmx.trigger('#sent-email-tab','click');closeDeleteModeModal();</script>"
            )
        return render(
            request,
            "draft_save_modal.html",
            {"model_name": model_name, "object_id": object_id, "pk": pk},
        )


@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.change_horillamailconfiguration",
            "horilla_mail.view_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class SaveDraftView(LoginRequiredMixin, View):
    """
    Save the current mail as draft
    """

    def post(self, request, *args, **kwargs):
        try:
            to_email = request.POST.get("to_email", "").strip()
            cc_email = request.POST.get("cc_email", "").strip()
            bcc_email = request.POST.get("bcc_email", "").strip()
            subject = request.POST.get("subject", "").strip()
            message_content = request.POST.get("message_content", "").strip()
            from_mail_id = request.POST.get("from_mail")
            uploaded_files = request.FILES.getlist("attachments")
            model_name = request.GET.get("model_name")
            object_id = request.GET.get("object_id")
            company = getattr(request, "active_company", None)
            pk = request.GET.get("pk")
            # Only save if there's actual content
            if not any([to_email, cc_email, bcc_email, subject, message_content]):
                messages.info(request, _("No content to save as draft"))
                return HttpResponse(
                    "<script>closehorillaModal();htmx.trigger('#sent-email-tab','click');closeDeleteModeModal();</script>"
                )

            # Get or create mail configuration
            from_mail_config = None
            if from_mail_id:
                try:
                    from_mail_config = HorillaMailConfiguration.objects.get(
                        id=from_mail_id
                    )
                except HorillaMailConfiguration.DoesNotExist:
                    from_mail_config = HorillaMailConfiguration.objects.filter(
                        is_primary=True
                    ).first()

            if not from_mail_config:
                from_mail_config = HorillaMailConfiguration.objects.first()

            # Get content type
            content_type = None
            if model_name and object_id:
                try:
                    content_type = ContentType.objects.get(model=model_name.lower())
                except ContentType.DoesNotExist:
                    pass

            # Find or create draft
            draft_mail = None
            if content_type and object_id:
                draft_mail = HorillaMail.objects.filter(
                    pk=pk,
                    content_type=content_type,
                    object_id=object_id,
                    mail_status="draft",
                    created_by=request.user,
                ).first()

            if not draft_mail:

                draft_mail = HorillaMail.objects.create(
                    content_type=content_type,
                    object_id=object_id,
                    mail_status="draft",
                    created_by=request.user,
                    sender=from_mail_config,
                    company=company,
                )

            # Update draft with current data
            if from_mail_config:
                draft_mail.sender = from_mail_config
            draft_mail.to = to_email
            draft_mail.cc = cc_email if cc_email else None
            draft_mail.bcc = bcc_email if bcc_email else None
            draft_mail.subject = subject
            draft_mail.body = message_content
            draft_mail.save()
            if draft_mail.pk:
                for f in uploaded_files:
                    attachment = HorillaMailAttachment(
                        mail=draft_mail, file=f, company=company
                    )
                    attachment.save()
            messages.success(request, _("Draft saved successfully"))
            return HttpResponse(
                "<script>closehorillaModal();$('#draft-email-tab').click();closeDeleteModeModal();</script>"
            )

        except Exception as e:
            messages.error(request, _("Error saving draft: ") + str(e))
            return HttpResponse(
                "<script>closehorillaModal();htmx.trigger('#draft-email-tab','click');closeDeleteModeModal();</script>"
            )


@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.change_horillamailconfiguration",
            "horilla_mail.view_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class DiscardDraftView(LoginRequiredMixin, View):
    """
    Discard the draft without saving
    """

    def delete(self, request, *args, **kwargs):
        try:
            model_name = request.GET.get("model_name")
            object_id = request.GET.get("object_id")
            pk = pk = request.GET.get("pk")

            if model_name and object_id:
                try:
                    content_type = ContentType.objects.get(model=model_name.lower())
                    HorillaMail.objects.filter(
                        pk=pk,
                        content_type=content_type,
                        object_id=object_id,
                        mail_status="draft",
                        created_by=request.user,
                    ).delete()
                except ContentType.DoesNotExist:
                    pass

            messages.info(request, _("Draft discarded"))
            return HttpResponse(
                "<script>closehorillaModal();$('#draft-email-tab').click();closeDeleteModeModal();</script>"
            )

        except Exception as e:
            messages.error(request, _("Error discarding draft: ") + str(e))
            return HttpResponse(
                "<script>closehorillaModal();htmx.trigger('#sent-email-tab','click');closeDeleteModeModal();</script>"
            )


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied("horilla_mail.delete_horillamailconfiguration"),
    name="dispatch",
)
class HorillaMailtDeleteView(LoginRequiredMixin, HorillaSingleDeleteView):

    model = HorillaMail

    def post(self, request, *args, **kwargs):
        view_from_get = request.GET.get("view")
        if view_from_get:
            pk = kwargs.get("pk") or self.kwargs.get("pk")
            request.session[f"mail_delete_view_{pk}"] = view_from_get
            self.view_param = view_from_get
        else:
            pk = kwargs.get("pk") or self.kwargs.get("pk")
            self.view_param = request.session.get(f"mail_delete_view_{pk}")
        return super().post(request, *args, **kwargs)

    def get_post_delete_response(self):
        view = getattr(self, "view_param", None)

        if view:
            pk = self.kwargs.get("pk")
            session_key = f"mail_delete_view_{pk}"
            if session_key in self.request.session:
                del self.request.session[session_key]

        tab_map = {
            "sent": "sent-email-tab",
            "draft": "draft-email-tab",
            "scheduled": "scheduled-email-tab",
        }

        tab_id = tab_map.get(view)

        if tab_id:
            return HttpResponse(f"<script>$('#{tab_id}').click();</script>")

        return HttpResponse("<script>location.reload();</script>")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.view_horillamailconfiguration",
            "horilla_mail.add_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class ScheduleMailView(LoginRequiredMixin, View):
    """
    Schedule mail view - saves draft with scheduled send time
    """

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk") or request.GET.get("pk")
        scheduled_at = request.POST.get("schedule_datetime")
        is_reschedule = bool(kwargs.get("pk"))

        if is_reschedule:
            errors = {}

            if not scheduled_at:
                errors["schedule_datetime"] = _("Schedule time is required")
                context = {
                    "pk": pk,
                    "is_reschedule": is_reschedule,
                    "errors": errors,
                    "non_field_errors": {},
                    "scheduled_at": scheduled_at or "",
                }
                html = render_to_string(
                    "schedule_mail_form.html", context, request=request
                )
                return HttpResponse(html)

            try:
                draft_mail = HorillaMail.objects.get(pk=pk)
            except HorillaMail.DoesNotExist:
                errors["non_field_error"] = _(
                    "Scheduled mail not found or you don't have permission"
                )
                context = {
                    "pk": pk,
                    "is_reschedule": is_reschedule,
                    "errors": errors,
                    "non_field_errors": errors,
                    "scheduled_at": scheduled_at or "",
                }
                html = render_to_string(
                    "schedule_mail_form.html", context, request=request
                )
                return HttpResponse(html)

            # Parse and validate the new scheduled time
            try:
                try:
                    schedule_at_naive = datetime.strptime(
                        scheduled_at, "%Y-%m-%dT%H:%M"
                    )
                except ValueError:
                    schedule_at_naive = datetime.strptime(
                        scheduled_at, "%Y-%m-%d %H:%M"
                    )

                user_tz = django_timezone.get_current_timezone()
                schedule_at = django_timezone.make_aware(schedule_at_naive, user_tz)

                if schedule_at <= timezone.now():
                    errors["schedule_datetime"] = _(
                        "Scheduled time must be in the future"
                    )
                    context = {
                        "pk": pk,
                        "is_reschedule": is_reschedule,
                        "errors": errors,
                        "non_field_errors": {},
                        "scheduled_at": scheduled_at or "",
                    }
                    html = render_to_string(
                        "schedule_mail_form.html", context, request=request
                    )
                    return HttpResponse(html)
            except ValueError:
                errors["schedule_datetime"] = _("Invalid date/time format")
                context = {
                    "pk": pk,
                    "is_reschedule": is_reschedule,
                    "errors": errors,
                    "non_field_errors": {},
                    "scheduled_at": scheduled_at or "",
                }
                html = render_to_string(
                    "schedule_mail_form.html", context, request=request
                )
                return HttpResponse(html)

            # Update only the scheduled time
            draft_mail.scheduled_at = schedule_at
            draft_mail.save(update_fields=["scheduled_at"])

            messages.success(
                request,
                _("Mail rescheduled successfully for ")
                + schedule_at.strftime("%Y-%m-%d %H:%M"),
            )
            return HttpResponse(
                "<script>closeModal();$('#scheduled-email-tab').click();</script>"
            )

        try:
            errors = {}

            # Get form data
            to_email = request.POST.get("to_email", "")
            cc_email = request.POST.get("cc_email", "")
            bcc_email = request.POST.get("bcc_email", "")
            subject = request.POST.get("subject", "")
            message_content = request.POST.get("message_content", "")
            from_mail_id = request.POST.get("from_mail")
            uploaded_files = request.FILES.getlist("attachments")

            # Get schedule data
            scheduled_at = request.POST.get("schedule_datetime")

            model_name = request.GET.get("model_name")
            object_id = request.GET.get("object_id")
            pk = request.GET.get("pk")

            company = getattr(request, "active_company", None)
            setattr(_thread_local, "from_mail_id", from_mail_id)

            # Validate required fields
            if not to_email:
                errors["to_email"] = _("To email is required")
            if not from_mail_id:
                errors["from_mail"] = _("From mail configuration is required")
            if not scheduled_at:
                errors["schedule_datetime"] = _("Schedule time is required")

            # Validate XSS
            if message_content and HorillaMail.has_xss(message_content):
                errors["message_content"] = _(
                    "Message body contains potentially dangerous content (XSS detected)."
                )

            # Validate date/time format
            if scheduled_at:
                try:
                    try:
                        schedule_at_naive = datetime.strptime(
                            scheduled_at, "%Y-%m-%dT%H:%M"
                        )
                    except ValueError:
                        schedule_at_naive = datetime.strptime(
                            scheduled_at, "%Y-%m-%d %H:%M"
                        )

                    user_tz = django_timezone.get_current_timezone()
                    schedule_at = django_timezone.make_aware(schedule_at_naive, user_tz)

                    if schedule_at <= timezone.now():
                        errors["schedule_datetime"] = _(
                            "Scheduled time must be in the future"
                        )
                except ValueError:
                    errors["schedule_datetime"] = _("Invalid date/time format")

            if errors:
                non_field_errors = {
                    k: v for k, v in errors.items() if k != "schedule_datetime"
                }
                context = {
                    "model_name": model_name,
                    "object_id": object_id,
                    "pk": pk,
                    "is_reschedule": is_reschedule,
                    "errors": errors,
                    "non_field_errors": non_field_errors,
                    "scheduled_at": scheduled_at or "",
                }
                html = render_to_string(
                    "schedule_mail_form.html", context, request=request
                )
                return HttpResponse(html)

            try:
                from_mail_config = HorillaMailConfiguration.objects.get(id=from_mail_id)
            except HorillaMailConfiguration.DoesNotExist:
                errors["from_mail"] = _("Invalid mail configuration selected")
                non_field_errors = {
                    k: v for k, v in errors.items() if k != "schedule_datetime"
                }
                context = {
                    "model_name": model_name,
                    "object_id": object_id,
                    "pk": pk,
                    "is_reschedule": is_reschedule,
                    "errors": errors,
                    "non_field_errors": non_field_errors,
                    "scheduled_at": scheduled_at or "",
                }
                html = render_to_string(
                    "schedule_mail_form.html", context, request=request
                )
                return HttpResponse(html)

            content_type = None
            if model_name and object_id:
                try:
                    content_type = ContentType.objects.get(model=model_name.lower())
                except ContentType.DoesNotExist:
                    errors["non_field_error"] = f"Invalid model name: {model_name}"
                    context = {
                        "model_name": model_name,
                        "object_id": object_id,
                        "pk": pk,
                        "is_reschedule": is_reschedule,
                        "errors": errors,
                        "scheduled_at": scheduled_at or "",
                    }
                    html = render_to_string(
                        "schedule_mail_form.html", context, request=request
                    )
                    return HttpResponse(html)

            # Find or create draft mail
            draft_mail = None
            if pk:
                try:
                    draft_mail = HorillaMail.objects.get(
                        pk=pk,
                        mail_status="draft",
                        created_by=request.user,
                    )
                except HorillaMail.DoesNotExist:
                    pass

            if not draft_mail:
                draft_mail = HorillaMail.objects.create(
                    content_type=content_type,
                    object_id=object_id or 0,
                    mail_status="scheduled",
                    created_by=request.user,
                    sender=from_mail_config,
                    company=company,
                )

            request_info = {
                "host": request.get_host(),
                "scheme": request.scheme,
            }

            # Extract inline images
            cleaned_message_content, inline_images = extract_inline_images_with_cid(
                message_content
            )

            # Update draft mail with scheduled status
            draft_mail.sender = from_mail_config
            draft_mail.to = to_email
            draft_mail.cc = cc_email if cc_email else None
            draft_mail.bcc = bcc_email if bcc_email else None
            draft_mail.subject = subject if subject else None
            draft_mail.body = (
                cleaned_message_content if cleaned_message_content else None
            )
            draft_mail.mail_status = "scheduled"
            draft_mail.scheduled_at = schedule_at
            if draft_mail.additional_info is None:
                draft_mail.additional_info = {}
            draft_mail.additional_info["request_info"] = request_info
            draft_mail.save()

            # Save attachments
            if draft_mail.pk:
                for f in uploaded_files:
                    attachment = HorillaMailAttachment(
                        mail=draft_mail, file=f, company=company
                    )
                    attachment.save()

                for img_file, cid in inline_images:
                    attachment = HorillaMailAttachment(
                        mail=draft_mail,
                        file=img_file,
                        company=company,
                        is_inline=True,
                        content_id=cid,
                    )
                    attachment.save()

            messages.success(
                request,
                _("Mail scheduled successfully for ")
                + schedule_at.strftime("%Y-%m-%d %H:%M"),
            )
            return HttpResponse(
                "<script>closehorillaModal();$('#scheduled-email-tab').click();closeModal();</script>"
            )

        except Exception as e:
            import traceback

            logger.error(traceback.format_exc())
            errors = {"non_field_error": _("Error scheduling mail: ") + str(e)}
            context = {
                "model_name": model_name,
                "object_id": object_id,
                "pk": pk,
                "is_reschedule": is_reschedule,
                "errors": errors,
                "scheduled_at": scheduled_at or "",
            }
            html = render_to_string("schedule_mail_form.html", context, request=request)
            return HttpResponse(html)


@method_decorator(htmx_required, name="dispatch")
@method_decorator(
    permission_required_or_denied(
        [
            "horilla_mail.view_horillamailconfiguration",
            "horilla_mail.add_horillamailconfiguration",
        ]
    ),
    name="dispatch",
)
class ScheduleMailModallView(LoginRequiredMixin, View):
    """
    Open the schedule modal
    """

    def get(self, request, *args, **kwargs):
        model_name = request.GET.get("model_name")
        object_id = request.GET.get("object_id")
        pk = request.GET.get("pk") or kwargs.get("pk")
        is_reschedule = bool(kwargs.get("pk"))
        mail = HorillaMail.objects.get(pk=pk)
        scheduled_at_formatted = ""
        if mail.scheduled_at:
            user_tz = django_timezone.get_current_timezone()
            scheduled_at_local = mail.scheduled_at.astimezone(user_tz)
            scheduled_at_formatted = scheduled_at_local.strftime("%Y-%m-%dT%H:%M")

        context = {
            "model_name": model_name,
            "object_id": object_id,
            "pk": pk,
            "is_reschedule": is_reschedule,
            "scheduled_at": scheduled_at_formatted,
        }

        html = render_to_string("schedule_mail_form.html", context, request=request)
        return HttpResponse(html)
