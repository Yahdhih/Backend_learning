# Module 08 — Security

> One security mistake can leak your users' data, bring down your app, or get you sued. Learn the common attacks and how Django protects against them.

---

## Learning Objectives

- Understand and exploit (in a lab) CSRF, XSS, and SQL injection
- Know Django's built-in security features
- Know how to harden a Django deployment
- Understand rate limiting and brute force protection

---

## 1. CSRF — Cross-Site Request Forgery

**The attack:**
```
1. User logs into yourbank.com
   → Browser has a valid session cookie

2. User visits evil.com while still logged in

3. evil.com's page contains:
   <form action="https://yourbank.com/transfer" method="POST">
     <input name="amount" value="1000">
     <input name="to" value="attacker">
   </form>
   <script>document.forms[0].submit()</script>

4. Browser automatically sends the bank's session cookie with the POST!
   → Transfer executes as the logged-in user
```

**Django's protection:**
```python
# Django includes CsrfViewMiddleware by default
# It requires a CSRF token in every POST/PUT/DELETE request

# HTML forms: {% csrf_token %} adds a hidden input
# AJAX: send the token in X-CSRFToken header
# APIs: use JWT or token auth instead of cookies (no CSRF risk)
```

**Why JWT doesn't have CSRF:** JWT is sent in the `Authorization` header, which JavaScript must explicitly set. Browsers don't auto-add custom headers to cross-origin requests.

---

## 2. SQL Injection

**The attack:**
```python
# NEVER do this:
username = request.GET["username"]
query = f"SELECT * FROM users WHERE username = '{username}'"
# If username = "' OR '1'='1", query becomes:
# SELECT * FROM users WHERE username = '' OR '1'='1'
# → Returns ALL users!

# Worse:
# username = "'; DROP TABLE users; --"
```

**Django's protection:** The ORM always uses parameterized queries:
```python
# Safe — Django passes username as a parameter, not string interpolation
User.objects.filter(username=username)
# Generates: SELECT * FROM users WHERE username = %s  with params=["alice"]

# If you use raw SQL, ALWAYS use parameterized queries:
User.objects.raw("SELECT * FROM users WHERE username = %s", [username])
# NEVER: User.objects.raw(f"... WHERE username = '{username}'")
```

---

## 3. XSS — Cross-Site Scripting

**The attack:**
```
User submits: <script>document.cookie</script> as their username

App stores it in DB and renders it in HTML without escaping:
<p>Welcome, <script>document.cookie</script></p>

→ Script executes in every visitor's browser
→ Attacker can steal cookies, redirect users, etc.
```

**Django's protection:**
- Django templates auto-escape HTML by default
- For APIs returning JSON, XSS is not an issue (JSON is not rendered as HTML)
- Never use `mark_safe()` with user-provided content

---

## 4. Django Security Checklist

```python
# settings.py — production security settings

DEBUG = False  # NEVER True in production — exposes stack traces

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # from env, never hardcoded

ALLOWED_HOSTS = ["api.example.com"]           # only your actual domain

# HTTPS settings
SECURE_SSL_REDIRECT = True                    # redirect HTTP → HTTPS
SECURE_HSTS_SECONDS = 31536000               # tell browsers: HTTPS only for 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = True                  # only send session cookie over HTTPS
CSRF_COOKIE_SECURE = True

# Clickjacking protection
X_FRAME_OPTIONS = "DENY"

# Content type sniffing
SECURE_CONTENT_TYPE_NOSNIFF = True
```

---

## 5. Rate Limiting

Without rate limiting:
- Brute-force password attacks (try millions of passwords)
- Scraping your entire database
- DDoS via expensive endpoints

```python
# django-ratelimit
from django_ratelimit.decorators import ratelimit

@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def login(request):
    ...

# DRF throttling
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
    }
}
```

---

## Exercises

1. [Exercise 01 — SQL Injection Lab](exercises/01_sql_injection_lab.md)
2. [Exercise 02 — CSRF Simulation](exercises/02_csrf_simulation.md)
3. [Exercise 03 — Django Security Audit](exercises/03_security_audit.md)

---

## Next → [Module 09: Caching & Performance](../09_caching_and_performance/README.md)
