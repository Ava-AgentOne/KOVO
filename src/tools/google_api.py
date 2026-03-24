"""
Google Workspace API client — Docs, Drive, Gmail.
Uses OAuth2 (user account). Credentials from google-credentials.json.
Tokens persisted in google-token.json.
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

_CREDS_FILE = Path("/opt/kovo/config/google-credentials.json")
_TOKEN_FILE = Path("/opt/kovo/config/google-token.json")


class GoogleAPIError(Exception):
    pass


class GoogleNotConfiguredError(GoogleAPIError):
    """Raised when credentials haven't been set up yet."""
    pass


def _get_credentials():
    """Load or refresh OAuth2 credentials. Raises GoogleNotConfiguredError if not set up."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as e:
        raise GoogleAPIError(f"Google auth libraries not installed: {e}")

    if not _CREDS_FILE.exists():
        raise GoogleNotConfiguredError(
            "Google credentials file not found. "
            "Download OAuth2 credentials from Google Console and save to "
            f"{_CREDS_FILE}"
        )

    creds = None
    if _TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                _TOKEN_FILE.write_text(creds.to_json())
            except Exception as e:
                log.warning("Token refresh failed: %s — re-auth required", e)
                creds = None

    if not creds:
        raise GoogleNotConfiguredError(
            "Google token not found or expired. "
            "Run /auth_google in Telegram to authenticate."
        )

    return creds


def start_auth_flow() -> tuple[str, object]:
    """
    Step 1 of headless OAuth: build the flow and return (auth_url, flow).
    The caller should send auth_url to the user and store flow for step 2.
    Raises GoogleAPIError if credentials file is missing.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not _CREDS_FILE.exists():
        raise GoogleAPIError(
            f"Credentials file not found at {_CREDS_FILE}. "
            "Download OAuth2 credentials from Google Console first."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(_CREDS_FILE), _SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    auth_url, _ = flow.authorization_url(prompt="consent")
    return auth_url, flow


def complete_auth_flow(flow, code: str) -> str:
    """
    Step 2 of headless OAuth: exchange the user-provided code for a token.
    Returns a status string.
    """
    try:
        flow.fetch_token(code=code.strip())
        creds = flow.credentials
        _TOKEN_FILE.write_text(creds.to_json())
        return "✅ Google authentication successful. Token saved."
    except Exception as e:
        return f"❌ Auth failed: {e}"


class GoogleAPI:
    """Wrapper around Google Workspace APIs (Docs, Drive, Gmail)."""

    def __init__(self):
        self._creds = None

    def _build(self, service: str, version: str):
        from googleapiclient.discovery import build
        if self._creds is None:
            self._creds = _get_credentials()
        return build(service, version, credentials=self._creds, cache_discovery=False)

    # ---- Docs ----

    def create_document(self, title: str) -> dict:
        """Create a new Google Doc. Returns {id, title, url}."""
        service = self._build("docs", "v1")
        doc = service.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]
        return {
            "id": doc_id,
            "title": doc["title"],
            "url": f"https://docs.google.com/document/d/{doc_id}/edit",
        }

    def get_document(self, doc_id: str) -> dict:
        """Read a Google Doc. Returns {id, title, body_text}."""
        service = self._build("docs", "v1")
        doc = service.documents().get(documentId=doc_id).execute()
        # Extract plain text from document body
        text_parts = []
        for elem in doc.get("body", {}).get("content", []):
            for para_elem in elem.get("paragraph", {}).get("elements", []):
                tr = para_elem.get("textRun", {})
                if tr.get("content"):
                    text_parts.append(tr["content"])
        return {
            "id": doc_id,
            "title": doc.get("title", ""),
            "body_text": "".join(text_parts),
        }

    def append_to_document(self, doc_id: str, text: str) -> dict:
        """Append text to an existing Google Doc."""
        service = self._build("docs", "v1")
        requests = [{"insertText": {"location": {"index": 1}, "text": text}}]
        result = service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()
        return {"doc_id": doc_id, "updated": True}

    # ---- Drive ----

    def search_drive(self, query: str, max_results: int = 10) -> list[dict]:
        """Search Drive files. Returns list of {id, name, mimeType, webViewLink}."""
        service = self._build("drive", "v3")
        results = service.files().list(
            q=f"name contains '{query}'",
            pageSize=max_results,
            fields="files(id,name,mimeType,webViewLink,modifiedTime)",
        ).execute()
        return results.get("files", [])

    def upload_file(self, local_path: str, parent_folder_id: str | None = None) -> dict:
        """Upload a local file to Drive. Returns {id, name, webViewLink}."""
        from googleapiclient.http import MediaFileUpload
        import mimetypes

        path = Path(local_path)
        mime_type, _ = mimetypes.guess_type(str(path))
        mime_type = mime_type or "application/octet-stream"

        service = self._build("drive", "v3")
        file_metadata = {"name": path.name}
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]

        media = MediaFileUpload(str(path), mimetype=mime_type)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id,name,webViewLink",
        ).execute()
        return file

    # ---- Gmail ----

    def send_email(self, to: str, subject: str, body: str, html: bool = False) -> dict:
        """Send an email (plain text or HTML). Returns {message_id}."""
        import base64
        from email.mime.text import MIMEText

        service = self._build("gmail", "v1")
        subtype = "html" if html else "plain"
        message = MIMEText(body, subtype)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return {"message_id": result["id"]}

    def list_emails(self, max_results: int = 10, query: str = "") -> list[dict]:
        """List recent emails. Returns list of {id, subject, from, snippet, date}."""
        service = self._build("gmail", "v1")
        list_result = service.users().messages().list(
            userId="me", maxResults=max_results, q=query
        ).execute()
        messages = []
        for msg_ref in list_result.get("messages", []):
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                ).execute()
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                messages.append({
                    "id": msg_ref["id"],
                    "subject": headers.get("Subject", "(no subject)"),
                    "from": headers.get("From", ""),
                    "date": headers.get("Date", ""),
                    "snippet": msg.get("snippet", ""),
                })
            except Exception as e:
                log.warning("Failed to fetch email %s: %s", msg_ref["id"], e)
        return messages
