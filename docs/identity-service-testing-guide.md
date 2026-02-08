# Identity Service — Testing Guide

This document describes how to test the identity service's login/logout flows, including the end-to-end OIDC redirect flow between the WebShell frontend and the self-hosted identity provider.

---

## Prerequisites

| Component | URL | Purpose |
|-----------|-----|---------|
| Identity Service | `http://localhost:8003` | Self-hosted OIDC identity provider |
| WebShell (Next.js) | `http://localhost:3000` | Frontend application |
| Docker Compose | — | Orchestrates all services |

### 1. Start All Services

```bash
cd /path/to/fastmicro
docker compose up -d
docker compose ps   # verify all containers are healthy
```

### 2. Seed a Test User

The identity service API provides a registration endpoint. Create a user via curl:

```bash
curl -X POST http://localhost:8003/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "Test1234!",
    "full_name": "Test User"
  }'
```

You should receive a `201 Created` with the new user's ID.

---

## Flow 1: Protected Route → Login → Redirect Back

This is the primary OIDC Authorization Code + PKCE flow.

### Step-by-Step

1. **Open WebShell**  
   Navigate to `http://localhost:3000` in your browser.

2. **Click a Protected Feature**  
   Click "Dashboard" or navigate to `http://localhost:3000/dashboard`.

3. **Automatic Redirect to Identity Service**  
   Since you are not authenticated, NextAuth redirects the browser through:
   ```
   http://localhost:3000/api/auth/signin
     → http://localhost:8003/oauth2/authorize
       → http://localhost:8003/login?response_type=code&client_id=...&redirect_uri=...&scope=openid+profile+email&state=...&code_challenge=...&code_challenge_method=S256
   ```
   You should see the **Identity Service Login Page**.

4. **Sign In**  
   Enter the test user credentials:
   - Email: `testuser@example.com`
   - Password: `Test1234!`
   - Click **Sign In**

5. **Consent Page** (first time only)  
   If this is the first login, the consent page appears asking you to authorize WebShell to access your profile. Click **Allow**.

6. **Redirect Back to WebShell**  
   After consent, the browser redirects to:
   ```
   http://localhost:3000/api/auth/callback/identity-service?code=...&state=...
   ```
   NextAuth exchanges the authorization code for tokens, and you land on the protected Dashboard page.

7. **Verify Authentication**  
   - You should see the Dashboard content
   - The session is active (check browser cookies for `next-auth.session-token`)

### What to Observe

| Step | What You See | What's Happening |
|------|-------------|------------------|
| 2 | Redirect flash | NextAuth `authorized` callback returns `false` → redirect to login |
| 3 | Identity Service login page | OIDC Authorization endpoint redirects to `/login` |
| 4 | Form submission | POST `/login` authenticates user, creates session, redirects to `/consent` |
| 5 | Scope approval | Consent page shows requested scopes |
| 6 | Brief redirect | Auth code exchange via back-channel (server-to-server via Docker network) |
| 7 | Dashboard | Fully authenticated, JWT tokens in session |

---

## Flow 2: Logout

### Step-by-Step

1. **While authenticated**, click the user menu / logout button in WebShell.
2. NextAuth signs out locally and can optionally redirect to:
   ```
   http://localhost:8003/logout?post_logout_redirect_uri=http://localhost:3000&client_id=webshell
   ```
3. The identity service clears the session cookie and shows the **"You have been signed out"** confirmation page.
4. After 5 seconds (or clicking "Return to Application"), you are redirected back to WebShell.
5. Accessing `/dashboard` again will trigger the login flow.

---

## Flow 3: Forgot Password

### Step-by-Step

1. On the login page, click **"Forgot password?"**
2. You are taken to `/forgot-password` with OIDC params preserved.
3. Enter your email address and click **Send Reset Link**.
4. A confirmation page is shown: *"If an account exists for your-email, we've sent a reset link."*
   - Note: In local development, no email is actually sent. Check logs for the reset token, or query the in-memory store.
5. Navigate to `/reset-password?token=<token>` (from the log output).
6. Enter and confirm your new password; click **Reset Password**.
7. On success, click **Sign In** to return to the login page.

### Testing the API Directly

```bash
# Request password reset (always returns 200 to prevent enumeration)
curl -X POST http://localhost:8003/api/v1/auth/password/reset-request \
  -H "Content-Type: application/json" \
  -d '{"email": "testuser@example.com", "callback_url_template": "/reset-password?token={token}"}'

# Reset password with token from logs
curl -X POST http://localhost:8003/api/v1/auth/password/reset \
  -H "Content-Type: application/json" \
  -d '{"token": "<token-from-logs>", "new_password": "NewPass1234!"}'
```

---

## Flow 4: Social Login (Google) — Placeholder

The login page includes a UI skeleton for external identity providers.
When configured, the flow works as:

1. User clicks **"Continue with Google"** on the login page.
2. Browser redirects to `/external/login/google?<oidc_params>`.
3. Identity service stores OIDC params in session, redirects to Google OAuth2.
4. After Google authentication, callback at `/external/callback/google`.
5. Identity service finds or creates the user by email, creates a session, redirects to `/consent`.
6. Normal consent → auth code → redirect back to WebShell.

> **To enable:** Uncomment the `external_providers` list in `routes.py` and implement the external login/callback handlers. See `routes.py` for the integration point.

---

## Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Login page not loading | Identity service not running | `docker compose up identity-service -d` |
| "Invalid redirect URI" | WebShell callback URL not registered | Check `ALLOWED_REDIRECT_URIS` in identity-service config |
| Redirect loop | Session cookie not being set | Check browser dev tools → Cookies, ensure `Secure` flag matches protocol |
| Token exchange fails | Docker network issue | Ensure `IDENTITY_SERVICE_INTERNAL_URL=http://identity-service:8000` in webshell env |
| "Invalid credentials" | Wrong password or user not registered | Register user via API first (see Prerequisites) |
| Consent page appears every time | Consent not being remembered | Click "Remember my decision" checkbox on consent page |

---

## Architecture Diagram

```
┌──────────────────┐     ┌─────────────────────┐     ┌───────────────────┐
│                  │     │                     │     │                   │
│   WebShell       │     │  Identity Service   │     │   External IdP    │
│   (Next.js)      │     │  (FastAPI)          │     │   (Google, etc.)  │
│   :3000          │     │  :8003              │     │                   │
│                  │     │                     │     │                   │
│  ┌────────────┐  │     │  ┌───────────────┐  │     │                   │
│  │  NextAuth  │──┼────►│  │ /oauth2/      │  │     │                   │
│  │  (OAuth)   │  │     │  │  authorize    │──┼────►│  (future)         │
│  └────────────┘  │     │  └──────┬────────┘  │     │                   │
│        ▲         │     │         │           │     └───────────────────┘
│        │         │     │         ▼           │
│  ┌─────┴──────┐  │     │  ┌───────────────┐  │
│  │ /api/auth/ │  │     │  │ /login        │  │
│  │  callback  │◄─┼─────│  │ /consent      │  │
│  └────────────┘  │     │  │ /logout       │  │
│                  │     │  │ /forgot-pw    │  │
│  Protected:      │     │  │ /reset-pw     │  │
│  /dashboard      │     │  └───────────────┘  │
│  /admin          │     │                     │
│                  │     │  ┌───────────────┐  │
│                  │     │  │ /oauth2/token │  │
│                  │◄────┼──│ /oauth2/      │  │
│                  │     │  │  userinfo     │  │
│                  │     │  └───────────────┘  │
└──────────────────┘     └─────────────────────┘
    Browser URLs              Docker internal:
    localhost:3000            identity-service:8000
    localhost:8003            (back-channel token exchange)
```

---

## Running Automated Tests

```bash
# Identity service unit tests
cd services/identity-service
uv run pytest tests/ -v

# All tests with markers
uv run pytest tests/ -v -m unit
```
