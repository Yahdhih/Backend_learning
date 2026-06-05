# Module 03 — WSGI: Before Django Exists

> Django is just a Python function. WSGI defines what that function looks like. Understanding this makes everything about Django's request/response cycle obvious.

---

## Learning Objectives

- Understand what WSGI is and why it exists
- Write a WSGI application by hand
- Implement URL routing, middleware, and error handling from scratch
- Understand why `runserver` isn't production-ready
- Know how Gunicorn and Django relate

---

## 1. The Problem WSGI Solves

Before WSGI (PEP 3333), every Python web framework (Django, Flask, etc.) had to write its own server. And every server had to be rewritten for each framework. 

WSGI standardizes the interface:

```
                  The WSGI Contract
                  ─────────────────
HTTP Request      WSGI Server          WSGI App
(raw bytes)  →   (Gunicorn, uWSGI) → (Django, Flask)
                  │                    │
                  │  calls app with:   │
                  │   - environ dict   │
                  │   - start_response │
                  │                    │
                  │◄── returns body ───│
                  │
HTTP Response ←───│
(raw bytes)
```

The contract:
- **WSGI Server** (Gunicorn): handles raw TCP, parses HTTP, calls your app
- **WSGI App** (Django): a Python callable that receives two arguments and returns a response

---

## 2. The WSGI Interface

A WSGI application is exactly this:

```python
def application(environ: dict, start_response: callable) -> iterable:
    ...
```

- `environ`: a dict containing everything about the request (method, path, headers, body, etc.)
- `start_response`: a callable you must call to send back the status and headers
- Return value: an iterable of bytes (the body)

The simplest possible WSGI app:

```python
def application(environ, start_response):
    status = "200 OK"
    headers = [("Content-Type", "text/plain")]
    start_response(status, headers)
    return [b"Hello, World!"]
```

That's it. Django is a very sophisticated version of this function.

---

## 3. The `environ` Dict

`environ` contains everything Gunicorn parsed from the HTTP request:

```python
{
    # Request basics
    "REQUEST_METHOD": "GET",
    "PATH_INFO": "/users",
    "QUERY_STRING": "page=2&limit=10",
    "HTTP_VERSION": "HTTP/1.1",

    # Headers (prefixed with HTTP_)
    "HTTP_HOST": "localhost:8000",
    "HTTP_ACCEPT": "application/json",
    "HTTP_AUTHORIZATION": "Bearer token123",
    "CONTENT_TYPE": "application/json",   # no HTTP_ prefix for these two
    "CONTENT_LENGTH": "47",               # no HTTP_ prefix

    # Body
    "wsgi.input": <socket-like object>,   # read() to get body bytes

    # Server info
    "SERVER_NAME": "localhost",
    "SERVER_PORT": "8000",
    "wsgi.url_scheme": "http",

    # WSGI metadata
    "wsgi.version": (1, 0),
    "wsgi.errors": <stderr-like object>,
    "wsgi.multithread": True,
    "wsgi.multiprocess": False,
}
```

**Notice:** Django's `request.method` is just `environ["REQUEST_METHOD"]`. `request.GET` is `environ["QUERY_STRING"]` parsed. The magic is just Python dict access.

---

## 4. Middleware in WSGI

Middleware wraps a WSGI app. It's a callable that returns a callable:

```python
class LoggingMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        method = environ["REQUEST_METHOD"]
        path = environ["PATH_INFO"]
        print(f"→ {method} {path}")

        response = self.app(environ, start_response)

        print(f"← done")
        return response

# Wrap your app
app = MyApp()
app = LoggingMiddleware(app)

# The WSGI server calls app(environ, start_response)
# which goes through LoggingMiddleware first, then MyApp
```

Django's middleware works exactly this way — each middleware wraps the next.

---

## 5. The Django Request Lifecycle (Full Picture)

```
HTTP Request arrives
       │
       ▼
┌─────────────────┐
│    Gunicorn      │  1. Parse HTTP bytes into environ dict
│    (WSGI server) │  2. Call django.core.handlers.wsgi.WSGIHandler(environ, start_response)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SecurityMiddleware    │
│  SessionMiddleware     │  Django middleware stack (each wraps the next)
│  CommonMiddleware      │  Request goes DOWN through all middleware
│  CsrfViewMiddleware    │
│  AuthenticationMiddleware│
│  MessageMiddleware     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   URL Resolver   │  Match PATH_INFO against urlpatterns
│   (urls.py)      │  Find the view function to call
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   View Function  │  Your code runs here
│   (views.py)     │  Returns an HttpResponse object
└────────┬────────┘
         │
         ▼  (response goes BACK UP through middleware)
┌─────────────────┐
│  Middleware Stack│  Each middleware can modify the response
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Gunicorn      │  Convert HttpResponse to raw HTTP bytes
└────────┬────────┘
         │
         ▼
HTTP Response sent
```

---

## 6. Why Not `runserver` in Production?

Django's development server (`manage.py runserver`):
- Single-threaded (one request at a time)
- No process management (one crash = server down)
- No connection pooling
- Not optimized for performance
- Not tested under production load

Gunicorn:
- Multiple worker processes (parallel requests)
- Process management (auto-restarts crashed workers)
- Tuned for production load
- Nginx handles SSL, static files, and proxies to Gunicorn

---

## Exercises

1. [Exercise 01 — Minimal WSGI App](exercises/01_minimal_wsgi.py)
2. [Exercise 02 — Router From Scratch](exercises/02_wsgi_router.py)

---

## Next → [Module 04: Django Fundamentals](../04_django_fundamentals/README.md)
