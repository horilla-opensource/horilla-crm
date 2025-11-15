from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View

from horilla_core.decorators import htmx_required
from horilla_core.models import Company, HorillaUser
from horilla_mail.models import HorillaMailConfiguration


@method_decorator(htmx_required(login=False), name="dispatch")
class ForgotPasswordView(View):
    template_name = "forgot_password/forgot_password.html"
    success_template = "forgot_password/forgot_password_success_partial.html"

    def get(self, request):
        """Display the forgot password form"""
        return render(request, self.template_name)

    def post(self, request):
        """Handle password reset email submission"""
        email_or_username = request.POST.get("email")

        try:
            user = HorillaUser.objects.get(
                Q(email=email_or_username) | Q(username=email_or_username)
            )

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            reset_link = request.build_absolute_uri(f"/reset-password/{uid}/{token}/")

            primary_config = HorillaMailConfiguration.objects.filter(
                is_primary=True, company=user.company
            ).first()

            if not primary_config:
                hq_company = Company.objects.filter(hq=True).first()
                if hq_company:
                    primary_config = HorillaMailConfiguration.objects.filter(
                        is_primary=True, company=hq_company
                    ).first()

            context = {
                "user": user,
                "reset_link": reset_link,
                "site_name": getattr(settings, "SITE_NAME", "Horilla"),
            }

            html_message = render_to_string(
                "forgot_password/password_reset_email.html", context
            )
            plain_message = strip_tags(html_message)

            email = EmailMessage(
                subject="Password Reset Request - Horilla",
                body=plain_message,
                from_email=(
                    primary_config.from_email
                    if primary_config
                    else settings.DEFAULT_FROM_EMAIL
                ),
                to=[user.email],
            )

            email.content_subtype = "html"
            email.body = html_message

            email.send(fail_silently=False)
            return render(request, self.success_template)

        except HorillaUser.DoesNotExist:
            messages.error(request, "User with this email or username does not exist.")

        except Exception as e:
            messages.error(request, "An error occurred. Please try again later.")
        return render(
            request, self.template_name, {"email_or_username": email_or_username}
        )


class PasswordResetConfirmView(View):
    template_name = "forgot_password/password_reset_confirm.html"
    success_template = "forgot_password/password_reset_success_partial.html"

    def get(self, request, uidb64, token):
        """Display the password reset form"""
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = HorillaUser.objects.get(pk=uid)
            print(uid, user)

            if default_token_generator.check_token(user, token):
                context = {
                    "validlink": True,
                    "uidb64": uidb64,
                    "token": token,
                }
            else:
                context = {"validlink": False}

        except Exception as e:
            context = {"validlink": False}

        return render(request, self.template_name, context)

    def post(self, request, uidb64, token):
        """Handle password reset via HTMX"""
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = HorillaUser.objects.get(pk=uid)

            if not default_token_generator.check_token(user, token):
                messages.error(
                    request, "Password reset link is invalid or has expired."
                )
                context = {"validlink": False}
                return render(request, self.template_name, context)

            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if not new_password or not confirm_password:
                messages.error(request, "Please fill in all password fields.")
            elif new_password != confirm_password:
                messages.error(request, "Passwords do not match.")

            else:
                user.set_password(new_password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been reset successfully.")

                if request.headers.get("HX-Request") == "true":
                    response = HttpResponse()
                    response["HX-Redirect"] = "/login/"
                    response["HX-Push-Url"] = "/login/"
                    return response

                return redirect("horilla_core:login")

            context = {
                "validlink": True,
                "uidb64": uidb64,
                "token": token,
                "new_password": new_password,
                "confirm_password": confirm_password,
            }
            return render(request, self.template_name, context)

        except (TypeError, ValueError, OverflowError, HorillaUser.DoesNotExist):
            messages.error(request, "Invalid password reset link.")
            context = {"validlink": False}
            return render(request, self.template_name, context)
