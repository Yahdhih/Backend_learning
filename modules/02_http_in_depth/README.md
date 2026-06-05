# Module 02 — HTTP In Depth

> HTTP is the language of the web. Django speaks it for you — but you need to understand it to debug issues, design good APIs, and know what Django is doing.

---

## Learning Objectives

- Know all HTTP methods and when to use each
- Read and write the most important headers
- Understand every status code category
- Understand cookies and sessions
- Understand CORS and why browsers enforce it
- Understand HTTPS at a conceptual level

---

## 1. HTTP Methods — Not Just GET and POST

Each method has a **semantic meaning**. Using the right one matters for caching, browser behavior, and API design.

| Method | Meaning | Has Body? | Safe? | Idempotent? |
|--------|---------|-----------|-------|-------------|
| GET | Read a resource | No | Yes | Yes |
| POST | Create / submit | Yes | No | No |
| PUT | Replace entirely | Yes | No | Yes |
| PATCH | Partial update | Yes | No | No* |
| DELETE | Remove | No | No | Yes |
| HEAD | Like GET, headers only | No | Yes | Yes |
| OPTIONS | What methods are allowed? | No | Yes | Yes |

**Safe** = doesn't change server state. Browsers can safely retry safe requests.
**Idempotent** = calling it N times has same effect as calling it once. PUT to replace a user is idempotent — calling it 10 times leaves you in the same state.

```
GET /users/1       → returns user #1 (no change)
POST /users        → creates a new user (different result each call)
PUT /users/1       → replaces user #1 entirely
PATCH /users/1     → changes only specified fields of user #1
DELETE /users/1    → removes user #1 (2nd call: 404, but state is same: no user #1)
```

---

## 2. Status Codes

Status codes are grouped by their first digit:

```
1xx — Informational (rare in practice)
      100 Continue
      101 Switching Protocols (WebSockets use this)

2xx — Success
      200 OK             — standard success
      201 Created        — resource was created (use for POST)
      204 No Content     — success but no body (use for DELETE)

3xx — Redirection
      301 Moved Permanently   — change bookmarks, cached by browser
      302 Found               — temporary redirect
      304 Not Modified        — cached version is still fresh

4xx — Client Error (YOU did something wrong)
      400 Bad Request         — malformed request / validation failed
      401 Unauthorized        — not authenticated (misleadingly named)
      403 Forbidden           — authenticated but not authorized
      404 Not Found           — resource doesn't exist
      405 Method Not Allowed  — tried DELETE on a read-only endpoint
      409 Conflict            — e.g. duplicate email on registration
      422 Unprocessable       — valid JSON but semantically wrong
      429 Too Many Requests   — rate limited

5xx — Server Error (WE did something wrong)
      500 Internal Server Error — unhandled exception
      502 Bad Gateway           — upstream service failed
      503 Service Unavailable   — server overloaded or in maintenance
      504 Gateway Timeout       — upstream took too long
```

**Common mistake:** Using 200 for everything and putting the error in the body. Don't do this. HTTP status codes exist precisely to communicate success/failure.

---

## 3. Request Headers (the most important ones)

```
GET /api/users HTTP/1.1
Host: api.example.com              ← REQUIRED in HTTP/1.1. Which server to reach.
Accept: application/json           ← What format the client wants back
Accept-Language: en-US,en;q=0.9   ← Preferred language
Accept-Encoding: gzip, deflate, br ← Client can decompress these
Authorization: Bearer eyJhbGci...  ← Token or credentials
Content-Type: application/json     ← Format of the REQUEST body (for POST/PUT)
Content-Length: 47                 ← Length of the request body in bytes
User-Agent: Mozilla/5.0 ...        ← What sent the request
Cookie: session=abc123; pref=dark  ← Cookies being sent back to server
Cache-Control: no-cache            ← Don't use cached response
If-None-Match: "abc123"            ← Conditional: only respond if content changed
X-Request-ID: uuid-here            ← Custom header for tracing (X- prefix = custom)
```

---

## 4. Response Headers (the most important ones)

```
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8   ← Format of the RESPONSE body
Content-Length: 245                              ← How many bytes in body
Cache-Control: max-age=3600, public             ← How long to cache this
ETag: "abc123"                                  ← Fingerprint of content (for caching)
Last-Modified: Thu, 05 Jun 2026 10:00:00 GMT   ← When it was last changed
Set-Cookie: session=xyz; HttpOnly; Secure       ← Tell browser to store a cookie
Location: /api/users/42                         ← Where to find new/moved resource
WWW-Authenticate: Bearer realm="api"            ← How to authenticate
Allow: GET, POST, OPTIONS                       ← For 405 — what methods work here
Access-Control-Allow-Origin: https://app.com   ← CORS: who can access this
Vary: Accept, Accept-Encoding                   ← Caching hint: this varies by header
X-RateLimit-Remaining: 98                       ← Custom: rate limit info
```

---

## 5. Cookies and Sessions

HTTP is stateless. Cookies are how we fake statefulness.

**How session auth works:**

```
Browser                                          Server
  │                                                │
  │── POST /login {username, password} ───────────►│
  │                                                │  1. Check credentials
  │                                                │  2. Create session in DB/Redis
  │                                                │     {session_id: "abc123", user_id: 5}
  │◄── 200 OK ──────────────────────────────────── │
  │    Set-Cookie: sessionid=abc123; HttpOnly      │
  │                                                │
  │  [Browser stores the cookie]                   │
  │                                                │
  │── GET /profile ────────────────────────────── ►│
  │   Cookie: sessionid=abc123                     │  3. Look up session "abc123"
  │                                                │  4. Find user_id=5
  │◄── 200 OK {user data} ──────────────────────── │
```

**Cookie security flags:**
- `HttpOnly` — JavaScript cannot read this cookie (prevents XSS theft)
- `Secure` — only sent over HTTPS
- `SameSite=Strict` — only sent to same site (prevents CSRF)
- `Max-Age=3600` — expires in 3600 seconds

---

## 6. CORS — Cross-Origin Resource Sharing

Your browser blocks JavaScript from reading responses from a different origin **by default**. CORS is how a server tells the browser "it's OK, allow this."

**What is an "origin"?**
```
https://app.example.com:443/page

protocol  ───── https
domain    ───── app.example.com
port      ───── 443

Two URLs have the same origin ONLY if all three match.
```

**The CORS flow:**

```
Browser (app.com)                          API (api.com)
    │                                           │
    │  Preflight: OPTIONS /data                 │
    │  Origin: https://app.com                  │
    │  Access-Control-Request-Method: POST ─────►│
    │                                           │  Server decides whether to allow
    │◄── 200 OK ────────────────────────────────│
    │    Access-Control-Allow-Origin: https://app.com
    │    Access-Control-Allow-Methods: GET, POST
    │    Access-Control-Max-Age: 86400
    │                                           │
    │  Actual request: POST /data ──────────────►│
    │◄── 200 OK {data} ─────────────────────────│
```

The **preflight** is an automatic OPTIONS request the browser sends before any cross-origin request that could modify data. The server must respond with the correct CORS headers or the browser blocks it.

In Django you use `django-cors-headers` to handle this.

---

## 7. HTTPS / TLS

HTTPS = HTTP over TLS (Transport Layer Security). TLS does two things:
1. **Encrypts** the connection — nobody in the middle can read it
2. **Verifies identity** — the server proves it's who it says it is (via certificate)

```
Without HTTPS (HTTP):
  You → [GET /login] → Router → [GET /login] → Server
        ← [password=abc123] ←  Router  ← [password=abc123] ←
  Anyone on the network can read this!

With HTTPS:
  You → [encrypted gibberish] → Router → [encrypted gibberish] → Server
       ← [encrypted gibberish] ← Router ← [encrypted gibberish] ←
  Router sees only encrypted bytes. Only you and the server can decrypt.
```

A TLS certificate proves the server owns the domain. Your browser has a list of trusted Certificate Authorities (CAs) — if the server's cert is signed by a trusted CA, the browser trusts it.

Let's Encrypt gives free TLS certificates. In production Django deployments, Nginx handles TLS termination so your Django code still speaks plain HTTP internally.

---

## 8. HTTP Versions

| Version | Year | Key feature |
|---------|------|-------------|
| HTTP/1.0 | 1996 | One request per TCP connection |
| HTTP/1.1 | 1997 | Keep-alive (reuse connections), pipelining |
| HTTP/2 | 2015 | Multiplexing (many requests on one connection), header compression, server push |
| HTTP/3 | 2022 | Built on QUIC (UDP-based), faster connection setup |

You don't need to deeply understand HTTP/2+ to build Django apps — Nginx handles this. But know they exist.

---

## Key Concepts to Commit to Memory

| Concept | One-liner |
|---------|-----------|
| Idempotent | Calling N times = same result as calling once |
| Safe | Doesn't change server state |
| Cookie | Small data the browser stores and sends back automatically |
| Session | Server-side data keyed by a session ID stored in a cookie |
| CORS | Browser policy that blocks cross-origin requests unless server allows them |
| HTTPS/TLS | HTTP with encryption + identity verification |
| Content-Type | Tells the receiver how to parse the body |
| ETag | A fingerprint for caching — "only send if content changed" |

---

## What Just Happened?

Answer this before doing exercises:

> "Why does a browser send an OPTIONS request before a POST to a different origin? What does the server need to include in the OPTIONS response for the POST to succeed?"

---

## Exercises

1. [Exercise 01 — HTTP Methods Lab](exercises/01_http_methods_lab.md)
2. [Exercise 02 — Headers Deep Dive](exercises/02_headers_deep_dive.md)
3. [Exercise 03 — Build an HTTP Parser](exercises/03_http_parser.py)

---

## Next → [Module 03: WSGI — Before Django Exists](../03_wsgi_first_server/README.md)
