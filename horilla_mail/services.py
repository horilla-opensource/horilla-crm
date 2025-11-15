from django.core.mail import EmailMessage
from django.utils import timezone

from horilla_mail.models import HorillaMail


class HorillaMailManager:
    MAX_RETRIES = 3  # Optional retry limit

    @staticmethod
    def send_mail(mail: HorillaMail, context=None):
        context = context or {}
        try:
            subject = mail.render_subject(context)
            body = mail.render_body(context)

            to = [
                email.strip() for email in (mail.to or "").split(",") if email.strip()
            ]
            cc = [
                email.strip() for email in (mail.cc or "").split(",") if email.strip()
            ]
            bcc = [
                email.strip() for email in (mail.bcc or "").split(",") if email.strip()
            ]

            if not to:
                raise ValueError("No recipient found in 'to' field")

            from django.core.mail import EmailMultiAlternatives, get_connection

            connection = get_connection(
                "horilla_mail.horilla_backends.HorillaDefaultMailBackend"
            )
            email = EmailMultiAlternatives(
                subject=subject,
                body=body,
                from_email=mail.sender.from_email if mail.sender else None,
                to=to,
                cc=cc,
                bcc=bcc,
                connection=connection,
            )

            # Attach the HTML version
            email.attach_alternative(body, "text/html")

            # Add file attachments
            # for attachment in mail.attachments.all():
            #     email.attach(
            #         attachment.file.name,
            #         attachment.file.read(),
            #         attachment.mime_type or "application/octet-stream",
            #     )
            for attachment in mail.attachments.filter(is_inline=True):
                from email.mime.image import MIMEImage

                with attachment.file.open("rb") as f:
                    img_data = f.read()

                # Determine subtype from mime_type
                mime_type = attachment.mime_type or "image/jpeg"
                subtype = mime_type.split("/")[-1] if "/" in mime_type else "jpeg"

                img = MIMEImage(img_data, _subtype=subtype)
                img.add_header("Content-ID", f"<{attachment.content_id}>")
                img.add_header(
                    "Content-Disposition", "inline", filename=attachment.file_name()
                )
                email.attach(img)

            # Add regular file attachments
            for attachment in mail.attachments.filter(is_inline=False):
                email.attach(
                    attachment.file_name(),
                    attachment.file.read(),
                    attachment.mime_type or "application/octet-stream",
                )

            email.send()

            mail.mail_status = "sent"
            mail.sent_at = timezone.now()
            mail.mail_status_message = ""
            mail.save()

        except Exception as e:
            mail.mail_status = "failed"
            mail.mail_status_message = str(e)
            mail.save()
