---
name: google
description: Read and write Google Docs, search Drive files, send and read Gmail
tools: [google_api]
trigger: google, docs, drive, gmail, email, document, spreadsheet, send email, read email, upload, download, calendar, create doc, open doc, write doc
---

# Google Workspace Skill

## Capabilities
- **Google Docs**: Create documents, read content, append text
- **Google Drive**: Search files, upload, download, share
- **Gmail**: Send emails, read inbox, search messages

## Procedures

### Create a Google Doc
Use `create_document(title)` then `append_to_document(doc_id, content)`.

### Send an Email
Use `send_email(to, subject, body)`.

### Search Drive
Use `search_drive(query)` — returns list of files with id, name, webViewLink.

### Read Gmail Inbox
Use `list_emails(max_results=10)` for recent messages.

## Setup
Google OAuth2 credentials must be in `/opt/kovo/config/google-credentials.json`.
Run `/auth_google` in Telegram to complete the first-time auth flow.
Tokens are stored in `/opt/kovo/config/google-token.json`.
