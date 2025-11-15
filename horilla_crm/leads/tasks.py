import email
import email.utils
import imaplib
import logging
from datetime import datetime

import requests
from celery import shared_task

from horilla_mail.horilla_outlook import refresh_outlook_token

from .models import EmailToLeadConfig, Lead, LeadStatus

logger = logging.getLogger(__name__)


@shared_task
def fetch_emails_to_leads():
    """Fetch today's emails from all configured email accounts and create Leads."""

    configs = EmailToLeadConfig.objects.all()

    if not configs.exists():
        return {"status": "error", "message": "No email settings configured."}

    total_created = 0
    total_filtered = 0
    results = []

    for config in configs:
        try:
            if config.mail.type == "mail":
                created_count, filtered_count = fetch_from_imap(config)
            elif config.mail.type == "outlook":
                created_count, filtered_count = fetch_from_outlook(config)
            else:
                results.append(
                    {
                        "email": config.mail.username,
                        "error": f"Unknown mail type: {config.mail.type}",
                    }
                )
                continue

            total_created += created_count
            total_filtered += filtered_count
            results.append(
                {
                    "email": config.mail.username,
                    "created": created_count,
                    "filtered_by_keywords": filtered_count,
                }
            )

        except Exception as e:
            logger.error(f"Error fetching emails for {config.mail.username}: {str(e)}")
            results.append({"email": config.mail.username, "error": str(e)})

    return {
        "status": "success",
        "total_leads_created": total_created,
        "total_filtered_by_keywords": total_filtered,
        "details": results,
    }


def fetch_from_imap(config):
    """Fetch emails using IMAP for standard mail configurations."""
    imap_conf = {
        "host": config.mail.host,
        "port": config.mail.port,
        "use_ssl": True,
    }

    if imap_conf["use_ssl"]:
        mail = imaplib.IMAP4_SSL(imap_conf["host"], imap_conf["port"])
    else:
        mail = imaplib.IMAP4(imap_conf["host"], imap_conf["port"])

    mail.login(config.mail.username, config.mail.get_decrypted_password())
    mail.select("inbox")

    # Get today's date in IMAP format
    today = datetime.now().strftime("%d-%b-%Y")
    result, data = mail.search(None, f"(SINCE {today})")

    email_ids = data[0].split()
    allowed_senders = config.get_accepted_emails()
    created_count = 0
    filtered_count = 0

    for e_id in email_ids:
        res, msg_data = mail.fetch(e_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        result = process_email_message(msg, config, allowed_senders)
        if result == "created":
            created_count += 1
        elif result == "filtered":
            filtered_count += 1

    mail.logout()
    return created_count, filtered_count


def fetch_from_outlook(config):
    """Fetch emails using Microsoft Graph API for Outlook configurations."""

    if not config.mail.token or "access_token" not in config.mail.token:
        raise ValueError("No valid access token found for Outlook configuration")

    access_token = config.mail.token["access_token"]

    # Get today's date in ISO 8601 format
    today = datetime.now().strftime("%Y-%m-%dT00:00:00Z")

    # Microsoft Graph API endpoint
    api_endpoint = (
        config.mail.outlook_api_endpoint or "https://graph.microsoft.com/v1.0"
    )
    url = f"{api_endpoint}/me/messages"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Filter for today's emails
    params = {
        "$filter": f"receivedDateTime ge {today}",
        "$select": "id,subject,from,body,bodyPreview,internetMessageId,internetMessageHeaders",
        "$top": 100,
    }
    response = requests.get(url, headers=headers, params=params)

    # Auto-refresh token if expired
    if response.status_code == 401:
        config.mail = refresh_outlook_token(config.mail)

        # Retry with new token
        headers["Authorization"] = f'Bearer {config.mail.token["access_token"]}'
        response = requests.get(url, headers=headers, params=params)

    response.raise_for_status()
    messages = response.json().get("value", [])

    allowed_senders = config.get_accepted_emails()
    created_count = 0
    filtered_count = 0

    for msg in messages:
        result = process_outlook_message(msg, config, allowed_senders)
        if result == "created":
            created_count += 1
        elif result == "filtered":
            filtered_count += 1

    return created_count, filtered_count


def process_email_message(msg, config, allowed_senders):
    """
    Process an email message from IMAP and create a Lead if needed.
    Returns: "created", "filtered", "skipped", or False
    """

    message_id = msg.get("Message-ID", "")

    if Lead.objects.filter(email_message_id=message_id).exists():
        return "skipped"

    in_reply_to = msg.get("In-Reply-To", "")
    references = msg.get("References", "")

    # Skip if this is a reply in an existing thread
    if check_existing_thread(in_reply_to, references):
        return "skipped"

    sender = email.utils.parseaddr(msg["From"])[1]

    if allowed_senders and sender.lower() not in allowed_senders:
        return "skipped"

    subject = msg.get("Subject", "(No Subject)")
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    # Check keyword filters
    if not config.matches_keywords(subject, body):
        logger.info(f"Email from {sender} filtered out by keywords. Subject: {subject}")
        return "filtered"

    Lead.objects.create(
        title=subject,
        email=sender,
        requirements=body,
        lead_owner=config.lead_owner,
        lead_status=LeadStatus.objects.first(),
        company=config.company,
        lead_source="email",
        email_message_id=message_id,
    )
    return "created"


def process_outlook_message(msg, config, allowed_senders):
    """
    Process an Outlook message from Microsoft Graph API and create a Lead if needed.
    Returns: "created", "filtered", "skipped", or False
    """

    message_id = msg.get("internetMessageId", "")

    if Lead.objects.filter(email_message_id=message_id).exists():
        return "skipped"

    # Extract In-Reply-To and References from headers
    in_reply_to = ""
    references = ""
    headers = msg.get("internetMessageHeaders", [])
    for header in headers:
        if header.get("name") == "In-Reply-To":
            in_reply_to = header.get("value", "")
        elif header.get("name") == "References":
            references = header.get("value", "")

    # Skip if this is a reply in an existing thread
    if check_existing_thread(in_reply_to, references):
        return "skipped"

    sender = msg.get("from", {}).get("emailAddress", {}).get("address", "")

    if allowed_senders and sender.lower() not in allowed_senders:
        return "skipped"

    subject = msg.get("subject", "(No Subject)")

    # Get body content (prefer text, fallback to bodyPreview)
    body = ""
    if msg.get("body"):
        body = msg["body"].get("content", "")
    if not body:
        body = msg.get("bodyPreview", "")

    # Check keyword filters
    if not config.matches_keywords(subject, body):
        logger.info(f"Email from {sender} filtered out by keywords. Subject: {subject}")
        return "filtered"

    Lead.objects.create(
        title=subject,
        email=sender,
        requirements=body,
        lead_owner=config.lead_owner,
        lead_status=LeadStatus.objects.first(),
        company=config.company,
        lead_source="email",
        email_message_id=message_id,
    )
    return "created"


def check_existing_thread(in_reply_to, references):
    """Check if email is part of an existing thread."""

    existing_lead = None
    if in_reply_to:
        existing_lead = Lead.objects.filter(email_message_id=in_reply_to).first()

    if not existing_lead and references:
        # References contains all message IDs in the thread
        ref_ids = references.split()
        if ref_ids:
            existing_lead = Lead.objects.filter(email_message_id__in=ref_ids).first()

    return existing_lead is not None
