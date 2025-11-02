# Google OAuth Setup Guide

## Overview

This guide covers setting up Google OAuth for user authentication in the Imagineer application.

## The Redirect URI Issue (FIXED)

### Problem

The OAuth flow was constructing the redirect URI without the `/api/` prefix:
```
❌ WRONG: https://imagineer.joshwentworth.com/auth/google/callback
✓ CORRECT: https://imagineer-api.joshwentworth.com/api/auth/google/callback
```

**Root Cause**: Flask's `url_for()` function with multiple route decorators was choosing the route without the `/api/` prefix.

**Fix Applied**: `server/api.py` line 185-188 now explicitly ensures the `/api/` prefix is included:
```python
redirect_uri = url_for("auth_callback", _external=True)
# Force /api/ prefix if it's missing
if "/api/auth/google/callback" not in redirect_uri:
    redirect_uri = redirect_uri.replace("/auth/google/callback", "/api/auth/google/callback")
```

## Google Cloud Console Configuration

### 1. Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to: **APIs & Services** → **Credentials**
4. Click **"Create Credentials"** → **"OAuth client ID"**
5. Select **"Web application"**

### 2. Configure Authorized Origins

Add these authorized JavaScript origins:

**Development:**
```
http://localhost:10050
http://localhost:3000
http://127.0.0.1:10050
http://127.0.0.1:3000
```

**Production:**
```
https://imagineer.joshwentworth.com
https://imagineer-api.joshwentworth.com
https://imagineer-generator.web.app
https://imagineer-generator.firebaseapp.com
```

### 3. Configure Authorized Redirect URIs

**IMPORTANT**: The redirect URI MUST include the `/api/` prefix.

Add these authorized redirect URIs:

**Development:**
```
http://localhost:10050/api/auth/google/callback
http://127.0.0.1:10050/api/auth/google/callback
```

**Production:**
```
https://imagineer-api.joshwentworth.com/api/auth/google/callback
```

### 4. Copy Credentials

After creating the OAuth client:

1. **Client ID**: Copy this value
2. **Client Secret**: Copy this value (shown only once!)

### 5. Configure Environment Variables

Add credentials to your `.env.production` file:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret-here
FLASK_SECRET_KEY=your-flask-secret-key-here
```

**Generate Flask Secret Key:**
```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

## Authentication Flow

### How It Works

1. **User clicks "Login with Google"** → Frontend calls `/api/auth/login`
2. **Server redirects to Google** → With redirect_uri=`https://imagineer-api.joshwentworth.com/api/auth/google/callback`
3. **User authenticates with Google** → Google redirects back to our callback
4. **Callback processes token** → `/api/auth/google/callback` receives the OAuth token
5. **Session created** → User is logged in, role determined from `users.json`

### API Endpoints

All authentication endpoints have dual routes (with and without `/api/` prefix):

```
GET  /api/auth/login                 - Initiate OAuth flow
GET  /api/auth/google/callback       - Handle OAuth callback
GET  /api/auth/me                    - Get current user info
GET  /api/auth/logout                - Logout user
```

Alternative routes (deprecated but supported):
```
GET  /auth/login
GET  /auth/google/callback
GET  /auth/me
GET  /auth/logout
```

## User Roles

### Role System

The application uses a simple public + admin role system:

- **Public Users** (default): Can view public content
- **Admin Users**: Full access to all features

### Managing User Roles

Roles are stored in `server/users.json`:

```json
{
  "admin@example.com": {
    "role": "admin",
    "name": "Admin User"
  },
  "user@example.com": {
    "role": null,
    "name": "Regular User"
  }
}
```

**To make a user an admin:**

1. Edit `server/users.json`
2. Add the user's Google email with `"role": "admin"`
3. Restart the API server
4. User must log out and log in again for role to update

## Testing the Fix

### Test Locally

1. **Start the API server:**
   ```bash
   . venv/bin/activate
   python server/api.py
   ```

2. **Check redirect URI construction:**
   ```bash
   curl -v http://localhost:10050/api/auth/login 2>&1 | grep -i location
   ```

   Should see: `Location: https://accounts.google.com/o/oauth2/v2/auth?...redirect_uri=http%3A%2F%2Flocalhost%3A10050%2Fapi%2Fauth%2Fgoogle%2Fcallback`

3. **Decode the redirect_uri parameter:**
   ```
   http://localhost:10050/api/auth/google/callback  ✓ CORRECT (has /api/)
   ```

### Test in Production

1. **Access the login page:** `https://imagineer.joshwentworth.com`
2. **Click "Login with Google"**
3. **Check browser network tab:**
   - Look for the redirect to Google
   - Verify the `redirect_uri` parameter includes `/api/`
4. **Complete Google authentication**
5. **Verify successful callback**

## Troubleshooting

### Error: "redirect_uri_mismatch"

**Problem**: Google shows an error saying the redirect URI doesn't match.

**Solution**:
1. Check that Google Cloud Console has the correct redirect URI
2. Ensure it includes `/api/`: `https://imagineer-api.joshwentworth.com/api/auth/google/callback`
3. Make sure the protocol matches (http vs https)
4. Restart the API server after environment changes

### Error: "Error 400: invalid_request"

**Problem**: Missing or invalid OAuth parameters.

**Solution**:
1. Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
2. Check environment variables are loaded: `env | grep GOOGLE`
3. Restart the API server

### Session Not Persisting

**Problem**: User gets logged out immediately after login.

**Solution**:
1. Verify `FLASK_SECRET_KEY` is set and consistent
2. Check session cookie settings in `server/auth.py`
3. Ensure cookies are not being blocked by browser

### Wrong Role Assigned

**Problem**: Admin user showing as public user (or vice versa).

**Solution**:
1. Check `server/users.json` has correct email and role
2. User must log out and log back in for role changes to apply
3. Check server logs for role lookup issues

## Security Considerations

### Production Checklist

- [ ] `GOOGLE_CLIENT_SECRET` is never committed to git
- [ ] `FLASK_SECRET_KEY` is strong (32+ characters, randomly generated)
- [ ] `FLASK_ENV=production` is set for production environment
- [ ] HTTPS is enforced via Cloudflare/Talisman
- [ ] Session cookies are `HttpOnly` and `Secure`
- [ ] CORS is configured with explicit allowed origins
- [ ] Redirect URIs in Google Console match exactly

### Best Practices

1. **Use environment variables** for all secrets
2. **Rotate secrets regularly** (at least annually)
3. **Monitor authentication logs** for suspicious activity
4. **Limit admin users** to trusted individuals only
5. **Use HTTPS everywhere** in production

## Related Documentation

- **Auth Module**: `server/auth.py` - Core authentication logic
- **API Routes**: `server/api.py` lines 179-270 - Auth endpoints
- **Environment Config**: `.env.production` - Production credentials
- **User Management**: `server/users.json` - Role assignments

## Summary

**What Changed:**
- Fixed redirect URI construction in `server/api.py` to always include `/api/` prefix
- Server now correctly sends: `https://imagineer-api.joshwentworth.com/api/auth/google/callback`

**What You Need to Do:**
1. Update Google Cloud Console authorized redirect URIs to include `/api/`
2. Restart the API server
3. Test the login flow

**Correct Redirect URI for Production:**
```
https://imagineer-api.joshwentworth.com/api/auth/google/callback
```
