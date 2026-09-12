# Google OAuth setup

ContextIQ uses a single Google sign-in flow for identity, Gmail read access and Calendar event access.

## Google Cloud Console

1. Create or select a Google Cloud project.
2. Enable **Gmail API** and **Google Calendar API**.
3. Configure the OAuth consent screen.
4. During hackathon development keep the app in **Testing** and add every demo Google account as a test user.
5. Create an **OAuth 2.0 Client ID → Web application**.
6. Add this authorized redirect URI for local development:

```text
http://localhost:8501
```

7. Download the client JSON and save it as:

```text
credentials/google_oauth_client.json
```

Do not commit this file.

## Scopes requested

```text
openid
userinfo.email
userinfo.profile
gmail.readonly
calendar.events
```

`gmail.readonly` is a Google restricted scope. The hackathon/testing setup can use explicit OAuth test users; public production distribution requires Google verification and potentially additional security requirements.

`calendar.events` is intentionally narrower than full Calendar access.

## Troubleshooting

If Google reports `redirect_uri_mismatch`, ensure both the Google Cloud OAuth client and `.env` use exactly:

```text
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8501
```

If Gmail sync reports that Google Workspace is not connected, sign out of ContextIQ and use **Continue with Google** again so the per-user refresh token is stored.
