# Authentication Testing

## Environment
- Backend running
- Frontend running
- PostgreSQL connected
- OAuth credentials configured

---

# Google OAuth Login

## Valid Google Login

Steps:
1. Click "Continue with Google"
2. Complete OAuth flow
3. Return to Omni-AI

Expected:
- User authenticated
- JWT/session stored
- Redirect to workspace
- User session persists on refresh

Status:
- Passed

Notes:
-

---

## Google OAuth Redirect Validation

Steps:
1. Trigger Google OAuth
2. Validate redirect URI

Expected:
- No redirect_uri_mismatch
- No redirect loops
- Callback succeeds

Status:
- Passed

Notes:
-

---

# GitHub OAuth Login

## Valid GitHub Login

Steps:
1. Click "Continue with GitHub"
2. Complete OAuth flow
3. Return to Omni-AI

Expected:
- User authenticated
- Session persists
- Redirect successful

Status:
- Passed

Notes:
-

---

## GitHub OAuth Callback

Steps:
1. Complete GitHub OAuth
2. Validate callback flow

Expected:
- No callback errors
- No stuck loading states
- Session restored correctly

Status:
- Passed

Notes:
-

---

# Session Persistence

## Refresh Persistence

Steps:
1. Login via OAuth
2. Refresh browser

Expected:
- User remains authenticated
- Workspace loads correctly

Status:
- Passed

Notes:
-

---

# Logout Testing

## Logout Flow

Steps:
1. Click logout

Expected:
- Session cleared
- User redirected to landing page
- Protected routes inaccessible

Status:
- Passed

Notes:
-