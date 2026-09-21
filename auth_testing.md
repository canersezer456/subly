# Subly Auth Testing Playbook

## Emergent Google OAuth

1. Start OAuth from the login screen using the current browser origin plus `/dashboard` as the redirect.
2. Return to the app with `#session_id=...` in the URL fragment.
3. The frontend must detect the fragment through `useLocation().hash`, call the backend exchange endpoint, and let the backend call Emergent Auth `/auth/v1/env/oauth/session-data`.
4. The backend stores the returned provider session token in an httpOnly, Secure, SameSite=None `session_token` cookie and `/api/auth/me` is the source of truth.
5. Logout must call the backend and clear the React Query session cache.

## MVP Demo Auth

The password flow is a local demo account flow for Subly. It is not a third-party integration and must never expose a password or session token in JSON.

## Financial Data Boundary

Automatic bank/card scanning is MOCKED in the first MVP using clearly labeled sample transactions. Do not claim live financial connectivity until a provider, credentials, consent flow, and read-only scopes are supplied.

## Verification

- Verify `/api/auth/me` with a valid session cookie or Authorization bearer fallback.
- Verify protected subscription CRUD with the same session.
- Verify the unauthenticated API returns 401 for protected endpoints.
- Verify the browser can complete the demo email/password login and the main dashboard flow.
- Verify the Google button points to `auth.emergentagent.com` with a redirect derived only from `window.location.origin + /dashboard`.
- Verify a simulated invalid callback fragment fails safely without exposing the session id.