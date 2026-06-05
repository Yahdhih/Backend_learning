# Module 07 — Auth & Sessions

> Authentication proves who you are. Authorization proves what you're allowed to do. Confusing these causes security bugs.

---

## Learning Objectives

- Understand the difference between Authentication and Authorization
- Implement session-based authentication (Django default)
- Understand JWT — what it is, how it works, trade-offs
- Implement token authentication with DRF
- Build permission classes
- Handle password hashing correctly

---

## 1. Authentication vs Authorization

```
Authentication: "Who are you?"
  → Login with username/password
  → The server says: "You are user #5, Alice"

Authorization: "What can you do?"
  → Alice can edit her own posts
  → Alice cannot edit Bob's posts
  → Admin can delete any post
```

---

## 2. Session-Based Authentication

```
Login:
  POST /login {username, password}
    → Django checks credentials
    → Creates a session in DB: {id: "abc123", user_id: 5, expires: ...}
    → Sets cookie: Set-Cookie: sessionid=abc123; HttpOnly; Secure

Subsequent requests:
  GET /profile
    Cookie: sessionid=abc123
    → Django looks up session "abc123" in DB
    → Finds user_id=5
    → Sets request.user = User.objects.get(id=5)

Logout:
  POST /logout
    → Deletes the session from DB
    → Cookie becomes invalid
```

**Trade-off:** Sessions require DB lookup on every request. With Redis as session store, this is fast.

---

## 3. JWT (JSON Web Token)

JWT is a self-contained token — the server doesn't need to look it up.

```
Structure: header.payload.signature

header:    base64({"alg": "HS256", "typ": "JWT"})
payload:   base64({"user_id": 5, "exp": 1748000000, "iat": 1747996400})
signature: HMAC_SHA256(header + "." + payload, SECRET_KEY)
```

Verification:
1. Decode header and payload (anyone can do this — they're just base64)
2. Recompute the signature using SECRET_KEY
3. If signatures match → token is valid (not tampered with)
4. Check `exp` (expiration) — is it in the past?

**No DB lookup needed.** The token is self-validating.

```
Login:
  POST /login {username, password}
    → Check credentials
    → Return: {"access": "eyJ...", "refresh": "eyJ..."}

Subsequent requests:
  GET /profile
    Authorization: Bearer eyJ...
    → Decode token, verify signature, check expiry
    → No DB lookup!

Token refresh:
  POST /token/refresh {refresh: "eyJ..."}
    → Verify refresh token (longer-lived)
    → Return new access token (short-lived)
```

**Trade-offs:**
| | Sessions | JWT |
|--|---------|-----|
| Revocation | Easy (delete from DB) | Hard (need a blacklist) |
| Server state | Stateful (DB) | Stateless |
| Horizontal scaling | Requires shared session store (Redis) | Simple (just verify signature) |
| Payload size | Small cookie | Larger header |
| Best for | Traditional web apps | APIs, microservices, mobile |

---

## 4. Permissions in DRF

```python
from rest_framework import permissions

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission: only the author can edit/delete.
    Anyone can read.
    """
    def has_permission(self, request, view):
        # Allow all read requests
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write requests require authentication
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions: allow for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions: only the author
        return obj.author == request.user


# Use in ViewSet
class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthorOrReadOnly]
```

**Built-in permissions:**
- `AllowAny` — everyone
- `IsAuthenticated` — must be logged in
- `IsAdminUser` — must be `is_staff=True`
- `IsAuthenticatedOrReadOnly` — logged in for writes, anyone for reads

---

## 5. Password Hashing

Django uses PBKDF2 by default. **Never store plain-text passwords.**

```python
from django.contrib.auth.hashers import make_password, check_password

# Django does this automatically when you use User.objects.create_user()
hashed = make_password("my_password")
# pbkdf2_sha256$600000$salt$hash

check_password("my_password", hashed)   # True
check_password("wrong", hashed)         # False

# The hash includes the algorithm, iterations, salt, and hash value
# This means you can upgrade hashing algorithms later
```

---

## Exercises

1. [Exercise 01 — Session Auth from Scratch](exercises/01_session_auth.md)
2. [Exercise 02 — JWT Implementation](exercises/02_jwt_auth.md)
3. [Exercise 03 — Custom Permissions](exercises/03_permissions.md)

---

## Next → [Module 08: Security](../08_security/README.md)
