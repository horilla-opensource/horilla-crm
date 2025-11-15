import logging

from celery import shared_task
from django.utils import timezone

from horilla_utils.middlewares import _thread_local

logger = logging.getLogger(__name__)


class MockRequest:
    """Mock request object for Celery tasks"""

    def __init__(self, user, company, request_info):
        self.user = user
        self.active_company = company
        self.META = request_info.get("meta", {})
        self._host = request_info.get("host", "")
        self.scheme = request_info.get("scheme", "https")

    def get_host(self):
        return self._host

    def build_absolute_uri(self, location=None):
        """Build absolute URI for use in templates"""
        if location is None:
            return f"{self.scheme}://{self._host}/"
        if location.startswith("http"):
            return location
        return f"{self.scheme}://{self._host}{location}"


@shared_task(bind=True, max_retries=3)
def send_scheduled_mail_task(self, mail_id):
    """
    Celery task to send a scheduled mail using HorillaMailManager
    """
    from django.contrib.auth import get_user_model

    from horilla_mail.models import HorillaMail
    from horilla_mail.services import HorillaMailManager

    User = get_user_model()
    logger.info(f"Processing scheduled mail {mail_id}")

    try:
        mail = HorillaMail.objects.get(pk=mail_id)

        # Check if mail is still in scheduled status
        if mail.mail_status != "scheduled":
            logger.info(f"Mail {mail_id} status is {mail.mail_status}, skipping send")
            return f"Mail {mail_id} is not in scheduled status"

        # Check if scheduled time has arrived
        if mail.scheduled_at and mail.scheduled_at > timezone.now():
            logger.info(f"Mail {mail_id} scheduled time not yet reached")
            return f"Mail {mail_id} not yet time to send"

        # Set thread local for from_mail_id to use correct configuration
        if mail.sender:
            setattr(_thread_local, "from_mail_id", mail.sender.pk)

        # Reconstruct context from additional_info
        request_info = (
            mail.additional_info.get("request_info", {}) if mail.additional_info else {}
        )

        # Get user and company
        user = mail.created_by
        company = mail.company

        # If user_id and company_id are stored in request_info, use them as fallback
        if not user and request_info.get("user_id"):
            try:
                user = User.objects.get(pk=request_info["user_id"])
            except User.DoesNotExist:
                pass

        if not company and request_info.get("company_id"):
            from horilla_core.models import Company

            try:
                company = Company.objects.get(pk=request_info["company_id"])
            except Company.DoesNotExist:
                pass

        # Create mock request object
        mock_request = MockRequest(user, company, request_info)
        setattr(_thread_local, "request", mock_request)

        # Prepare context for rendering
        context = {
            "instance": mail.related_to,
            "user": user,
            "active_company": company,
            "request": mock_request,
        }

        # Check for XSS before rendering (on templates)
        if HorillaMail.has_xss(mail.subject or "") or HorillaMail.has_xss(
            mail.body or ""
        ):
            logger.warning(f"XSS detected in mail templates {mail_id}")
            mail.mail_status = "failed"
            mail.mail_status_message = "XSS content detected in email templates"
            mail.save(update_fields=["mail_status", "mail_status_message"])
            return f"XSS detected in mail {mail_id}"

        # Use HorillaMailManager to send the mail
        HorillaMailManager.send_mail(mail, context=context)

        logger.info(f"Successfully sent mail {mail_id}")
        return f"Successfully sent mail {mail_id}"

    except HorillaMail.DoesNotExist:
        logger.error(f"Mail {mail_id} does not exist")
        return f"Mail {mail_id} not found"

    except ValueError as e:
        # Handle validation errors from HorillaMailManager
        logger.error(f"Validation error sending mail {mail_id}: {str(e)}")

        try:
            mail = HorillaMail.objects.get(pk=mail_id)
            mail.mail_status = "failed"
            mail.mail_status_message = str(e)
            mail.save(update_fields=["mail_status", "mail_status_message"])
        except:
            pass

        return f"Failed to send mail {mail_id}: {str(e)}"

    except Exception as e:
        logger.error(f"Error sending mail {mail_id}: {str(e)}")

        try:
            mail = HorillaMail.objects.get(pk=mail_id)
            # HorillaMailManager already set status to failed
            # Only update if status is still scheduled
            if mail.mail_status == "scheduled":
                mail.mail_status = "failed"
                mail.mail_status_message = str(e)
                mail.save(update_fields=["mail_status", "mail_status_message"])
        except:
            pass

        # Retry the task
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes

    finally:
        # Clean up thread local
        if hasattr(_thread_local, "from_mail_id"):
            delattr(_thread_local, "from_mail_id")
        if hasattr(_thread_local, "request"):
            delattr(_thread_local, "request")


@shared_task
def process_scheduled_mails():
    """
    Periodic task to check and queue scheduled mails for sending
    """
    from horilla_mail.models import HorillaMail

    # Get all scheduled mails whose time has arrived
    scheduled_mails = HorillaMail.objects.filter(
        mail_status="scheduled", scheduled_at__lte=timezone.now()
    )

    logger.info(f"Found {scheduled_mails.count()} scheduled mails to process")
    logger.info(f"Current time: {timezone.now()}")

    count = 0
    for mail in scheduled_mails:
        # Queue each mail for sending
        send_scheduled_mail_task.delay(mail.pk)
        count += 1

    logger.info(f"Queued {count} scheduled mails for sending")
    return f"Queued {count} mails"


@shared_task
def send_mail_async(mail_id, context=None):
    """
    General purpose async task to send any mail immediately using HorillaMailManager
    """
    from django.contrib.auth import get_user_model

    from horilla_mail.models import HorillaMail
    from horilla_mail.services import HorillaMailManager

    User = get_user_model()

    try:
        mail = HorillaMail.objects.get(pk=mail_id)

        # Set thread local if sender exists
        if mail.sender:
            setattr(_thread_local, "from_mail_id", mail.sender.pk)

        # If no context provided, try to reconstruct from additional_info
        if context is None:
            request_info = (
                mail.additional_info.get("request_info", {})
                if mail.additional_info
                else {}
            )

            user = mail.created_by
            company = mail.company

            if not user and request_info.get("user_id"):
                try:
                    user = User.objects.get(pk=request_info["user_id"])
                except User.DoesNotExist:
                    pass

            if not company and request_info.get("company_id"):
                from horilla_core.models import Company

                try:
                    company = Company.objects.get(pk=request_info["company_id"])
                except Company.DoesNotExist:
                    pass

            # Create mock request
            mock_request = MockRequest(user, company, request_info)
            setattr(_thread_local, "request", mock_request)

            context = {
                "instance": mail.related_to,
                "user": user,
                "active_company": company,
                "request": mock_request,
            }

        # Use HorillaMailManager to send
        HorillaMailManager.send_mail(mail, context=context)

        logger.info(f"Successfully sent mail {mail_id} asynchronously")
        return f"Successfully sent mail {mail_id}"

    except HorillaMail.DoesNotExist:
        logger.error(f"Mail {mail_id} does not exist")
        return f"Mail {mail_id} not found"

    except Exception as e:
        logger.error(f"Error sending mail {mail_id}: {str(e)}")
        return f"Failed to send mail {mail_id}: {str(e)}"

    finally:
        # Clean up thread local
        if hasattr(_thread_local, "from_mail_id"):
            delattr(_thread_local, "from_mail_id")
        if hasattr(_thread_local, "request"):
            delattr(_thread_local, "request")
