import logging
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.mail.backends.smtp import EmailBackend
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from requests_oauthlib import OAuth2Session

from horilla_utils.middlewares import _thread_local

logger = logging.getLogger(__name__)


class HorillaDefaultMailBackend(EmailBackend):
    def __init__(
        self,
        host=None,
        port=None,
        username=None,
        password=None,
        use_tls=None,
        fail_silently=None,
        use_ssl=None,
        timeout=None,
        ssl_keyfile=None,
        ssl_certfile=None,
        **kwargs,
    ):
        self.configuration = self.get_dynamic_email_config()
        ssl_keyfile = (
            getattr(self.configuration, "ssl_keyfile", None)
            if self.configuration
            else ssl_keyfile or getattr(settings, "ssl_keyfile", None)
        )
        ssl_certfile = (
            getattr(self.configuration, "ssl_certfile", None)
            if self.configuration
            else ssl_certfile or getattr(settings, "ssl_certfile", None)
        )

        if self.configuration and self.configuration.type == "mail":
            super().__init__(
                host=self.dynamic_host,
                port=self.dynamic_port,
                username=self.dynamic_username,
                password=self.dynamic_password,
                use_tls=self.dynamic_use_tls,
                fail_silently=self.dynamic_fail_silently,
                use_ssl=self.dynamic_use_ssl,
                timeout=self.dynamic_timeout,
                ssl_keyfile=ssl_keyfile,
                ssl_certfile=ssl_certfile,
                **kwargs,
            )
        else:
            # For Outlook or fallback, still initialize with default values
            super().__init__(
                host=host or getattr(settings, "EMAIL_HOST", None),
                port=port or getattr(settings, "EMAIL_PORT", None),
                username=username or getattr(settings, "EMAIL_HOST_USER", None),
                password=password or getattr(settings, "EMAIL_HOST_PASSWORD", None),
                use_tls=use_tls or getattr(settings, "EMAIL_USE_TLS", None),
                fail_silently=fail_silently
                or getattr(settings, "EMAIL_FAIL_SILENTLY", True),
                use_ssl=use_ssl or getattr(settings, "EMAIL_USE_SSL", None),
                timeout=timeout or getattr(settings, "EMAIL_TIMEOUT", None),
                ssl_keyfile=ssl_keyfile,
                ssl_certfile=ssl_certfile,
                **kwargs,
            )

    @staticmethod
    def get_dynamic_email_config():
        from horilla_mail.models import HorillaMailConfiguration

        request = getattr(_thread_local, "request", None)
        from_mail_id = getattr(_thread_local, "from_mail_id", None)

        company = None

        if request and not request.user.is_anonymous:
            company = request.user.company

        configuration = None

        if from_mail_id:
            try:
                configuration = HorillaMailConfiguration.objects.filter(
                    pk=from_mail_id
                ).first()
            except:
                messages.error(
                    request, f"Email configuration ID {from_mail_id} not found."
                )
                setattr(_thread_local, "invalid_config", True)
                return None

        if not configuration and company:
            configuration = HorillaMailConfiguration.objects.filter(
                company=company
            ).first()

        if not configuration:
            configuration = HorillaMailConfiguration.objects.filter(
                is_primary=True
            ).first()

        if configuration:
            display_email_name = (
                f"{configuration.display_name} <{configuration.from_email}>"
            )
            user_id = ""
            if request:
                if (
                    configuration.use_dynamic_display_name
                    and request.user.is_authenticated
                ):
                    display_email_name = (
                        f"{request.user.get_full_name()} <{request.user.email}>"
                    )
                if request.user.is_authenticated:
                    user_id = request.user.pk
                    reply_to = [request.user.email]
                    cache.set(f"reply_to{request.user.pk}", reply_to)

            cache.set(f"dynamic_display_name{user_id}", display_email_name)

        return configuration

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        if not email_messages:
            return 0

        if self.configuration and self.configuration.type == "outlook":
            return self._send_outlook_messages(email_messages)
        else:
            # Use default SMTP for email
            return super().send_messages(email_messages)

    def _send_outlook_messages(self, email_messages):
        """Send messages using Microsoft Graph API"""
        sent_count = 0
        for message in email_messages:
            try:
                if self._send_outlook_message(message):
                    sent_count += 1
            except Exception as e:
                if not self.fail_silently:
                    raise e

        return sent_count

    from datetime import datetime

    def _get_outlook_access_token(self):
        """Get or refresh Outlook access token"""
        if not self.configuration or not self.configuration.token:
            return None

        token_data = self.configuration.token
        if "expires_at" in token_data:
            try:
                expires_at_val = token_data["expires_at"]

                if isinstance(expires_at_val, (int, float)):
                    # Handle Unix timestamp
                    expires_at = datetime.fromtimestamp(expires_at_val)
                elif isinstance(expires_at_val, str):
                    # Handle ISO 8601 string
                    expires_at = datetime.fromisoformat(expires_at_val)
                else:
                    raise ValueError(
                        f"Unexpected expires_at type: {type(expires_at_val)}"
                    )

            except Exception as e:
                logger.error("Error parsing expires_at:", e)
                return None

            if datetime.now() >= expires_at:
                return self._refresh_outlook_token()

        return token_data.get("access_token")

    def _refresh_outlook_token(self):
        """Refresh Outlook access token"""
        if (
            not self.configuration.token
            or "refresh_token" not in self.configuration.token
        ):
            return None

        refresh_data = {
            "client_id": self.configuration.outlook_client_id,
            "client_secret": self.configuration.get_decrypted_client_secret(),
            "refresh_token": self.configuration.token["refresh_token"],
            "grant_type": "refresh_token",
        }

        try:
            response = requests.post(
                self.configuration.outlook_token_url, data=refresh_data, timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()

                # Calculate expiry time
                expires_in = token_data.get("expires_in", 3600)
                expires_at = datetime.now() + timedelta(seconds=expires_in)
                token_data["expires_at"] = expires_at.isoformat()

                # Update configuration
                self.configuration.token = token_data
                self.configuration.last_refreshed = timezone.now()
                self.configuration.save(update_fields=["token", "last_refreshed"])

                return token_data.get("access_token")
            else:
                raise Exception(f"Token refresh failed: {response.text}")

        except Exception as e:
            raise Exception(f"Failed to refresh token: {str(e)}")

    def _prepare_outlook_message_data(self, message):
        """Convert EmailMessage to Outlook Graph API format"""
        # Build recipients
        to_recipients = [{"emailAddress": {"address": email}} for email in message.to]
        cc_recipients = [
            {"emailAddress": {"address": email}} for email in (message.cc or [])
        ]
        bcc_recipients = [
            {"emailAddress": {"address": email}} for email in (message.bcc or [])
        ]

        reply_to = []
        if message.reply_to:
            reply_to = [
                {"emailAddress": {"address": email}} for email in message.reply_to
            ]

        message_body = {"contentType": "text", "content": message.body or ""}

        if isinstance(message, EmailMultiAlternatives):
            for alternative in getattr(message, "alternatives", []):
                if alternative[1] == "text/html":
                    message_body = {
                        "contentType": "html",
                        "content": alternative[0] or "",
                    }
                    break

        outlook_message = {
            "message": {
                "subject": message.subject or "",
                "body": message_body,
                "toRecipients": to_recipients,
            }
        }

        if hasattr(self.configuration, "from_email") and self.configuration.from_email:
            outlook_message["message"]["from"] = {
                "emailAddress": {
                    "address": self.configuration.from_email,
                    "name": getattr(self.configuration, "display_name", None),
                }
            }

        if cc_recipients:
            outlook_message["message"]["ccRecipients"] = cc_recipients
        if bcc_recipients:
            outlook_message["message"]["bccRecipients"] = bcc_recipients
        if reply_to:
            outlook_message["message"]["replyTo"] = reply_to

        if hasattr(message, "attachments") and message.attachments:
            outlook_message["message"]["attachments"] = []
            for attachment in message.attachments:
                try:
                    import base64

                    if hasattr(attachment, "get_payload"):
                        content = attachment.get_payload()

                        if attachment.get("Content-Transfer-Encoding") == "base64":
                            if isinstance(content, bytes):
                                content = content.decode("ascii")
                            content_bytes = content
                        else:
                            if isinstance(content, str):
                                content_bytes = base64.b64encode(
                                    content.encode()
                                ).decode()
                            else:
                                content_bytes = base64.b64encode(content).decode()

                        content_id = attachment.get("Content-ID", "")
                        if content_id:
                            content_id = content_id.strip("<>")

                        is_inline = bool(content_id)

                        attachment_data = {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": attachment.get_filename() or "image.png",
                            "contentBytes": content_bytes,
                            "isInline": is_inline,
                            "contentType": attachment.get_content_type() or "image/png",
                        }

                        if is_inline:
                            attachment_data["contentId"] = content_id

                    else:
                        filename, content, mimetype = attachment
                        if isinstance(content, str):
                            content = content.encode()

                        attachment_data = {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": filename,
                            "contentBytes": base64.b64encode(content).decode(),
                            "contentType": mimetype,
                            "isInline": False,
                        }

                    outlook_message["message"]["attachments"].append(attachment_data)
                except Exception as e:
                    logger.error(f"Error processing attachment: {e}")
                    import traceback

                    logger.error(traceback.format_exc())
                    continue

        return outlook_message

    def _send_outlook_message(self, message):
        """Send a single message using Microsoft Graph API"""
        try:
            # Get access token
            access_token = self._get_outlook_access_token()

            if not access_token:
                raise Exception("Failed to get Outlook access token")

            message_data = self._prepare_outlook_message_data(message)

            api = self.get_dynamic_email_config()

            oauth = OAuth2Session(
                api.outlook_client_id,
                token=api.token,
                auto_refresh_kwargs={
                    "client_id": api.outlook_client_id,
                    "client_secret": api.get_decrypted_client_secret(),
                },
                auto_refresh_url=api.outlook_token_url,
            )

            graph_endpoint = f"{api.outlook_api_endpoint}/me/sendMail"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            }

            response = oauth.post(graph_endpoint, json=message_data, headers=headers)
            response.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            if not self.fail_silently:
                raise e
            return False

    @property
    def dynamic_host(self):
        if self.configuration and self.configuration.type == "outlook":
            return None  # Not used for Outlook
        return (
            self.configuration.host
            if self.configuration
            else getattr(settings, "EMAIL_HOST", None)
        )

    @property
    def dynamic_port(self):
        if self.configuration and self.configuration.type == "outlook":
            return None  # Not used for Outlook
        return (
            self.configuration.port
            if self.configuration
            else getattr(settings, "EMAIL_PORT", None)
        )

    @property
    def dynamic_username(self):
        if self.configuration and self.configuration.type == "outlook":
            return self.configuration.from_email
        return (
            self.configuration.username
            if self.configuration
            else getattr(settings, "EMAIL_HOST_USER", None)
        )

    @property
    def dynamic_mail_sent_from(self):
        return (
            self.configuration.from_email
            if self.configuration
            else getattr(settings, "DEFAULT_FROM_EMAIL", None)
        )

    @property
    def dynamic_display_name(self):
        return self.configuration.display_name if self.configuration else None

    @property
    def dynamic_from_email_with_display_name(self):
        return (
            f"{self.dynamic_display_name} <{self.dynamic_mail_sent_from}>"
            if self.dynamic_display_name
            else self.dynamic_mail_sent_from
        )

    @property
    def dynamic_password(self):
        if self.configuration and self.configuration.type == "outlook":
            return None
        return (
            self.configuration.get_decrypted_password()
            if self.configuration
            else getattr(settings, "EMAIL_HOST_PASSWORD", None)
        )

    @property
    def dynamic_use_tls(self):
        if self.configuration and self.configuration.type == "outlook":
            return False  # Not used for Outlook
        return (
            self.configuration.use_tls
            if self.configuration
            else getattr(settings, "EMAIL_USE_TLS", None)
        )

    @property
    def dynamic_fail_silently(self):
        return (
            self.configuration.fail_silently
            if self.configuration
            else getattr(settings, "EMAIL_FAIL_SILENTLY", True)
        )

    @property
    def dynamic_use_ssl(self):
        if self.configuration and self.configuration.type == "outlook":
            return False  # Not used for Outlook
        return (
            self.configuration.use_ssl
            if self.configuration
            else getattr(settings, "EMAIL_USE_SSL", None)
        )

    @property
    def dynamic_timeout(self):
        return (
            self.configuration.timeout
            if self.configuration
            else getattr(settings, "EMAIL_TIMEOUT", None)
        )


message_init = EmailMessage.__init__


def new_init(
    self,
    subject="",
    body="",
    from_email=None,
    to=None,
    bcc=None,
    connection=None,
    attachments=None,
    headers=None,
    cc=None,
    reply_to=None,
):
    """
    custom __init_method to override
    """
    request = getattr(_thread_local, "request", None)
    HorillaDefaultMailBackend()
    user_id = ""
    if request and request.user and request.user.is_authenticated:
        user_id = request.user.pk
        reply_to = cache.get(f"reply_to{user_id}") if not reply_to else reply_to

    from_email = cache.get(f"dynamic_display_name{user_id}")
    message_init(
        self,
        subject=subject,
        body=body,
        from_email=from_email,
        to=to,
        bcc=bcc,
        connection=connection,
        attachments=attachments,
        headers=headers,
        cc=cc,
        reply_to=reply_to,
    )


EmailMessage.__init__ = new_init
