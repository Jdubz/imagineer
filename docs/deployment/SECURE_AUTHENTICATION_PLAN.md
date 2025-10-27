# Secure Authentication Plan

**Status:** Planning Phase
**Last Updated:** 2025-10-27
**Current Implementation:** Google OAuth session (legacy password gate removed)

> **Note:** The legacy password gate described below has been removed in favor of Google OAuth-based login as of October 27, 2025. The previous approach is retained here for historical context.

## Legacy Implementation (v1.0)

### Overview (legacy)
A simple password gate protects the frontend application:
- **Password:** Stored as environment variable (`VITE_APP_PASSWORD`)
- **Session:** 24-hour localStorage token
- **Validation:** Client-side password comparison
- **Logout:** Manual session clearing

### Files (legacy - removed October 27, 2025)
- `web/src/components/PasswordGate.jsx` - Legacy password gate component
- `web/src/styles/PasswordGate.css` - Legacy styling
- `web/.env.development` - Legacy development config key (`VITE_APP_PASSWORD`)
- `web/.env.production` - Legacy production config key (`VITE_APP_PASSWORD`)

### Security Limitations (legacy)
- ⚠️ **Client-side only** - Password visible in compiled JavaScript
- ⚠️ **No rate limiting** - Brute force attacks possible
- ⚠️ **Shared password** - Single credential for all users
- ⚠️ **No audit trail** - Cannot track who accessed the system
- ⚠️ **localStorage vulnerable** - Can be accessed by XSS attacks
- ⚠️ **No session revocation** - Cannot invalidate sessions remotely

### When Legacy Implementation Was Acceptable
✅ **Personal projects** on trusted networks
✅ **Development/staging environments**
✅ **Behind VPN** or firewall
✅ **Low-sensitivity content**

### When to Upgrade
🚨 **Public internet access**
🚨 **Multiple users** needing different access levels
🚨 **Sensitive content** or operations
🚨 **Compliance requirements** (HIPAA, SOC2, etc.)
🚨 **Commercial use**

---

## Recommended Authentication Strategy

### Phase 2: Backend Session Authentication (Recommended)

**Estimated Implementation Time:** 3-4 hours
**Complexity:** Medium
**Security Level:** ⭐⭐⭐⭐ (Good for most use cases)

#### Overview
Move authentication to the backend with proper session management:
- **Backend validates** credentials against hashed passwords
- **HTTP-only cookies** prevent XSS token theft
- **Session management** with expiration and revocation
- **Rate limiting** prevents brute force attacks
- **bcrypt password hashing** for secure storage

#### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  - Login form (username/password)                        │
│  - No password stored in code                            │
│  - Auth state from /api/auth/me                         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│               Flask Backend (server/api.py)              │
│                                                           │
│  POST /api/auth/login                                    │
│    ├─ Validate credentials                               │
│    ├─ Check rate limit                                   │
│    ├─ Hash password with bcrypt                          │
│    ├─ Create session                                     │
│    └─ Return HTTP-only cookie                            │
│                                                           │
│  GET /api/auth/me                                        │
│    ├─ Verify session cookie                              │
│    └─ Return user info                                   │
│                                                           │
│  POST /api/auth/logout                                   │
│    ├─ Invalidate session                                 │
│    └─ Clear cookie                                       │
│                                                           │
│  Middleware: @require_auth decorator                     │
│    └─ Protect all /api/* routes                          │
└─────────────────────────────────────────────────────────┘
```

#### Implementation Steps

##### 1. Add Backend Dependencies

**File:** `requirements.txt`
```txt
# Add these dependencies
flask-login>=0.6.3       # Session management
bcrypt>=4.1.2            # Password hashing
redis>=5.0.1             # Session store (optional, can use in-memory)
```

##### 2. Create User Model

**File:** `server/auth.py` (new file)
```python
"""
Authentication module for Imagineer API
"""
import bcrypt
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session

# In-memory session store (replace with Redis for production)
sessions = {}
SESSION_DURATION = timedelta(hours=24)

# User credentials (hashed passwords)
# In production, move to database or environment variables
USERS = {
    "admin": {
        "password_hash": bcrypt.hashpw(b"[REDACTED]", bcrypt.gensalt()),
        "role": "admin"
    }
}

def hash_password(password: str) -> bytes:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password: str, password_hash: bytes) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash)

def create_session(username: str) -> str:
    """Create a new session for a user"""
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "username": username,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + SESSION_DURATION
    }
    return session_id

def get_session(session_id: str):
    """Get session data if valid"""
    if session_id not in sessions:
        return None

    session_data = sessions[session_id]

    # Check expiration
    if datetime.now() > session_data["expires_at"]:
        del sessions[session_id]
        return None

    return session_data

def delete_session(session_id: str):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.cookies.get('session_id')

        if not session_id:
            return jsonify({'error': 'Not authenticated'}), 401

        session_data = get_session(session_id)
        if not session_data:
            return jsonify({'error': 'Session expired'}), 401

        # Add user info to request context
        request.user = session_data

        return f(*args, **kwargs)
    return decorated_function
```

##### 3. Add Authentication Routes

**File:** `server/api.py` (add these routes)
```python
from flask import make_response
from server.auth import (
    USERS, verify_password, create_session,
    get_session, delete_session, require_auth
)
from flask_limiter import Limiter

# Add rate limiting for auth endpoints
limiter = Limiter(
    key_func=lambda: request.remote_addr,
    default_limits=["200 per hour"]
)

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")  # Strict rate limit
def login():
    """Login endpoint"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    # Verify credentials
    user = USERS.get(username)
    if not user or not verify_password(password, user['password_hash']):
        # Use same error message to prevent username enumeration
        return jsonify({'error': 'Invalid credentials'}), 401

    # Create session
    session_id = create_session(username)

    # Create response with HTTP-only cookie
    response = make_response(jsonify({
        'message': 'Login successful',
        'username': username,
        'role': user['role']
    }))

    response.set_cookie(
        'session_id',
        session_id,
        httponly=True,      # Prevent JavaScript access
        secure=True,        # HTTPS only (disable in dev)
        samesite='Strict',  # CSRF protection
        max_age=86400       # 24 hours
    )

    return response

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user info"""
    return jsonify({
        'username': request.user['username'],
        'authenticated': True
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout endpoint"""
    session_id = request.cookies.get('session_id')
    if session_id:
        delete_session(session_id)

    response = make_response(jsonify({'message': 'Logged out'}))
    response.set_cookie('session_id', '', expires=0)
    return response

# Apply authentication to all API routes
@app.before_request
def check_auth():
    """Check authentication before all requests"""
    # Skip auth for login and health check
    if request.path in ['/api/auth/login', '/api/health']:
        return

    # Require auth for all other API routes
    if request.path.startswith('/api/'):
        session_id = request.cookies.get('session_id')
        if not session_id or not get_session(session_id):
            return jsonify({'error': 'Not authenticated'}), 401
```

##### 4. Update Frontend Login Component

**File:** `web/src/components/AuthGate.jsx` (replace PasswordGate)
```javascript
import React, { useState, useEffect } from 'react'
import '../styles/AuthGate.css'

function AuthGate({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      const response = await fetch('/api/auth/me', {
        credentials: 'include'  // Important: include cookies
      })

      if (response.ok) {
        const data = await response.json()
        setIsAuthenticated(true)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',  // Important: include cookies
        body: JSON.stringify({ username, password })
      })

      if (response.ok) {
        setIsAuthenticated(true)
        setUsername('')
        setPassword('')
      } else {
        const data = await response.json()
        setError(data.error || 'Login failed')
        setPassword('')
      }
    } catch (error) {
      setError('Network error. Please try again.')
    }
  }

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include'
      })
      setIsAuthenticated(false)
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  if (isLoading) {
    return <div className="auth-loading">Loading...</div>
  }

  if (!isAuthenticated) {
    return (
      <div className="auth-gate">
        <div className="auth-container">
          <div className="auth-card">
            <h1>✨ Imagineer</h1>
            <p className="subtitle">AI Image Generation Toolkit</p>

            <form onSubmit={handleSubmit} className="auth-form">
              <div className="form-group">
                <label htmlFor="username">Username</label>
                <input
                  type="text"
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Username"
                  autoFocus
                  autoComplete="username"
                />
              </div>

              <div className="form-group">
                <label htmlFor="password">Password</label>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  autoComplete="current-password"
                />
              </div>

              {error && <div className="error-message">{error}</div>}

              <button type="submit" className="submit-button">
                Login
              </button>
            </form>

            <p className="footer-text">
              Secure Authentication • Session expires in 24 hours
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="auth-status">
        <button onClick={handleLogout} className="logout-button">
          🚪 Logout
        </button>
      </div>
      {children}
    </>
  )
}

export default AuthGate
```

##### 5. Update API Calls to Include Credentials

**File:** `web/src/App.jsx` (update all fetch calls)
```javascript
// Add credentials: 'include' to all fetch calls
const fetchConfig = async () => {
  try {
    const response = await fetch('/api/config', {
      credentials: 'include'  // Include cookies
    })
    const data = await response.json()
    setConfig(data)
  } catch (error) {
    console.error('Failed to fetch config:', error)
  }
}

// Apply to all other API calls...
```

#### Testing Checklist
- [ ] Login with correct credentials succeeds
- [ ] Login with incorrect credentials fails
- [ ] Rate limiting works (5 attempts per minute)
- [ ] Session persists across page refreshes
- [ ] Session expires after 24 hours
- [ ] Logout clears session properly
- [ ] Authenticated requests work
- [ ] Unauthenticated requests are blocked
- [ ] Cookie is HTTP-only (check in DevTools)
- [ ] Cookie is Secure (in production with HTTPS)

---

## Phase 3: OAuth2 / OpenID Connect (Enterprise)

**Estimated Implementation Time:** 8-12 hours
**Complexity:** High
**Security Level:** ⭐⭐⭐⭐⭐ (Enterprise-grade)

### Overview
Integrate with external identity providers:
- **Google OAuth** - Free for personal Google accounts
- **GitHub OAuth** - Free for GitHub accounts
- **Auth0** - Paid service with free tier
- **Keycloak** - Self-hosted open-source solution

### Benefits
- ✅ No password management (delegated to provider)
- ✅ Multi-factor authentication (MFA) support
- ✅ Single Sign-On (SSO) across multiple apps
- ✅ User management UI
- ✅ Audit logs and analytics

### Implementation
Use libraries like:
- **Python:** `authlib` or `flask-oauthlib`
- **React:** `react-oauth2-code-pkce` or `react-google-login`

---

## Phase 4: JWT + Refresh Tokens (API-First)

**Estimated Implementation Time:** 6-8 hours
**Complexity:** Medium-High
**Security Level:** ⭐⭐⭐⭐⭐ (Stateless, scalable)

### Overview
Token-based authentication for distributed systems:
- **JWT access tokens** (short-lived, 15 minutes)
- **Refresh tokens** (long-lived, 7 days)
- **Stateless** - no server-side session store needed
- **Scalable** - works with load balancers

### Implementation
Use libraries like:
- **Python:** `PyJWT` or `python-jose`
- **React:** Store tokens in memory, not localStorage

---

## Comparison Matrix

| Feature | v1.0 Password Gate | v2.0 Session Auth | v3.0 OAuth | v4.0 JWT |
|---------|-------------------|-------------------|------------|----------|
| **Implementation Time** | 2 hours | 4 hours | 12 hours | 8 hours |
| **Security Level** | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Multiple Users** | ❌ | ✅ | ✅ | ✅ |
| **Rate Limiting** | ❌ | ✅ | ✅ | ✅ |
| **Audit Trail** | ❌ | ✅ | ✅ | ✅ |
| **MFA Support** | ❌ | ⚠️ Custom | ✅ | ⚠️ Custom |
| **Session Revocation** | ❌ | ✅ | ✅ | ⚠️ Blacklist |
| **Scalability** | ✅ | ⚠️ Sticky sessions | ✅ | ✅ |
| **Offline Mode** | ✅ | ❌ | ❌ | ⚠️ Limited |
| **Cost** | Free | Free | Free/Paid | Free |

---

## Migration Path

### From v1.0 → v2.0 (Recommended Next Step)

1. **Implement backend authentication** (3 hours)
   - Add `server/auth.py`
   - Add auth routes to `server/api.py`
   - Add rate limiting

2. **Update frontend** (1 hour)
   - Replace `PasswordGate` with `AuthGate`
   - Update all fetch calls to include credentials
   - Test login/logout flow

3. **Deploy** (30 minutes)
   - Update environment variables
   - Deploy backend first
   - Deploy frontend
   - Verify end-to-end

4. **Document** (30 minutes)
   - Update user documentation
   - Add admin guide for managing users

### From v2.0 → v3.0 (If Needed)

Only if you need:
- Multiple organizations
- SSO integration
- Third-party provider trust
- Compliance requirements

---

## Security Best Practices (All Versions)

1. **HTTPS Only** - Always use SSL/TLS in production
2. **Environment Variables** - Never hardcode secrets
3. **Rate Limiting** - Prevent brute force attacks
4. **Session Expiration** - Limit session lifetime
5. **Audit Logging** - Track authentication events
6. **Password Complexity** - Enforce strong passwords (v2.0+)
7. **MFA** - Enable two-factor authentication (v3.0+)
8. **Regular Updates** - Keep dependencies updated
9. **Security Headers** - Use CSP, HSTS, X-Frame-Options
10. **Monitoring** - Alert on suspicious activity

---

## Immediate Action Items

### For Current v1.0 Password Gate

✅ **Completed:**
- [x] Password gate component created
- [x] Environment variable configuration
- [x] 24-hour session expiration
- [x] Logout functionality
- [x] .gitignore updated

### Before Production Deployment

⚠️ **Required:**
- [ ] Change password from default
- [ ] Add HTTPS (required for secure cookies)
- [ ] Test on production environment
- [ ] Add basic monitoring/logging

### Optional Enhancements

🔧 **Nice to have:**
- [ ] Add "Remember Me" option (extend session)
- [ ] Add session timeout warning
- [ ] Add failed login attempt counter
- [ ] Add basic rate limiting on frontend

---

## Recommendation

**For Imagineer:**

1. **Now:** Continue with v1.0 password gate for initial Firebase deployment
2. **Next (1-2 weeks):** Upgrade to v2.0 session authentication
3. **Future (if needed):** Consider v3.0 OAuth if you need to share access with others

The v2.0 session authentication provides excellent security for a personal/small team project while remaining simple to implement and maintain.

---

## Resources

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [Flask-Login Documentation](https://flask-login.readthedocs.io/)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [OAuth 2.0 Simplified](https://www.oauth.com/)

---

**Document Version:** 1.0
**Author:** Claude Code
**Last Review:** 2025-10-14
