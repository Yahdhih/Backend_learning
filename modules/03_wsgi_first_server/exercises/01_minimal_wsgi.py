"""
Exercise 01 — Minimal WSGI App

Build a working WSGI application using Python's built-in wsgiref server.
This runs a REAL server using the WSGI standard.

HOW TO RUN:
    python3 01_minimal_wsgi.py

Then visit:
    http://localhost:8001/
    http://localhost:8001/hello
    http://localhost:8001/json
    http://localhost:8001/error

Or use curl:
    curl -v http://localhost:8001/

IMPORTANT: This file uses Python's built-in wsgiref.simple_server — the same
WSGI interface that Gunicorn uses. Your app function works unchanged with
either server. That's the point of WSGI.
"""

import json
from wsgiref.simple_server import make_server
from io import BytesIO


# ─── PART 1: Understand the environ ──────────────────────────────────────────

def debug_app(environ, start_response):
    """
    Dump the entire environ dict as JSON.
    This is the raw data EVERY WSGI app receives.
    Visit http://localhost:8001/ to see it.
    """
    # Some values in environ aren't JSON-serializable (file objects, etc.)
    # So we filter to only serializable values
    safe_environ = {}
    for key, value in environ.items():
        if isinstance(value, (str, int, float, bool, list, dict, type(None))):
            safe_environ[key] = value
        else:
            safe_environ[key] = f"<{type(value).__name__}>"

    body = json.dumps(safe_environ, indent=2).encode("utf-8")

    start_response("200 OK", [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


# ─── PART 2: Build a real routing WSGI app ───────────────────────────────────
#
# Complete the functions below, then plug them into the router.

def handle_home(environ) -> tuple[int, str, str]:
    """
    Returns: (status_code, content_type, body_string)
    Return an HTML page with a welcome message.
    """
    # YOUR CODE HERE
    pass


def handle_hello(environ) -> tuple[int, str, str]:
    """
    Returns: (status_code, content_type, body_string)
    Read the query string "name" param.
    If ?name=Alice: return JSON {"message": "Hello, Alice!"}
    If no name: return JSON {"message": "Hello, stranger!"}

    Hint: environ["QUERY_STRING"] might be "name=Alice"
    Parse it: dict(pair.split("=") for pair in qs.split("&") if "=" in pair)
    """
    # YOUR CODE HERE
    pass


def handle_method_demo(environ) -> tuple[int, str, str]:
    """
    Returns: (status_code, content_type, body_string)
    Show what HTTP method was used and echo any body back.

    GET:  return {"method": "GET", "message": "This was a GET request"}
    POST: read the body from environ["wsgi.input"], return {"method": "POST", "body": "..."}
    Other: return 405 with {"error": "Method not allowed"}

    Reading body from WSGI:
        content_length = int(environ.get("CONTENT_LENGTH") or 0)
        body = environ["wsgi.input"].read(content_length)
        body_str = body.decode("utf-8")
    """
    # YOUR CODE HERE
    pass


# ─── PART 3: Build the router + middleware ───────────────────────────────────

def router(environ, start_response):
    """
    Route requests to the right handler based on PATH_INFO.

    Routes:
        /         → debug_app (show environ)
        /hello    → handle_hello
        /methods  → handle_method_demo
        anything else → 404

    Each handler returns (status_code, content_type, body_string).
    This function should call start_response and return the body.
    """
    path = environ.get("PATH_INFO", "/")

    handlers = {
        "/": debug_app,
        "/hello": handle_hello,
        "/methods": handle_method_demo,
    }

    # YOUR CODE HERE - route and respond
    pass


class LoggingMiddleware:
    """
    Wrap any WSGI app and log each request/response.
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "?")
        path = environ.get("PATH_INFO", "/")

        # We need to capture the status code from start_response
        # to log it — intercept start_response with our own wrapper

        captured = {}

        def capturing_start_response(status, headers, exc_info=None):
            captured["status"] = status
            return start_response(status, headers, exc_info)

        result = self.app(environ, capturing_start_response)
        status = captured.get("status", "???")
        print(f"  {method} {path} → {status}")
        return result


class CORSMiddleware:
    """
    Add CORS headers to all responses.
    Complete the __call__ method.

    For every response, add:
        Access-Control-Allow-Origin: *
        Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
        Access-Control-Allow-Headers: Content-Type, Authorization

    For OPTIONS requests (preflight), return 200 immediately with just the CORS headers.
    """

    def __init__(self, app, allowed_origin="*"):
        self.app = app
        self.allowed_origin = allowed_origin

    def __call__(self, environ, start_response):
        # YOUR CODE HERE
        pass


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def build_app():
    """Build the full app with middleware stack."""
    app = router
    app = LoggingMiddleware(app)
    app = CORSMiddleware(app)
    return app


if __name__ == "__main__":
    app = build_app()

    print("WSGI server running at http://localhost:8001")
    print("\nTry these:")
    print("  curl -v http://localhost:8001/           (debug: full environ)")
    print("  curl -v http://localhost:8001/hello      (handler)")
    print("  curl -v 'http://localhost:8001/hello?name=Alice'")
    print("  curl -v -X POST -d 'test' http://localhost:8001/methods")
    print("  curl -v -X OPTIONS http://localhost:8001/hello  (CORS preflight)")
    print("\nPress Ctrl+C to stop.\n")

    with make_server("", 8001, app) as httpd:
        httpd.serve_forever()
