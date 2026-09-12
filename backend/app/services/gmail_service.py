from pathlib import Path
from email.utils import parsedate_to_datetime
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# ==========================================================
# GOOGLE OAUTH / SERVICES
# ==========================================================

from backend.app.services.google_token_store import (
    load_google_credentials,
    save_google_credentials,
)
from backend.app.user_context import require_current_user

WORKSPACE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def get_google_credentials(user_email: str | None = None):
    """Load and refresh the authenticated user's encrypted Google token."""
    user_email = user_email or require_current_user()
    creds = load_google_credentials(user_email, scopes=WORKSPACE_SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_google_credentials(user_email, creds)
        except Exception as error:
            raise RuntimeError(
                "Google authorization expired. Sign in with Google again."
            ) from error

    if not creds or not creds.valid:
        raise RuntimeError(
            "Google Workspace is not connected for this ContextIQ user. "
            "Sign in with Google to connect Gmail and Calendar."
        )

    return creds


def get_gmail_service(user_email: str | None = None):
    return build(
        "gmail",
        "v1",
        credentials=get_google_credentials(user_email),
        cache_discovery=False,
    )


def get_calendar_service(user_email: str | None = None):
    return build(
        "calendar",
        "v3",
        credentials=get_google_credentials(user_email),
        cache_discovery=False,
    )


# ==========================================================
# LIST GMAIL MESSAGE IDS
# ==========================================================

def list_gmail_messages(
    service=None,
    max_results: int = 10
):
    """
    Return only Gmail message ID strings.
    """

    if service is None:
        service = get_gmail_service()

    message_ids = []

    for label in ["INBOX", "SPAM"]:

        response = (
            service
            .users()
            .messages()
            .list(
                userId="me",
                labelIds=[label],
                maxResults=max_results
            )
            .execute()
        )

        for message in response.get(
            "messages",
            []
        ):

            message_id = message.get(
                "id"
            )

            if message_id:
                message_ids.append(
                    message_id
                )

    return list(
        dict.fromkeys(
            message_ids
        )
    )


# ==========================================================
# GET RAW MESSAGE
# ==========================================================

def get_raw_gmail_message(
    service=None,
    message_id=None
):
    """
    Fetch one raw Gmail message.

    Supports:
        get_raw_gmail_message("ID")

        get_raw_gmail_message(
            service,
            "ID"
        )

        get_raw_gmail_message(
            service=service,
            message_id="ID"
        )
    """

    if (
        message_id is None
        and isinstance(service, str)
    ):

        message_id = service
        service = None

    if service is None:
        service = get_gmail_service()

    if not message_id:

        raise ValueError(
            "Gmail message ID is required."
        )

    return (
        service
        .users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full"
        )
        .execute()
    )


# ==========================================================
# DECODE BODY
# ==========================================================

def decode_body_data(
    data
) -> str:

    if not data:
        return ""

    try:

        decoded = (
            base64
            .urlsafe_b64decode(
                data
            )
        )

        return decoded.decode(
            "utf-8",
            errors="ignore"
        )

    except Exception:

        return ""


# ==========================================================
# EXTRACT BODY
# ==========================================================

def extract_message_body(
    payload: dict
) -> str:

    direct_data = (
        payload
        .get("body", {})
        .get("data")
    )

    if direct_data:

        body = decode_body_data(
            direct_data
        )

        if body:
            return body

    parts = payload.get(
        "parts",
        []
    )

    # Prefer text/plain
    for part in parts:

        if part.get(
            "mimeType"
        ) == "text/plain":

            data = (
                part
                .get("body", {})
                .get("data")
            )

            body = decode_body_data(
                data
            )

            if body:
                return body

    # Recursive MIME search
    for part in parts:

        nested_parts = part.get(
            "parts",
            []
        )

        if nested_parts:

            nested_payload = {
                "body": part.get(
                    "body",
                    {}
                ),
                "parts": nested_parts
            }

            body = extract_message_body(
                nested_payload
            )

            if body:
                return body

    return ""


# ==========================================================
# EXTRACT ATTACHMENTS
# ==========================================================

def extract_attachments(
    payload: dict
):

    attachments = []

    def walk(parts):

        for part in parts:

            filename = part.get(
                "filename",
                ""
            )

            mime_type = part.get(
                "mimeType",
                ""
            )

            body = part.get(
                "body",
                {}
            )

            attachment_id = body.get(
                "attachmentId"
            )

            if (
                filename
                and attachment_id
            ):

                attachments.append(
                    {
                        "filename": filename,
                        "mime_type": mime_type,
                        "attachment_id": attachment_id,
                    }
                )

            nested_parts = part.get(
                "parts",
                []
            )

            if nested_parts:
                walk(
                    nested_parts
                )

    walk(
        payload.get(
            "parts",
            []
        )
    )

    return attachments


# ==========================================================
# PARSE GMAIL MESSAGE
# ==========================================================

def parse_gmail_message(
    message,
    service=None
):
    """
    Parse Gmail message.

    Supports a raw message dictionary OR a message ID.

    Returns both modern field names and compatibility
    aliases so existing ContextIQ code continues to work.
    """

    # ------------------------------------------------------
    # If a message ID was supplied
    # ------------------------------------------------------

    if isinstance(
        message,
        str
    ):

        message = (
            get_raw_gmail_message(
                service=service,
                message_id=message
            )
        )

    if not isinstance(
        message,
        dict
    ):

        raise TypeError(
            "Expected Gmail message dictionary."
        )

    payload = message.get(
        "payload",
        {}
    )

    headers = payload.get(
        "headers",
        []
    )

    header_map = {}

    for header in headers:

        name = (
            header
            .get("name", "")
            .strip()
            .lower()
        )

        value = (
            header
            .get("value", "")
        )

        header_map[name] = value

    # ------------------------------------------------------
    # Read fields
    # ------------------------------------------------------

    sender = header_map.get(
        "from",
        ""
    )

    recipient = header_map.get(
        "to",
        ""
    )

    subject = header_map.get(
        "subject",
        ""
    )

    body = extract_message_body(
        payload
    )

    # ------------------------------------------------------
    # Date
    # ------------------------------------------------------

    date_value = header_map.get(
        "date"
    )

    received_at = None

    if date_value:

        try:

            received_at = (
                parsedate_to_datetime(
                    date_value
                )
            )

            received_at = (
                received_at.replace(
                    tzinfo=None
                )
            )

        except Exception:

            received_at = None

    # ------------------------------------------------------
    # Gmail message ID
    # ------------------------------------------------------

    gmail_message_id = message.get(
        "id"
    )

    # ------------------------------------------------------
    # Attachments
    # ------------------------------------------------------

    attachments = extract_attachments(
        payload
    )

    # ------------------------------------------------------
    # IMPORTANT:
    # Return aliases used by different versions
    # of emails.py.
    # ------------------------------------------------------

    return {
        "gmail_message_id": gmail_message_id,

        # ContextIQ names
        "sender": sender,
        "recipient": recipient,

        # Compatibility aliases
        "from": sender,
        "to": recipient,

        # Common fields
        "subject": subject,
        "body": body,
        "received_at": received_at,

        # Attachment information
        "attachments": attachments,

        # Raw headers if needed later
        "headers": header_map,
    }


# ==========================================================
# GET + PARSE GMAIL MESSAGE
# ==========================================================

def get_gmail_message(
    service=None,
    message_id=None
):
    """
    Fetch and parse one Gmail message.

    Supports:

        get_gmail_message("ID")

        get_gmail_message(
            service,
            "ID"
        )

        get_gmail_message(
            service=service,
            message_id="ID"
        )
    """

    # ------------------------------------------------------
    # Support get_gmail_message("ID")
    # ------------------------------------------------------

    if (
        message_id is None
        and isinstance(service, str)
    ):

        message_id = service
        service = None

    if service is None:
        service = get_gmail_service()

    raw_message = (
        get_raw_gmail_message(
            service=service,
            message_id=message_id
        )
    )

    return parse_gmail_message(
        raw_message,
        service=service
    )


# ==========================================================
# DOWNLOAD ATTACHMENT
# ==========================================================

def download_attachment(
    service=None,
    message_id=None,
    attachment_id=None
):
    """
    Download one Gmail attachment.
    """

    # Support:
    # download_attachment(
    #     message_id,
    #     attachment_id
    # )

    if (
        isinstance(service, str)
        and isinstance(message_id, str)
        and attachment_id is None
    ):

        attachment_id = message_id
        message_id = service
        service = None

    if service is None:
        service = get_gmail_service()

    if not message_id:

        raise ValueError(
            "Gmail message ID is required."
        )

    if not attachment_id:

        raise ValueError(
            "Gmail attachment ID is required."
        )

    attachment = (
        service
        .users()
        .messages()
        .attachments()
        .get(
            userId="me",
            messageId=message_id,
            id=attachment_id
        )
        .execute()
    )

    data = attachment.get(
        "data",
        ""
    )

    return (
        base64
        .urlsafe_b64decode(
            data
        )
        if data
        else b""
    )