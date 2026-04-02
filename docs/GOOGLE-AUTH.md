# Google Workspace Setup

KOVO can access Google Docs, Drive, Gmail, Calendar, and Sheets on your behalf. Setup is a **two-step process**:

## The Two Steps

```mermaid
flowchart TD
    A["Step 1: App Registration\n(Dashboard Setup Wizard)"] -->|Saves credentials.json| B["Step 2: User Authorization\n(/auth_google in Telegram)"]
    B -->|Saves token.json| C["✅ Google Access Working"]

    A1["Tells Google:\n'this app exists'"] -.-> A
    B1["Tells Google:\n'I authorize this app\nto access MY data'"] -.-> B

    style A fill:#378ADD,color:#fff,stroke:none
    style B fill:#f59e0b,color:#fff,stroke:none
    style C fill:#10b981,color:#fff,stroke:none
    style A1 fill:none,stroke:#378ADD,color:#666
    style B1 fill:none,stroke:#f59e0b,color:#666
```

## Step 1: Create Google Credentials (Dashboard)

This happens during the Setup Wizard, or you can do it later from Settings.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create or select a project
2. Enable the APIs KOVO needs:
   - [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
   - [Google Docs API](https://console.cloud.google.com/apis/library/docs.googleapis.com)
   - [Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
   - [Google Calendar API](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
   - [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
3. Go to [Credentials](https://console.cloud.google.com/apis/credentials) → **Create Credentials** → **OAuth 2.0 Client ID** → select **Desktop app**
4. Download the JSON file
5. Paste its contents into the Setup Wizard's Google page (or upload to `config/google-credentials.json`)

> **What this does:** Registers your KOVO installation as an app with Google. The JSON file contains your `client_id` and `client_secret` — it's like a passport for the app, but it doesn't grant access to any data yet.

## Step 2: Authorize Your Account (Telegram)

After the Setup Wizard is complete and KOVO is running:

1. Open your KOVO bot in Telegram
2. Send: `/auth_google`
3. KOVO replies with an authorization URL
4. Open the URL in your browser
5. Sign in with your Google account
6. Click **"Allow"** to grant KOVO access
7. Copy the authorization code shown
8. Paste it back in Telegram

```mermaid
sequenceDiagram
    participant You
    participant KOVO
    participant Google

    You->>KOVO: /auth_google
    KOVO->>You: Here's the auth URL
    You->>Google: Open URL, sign in
    Google->>You: Authorization code
    You->>KOVO: Paste code
    KOVO->>Google: Exchange code for token
    Google->>KOVO: Access token + refresh token
    KOVO->>You: ✅ Google connected!
```

> **What this does:** You personally authorize KOVO to access your Gmail, Drive, etc. The resulting token is stored at `config/google-token.json` and auto-refreshes — you only do this once.

## After Setup

Once authorized, you can talk to KOVO naturally:

- "Send an email to john@example.com about the project update"
- "What's on my calendar tomorrow?"
- "Find the Q3 report on Google Drive"
- "Create a new Google Doc titled Meeting Notes"

## Common Issues

| Problem | Cause | Fix |
|---|---|---|
| "Not authorized" | Step 2 not done | Send `/auth_google` in Telegram |
| "Invalid client" | Wrong credentials JSON | Re-download from Cloud Console |
| "Access denied" | API not enabled | Enable all 5 APIs in Cloud Console |
| "Token expired" | Refresh token revoked | Run `/auth_google` again |
