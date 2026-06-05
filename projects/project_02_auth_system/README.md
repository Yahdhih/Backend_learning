# Project 02 — Auth System

**Prerequisites:** Complete Modules 07–08

**Time estimate:** 3–4 hours

Build a complete authentication and authorization system.

---

## Features

- Registration with email verification
- JWT auth (access + refresh tokens)
- Password reset via email
- Role-based access control (user/moderator/admin)
- Rate limiting on auth endpoints
- Account lockout after failed attempts

---

## Endpoints

```
POST /auth/register/
POST /auth/verify-email/{token}/
POST /auth/login/
POST /auth/logout/
POST /auth/token/refresh/
POST /auth/password-reset/
POST /auth/password-reset/confirm/{token}/
GET  /auth/me/
PATCH /auth/me/

# Admin only:
GET  /admin/users/
PATCH /admin/users/{id}/role/
POST /admin/users/{id}/ban/
```

---

## Key Challenges

1. Email verification: generate a signed token, send email (use `EMAIL_BACKEND = console` for dev), verify on click
2. Password reset: same pattern — signed time-limited token
3. JWT blacklisting on logout: when user logs out, add refresh token to a blacklist (store in Redis with TTL matching token expiry)
4. Role-based permissions: custom permission classes that check `user.role`
5. Account lockout: after 5 failed logins, lock for 15 minutes (use Redis to count attempts)

---

## Acceptance Criteria

- [ ] Can register → verify email → login → access protected routes
- [ ] Can request password reset → receive link → set new password
- [ ] Logout invalidates the token
- [ ] 5 failed logins locks the account
- [ ] Rate limit on /login: 5 attempts per minute per IP
- [ ] Admins can change roles, moderators cannot
