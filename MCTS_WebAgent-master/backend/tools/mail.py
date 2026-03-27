
##############################################################################################################

# backend/tools/mail.py

import smtplib
import imaplib
import email
import base64
import os
import mimetypes
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from llm import get_llm

load_dotenv()

SMTP_HOST  = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT  = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER  = os.getenv("SMTP_USER")
SMTP_PASS  = os.getenv("SMTP_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", "manasi.official2024@gmail.com")

# Fixed sender signature — always used in AI-generated bodies
SENDER_NAME  = "Manasi"
SENDER_EMAIL = "manasi.official2024@gmail.com"

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def extract_name_from_email(email_address: str) -> str:
    """
    Best-effort extraction of a human-readable name from an email address.
    Examples:
      john.doe@gmail.com     → John Doe
      alice_smith@yahoo.com  → Alice Smith
      bob@company.com        → Bob
      support@example.com    → Support
    """
    if not email_address:
        return "there"

    # Strip display name if present e.g. "John Doe <john@x.com>"
    if "<" in email_address:
        display = email_address.split("<")[0].strip().strip('"')
        if display:
            return display.title()
        email_address = email_address.split("<")[1].rstrip(">").strip()

    local = email_address.split("@")[0]

    # Replace separators with spaces
    for sep in [".", "_", "-", "+"]:
        local = local.replace(sep, " ")

    # Remove trailing digits (e.g. john123 → john)
    parts = []
    for part in local.split():
        cleaned = part.rstrip("0123456789")
        if cleaned:
            parts.append(cleaned.capitalize())

    if parts:
        return " ".join(parts)

    return "there"


def generate_email_body(subject: str, recipient_email: str) -> str:
    """
    Generate a professional email body using the local LLM.
    Fills in recipient name from email address and signs off as Manasi.
    """
    recipient_name = extract_name_from_email(recipient_email)

    try:
        llm = get_llm()

        prompt = f"""Write a professional email body based on this subject.

Subject: {subject}
Recipient Name: {recipient_name}
Sender Name: {SENDER_NAME}
Sender Email: {SENDER_EMAIL}

Instructions:
- Start with: Dear {recipient_name},
- Write a clear, professional email body (5-8 lines)
- Do NOT include a subject line
- End with:
  Best regards,
  {SENDER_NAME}
  {SENDER_EMAIL}
- Use the exact recipient name and sender details above
- Do not use placeholder brackets like [Name] or [Your Name]
"""

        response = llm.invoke(prompt)
        body = str(response).strip()

        # Safety check — if LLM still used brackets, replace them
        body = body.replace("[Recipient's Name]", recipient_name)
        body = body.replace("[Your Name]", SENDER_NAME)
        body = body.replace("[Sender's Name]", SENDER_NAME)
        body = body.replace("[Name]", recipient_name)

        return body

    except Exception:
        return f"""Dear {recipient_name},

I am writing regarding: {subject}

Please let me know your thoughts at your earliest convenience.

Best regards,
{SENDER_NAME}
{SENDER_EMAIL}"""


# ──────────────────────────────────────────────────────────────────
# Send Email
# ──────────────────────────────────────────────────────────────────

def send_email(
    recipient: str,
    subject: str,
    body: str,
    attachment_data: str = None,       # base64-encoded file content
    attachment_name: str = None,       # original filename
) -> str:
    """
    Send an email with optional attachment.

    Args:
        recipient:       Recipient email address
        subject:         Email subject
        body:            Email body (empty = AI-generated)
        attachment_data: Base64-encoded file bytes (optional)
        attachment_name: Original filename with extension (optional)
    """
    if not SMTP_USER or not SMTP_PASS:
        return "SMTP credentials not configured in .env file"

    try:
        # Auto-generate body if empty
        if not body or not body.strip():
            body = generate_email_body(subject, recipient)

        # ── Build message ──────────────────────────────────────
        if attachment_data and attachment_name:
            # Use MIMEMultipart to support attachment
            msg = MIMEMultipart()
            msg["From"]    = EMAIL_FROM or SENDER_EMAIL
            msg["To"]      = recipient
            msg["Subject"] = subject or "No Subject"
            msg.attach(MIMEText(body, "plain"))

            # Decode base64 attachment
            try:
                file_bytes = base64.b64decode(attachment_data)
            except Exception:
                return "Attachment could not be decoded. Please try again."

            # Detect MIME type from filename
            mime_type, _ = mimetypes.guess_type(attachment_name)
            if mime_type:
                main_type, sub_type = mime_type.split("/", 1)
            else:
                main_type, sub_type = "application", "octet-stream"

            part = MIMEBase(main_type, sub_type)
            part.set_payload(file_bytes)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{attachment_name}"',
            )
            msg.attach(part)

        else:
            # Simple plain-text email
            msg = EmailMessage()
            msg["From"]    = EMAIL_FROM or SENDER_EMAIL
            msg["To"]      = recipient
            msg["Subject"] = subject or "No Subject"
            msg.set_content(body)

        # ── Send ───────────────────────────────────────────────
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)

        attachment_info = f"\nAttachment: {attachment_name}" if attachment_name else ""

        return f"""Email sent successfully

To: {recipient}
Subject: {subject}{attachment_info}

Body:
{body}
"""

    except Exception as e:
        return f"Error sending email: {str(e)}"


# ──────────────────────────────────────────────────────────────────
# Fetch Emails
# ──────────────────────────────────────────────────────────────────

def fetch_unread_emails() -> str:
    """Fetch 5 most recent emails from inbox"""

    if not SMTP_USER or not SMTP_PASS:
        return "Email credentials not configured in .env file"

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(SMTP_USER, SMTP_PASS)
        mail.select("inbox")

        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()

        if not email_ids:
            return "No emails found in inbox"

        recent_ids = email_ids[-5:]
        summaries  = []

        for eid in recent_ids:
            try:
                status, msg_data = mail.fetch(eid, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()[:150]
                            except Exception:
                                body = "Unable to decode"
                            break
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()[:150]
                    except Exception:
                        body = "Unable to decode"

                summaries.append({
                    "from":    msg["From"],
                    "subject": msg["Subject"],
                    "date":    msg["Date"],
                    "preview": body,
                })

            except Exception:
                continue

        mail.close()
        mail.logout()

        if not summaries:
            return "Could not fetch emails"

        result = f"Latest {len(summaries)} emails:\n\n"
        for i, e in enumerate(summaries, 1):
            result += f"{i}. From: {e['from']}\n"
            result += f"   Subject: {e['subject']}\n"
            result += f"   Date: {e['date']}\n"
            result += f"   Preview: {e['preview']}...\n\n"

        return result

    except Exception as e:
        return f"Error fetching emails: {str(e)}"