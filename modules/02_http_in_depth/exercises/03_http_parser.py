"""
Exercise 03 — Build an HTTP Parser

Parse raw HTTP messages from bytes into structured Python objects.
This is what every web framework does as the very first step.

Run with: python3 03_http_parser.py
"""

from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import unquote_plus


@dataclass
class HttpRequest:
    method: str
    path: str
    query_params: dict
    http_version: str
    headers: dict
    body: bytes
    raw: bytes


@dataclass
class HttpResponse:
    status_code: int
    status_text: str
    headers: dict
    body: str


# ─── IMPLEMENT THESE ─────────────────────────────────────────────────────────

def parse_request(raw: bytes) -> HttpRequest:
    """
    Parse raw HTTP request bytes into an HttpRequest object.

    A raw request looks like:
        b"POST /users?active=true HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: 27\r\n\r\n{\"name\":\"Alice\",\"age\":30}"

    Steps:
    1. Split on \r\n\r\n to separate headers from body
    2. Split header section on \r\n to get individual lines
    3. First line is the request line: parse method, path, version
    4. Path may contain "?query=string" — split those out
    5. Parse query string: "a=1&b=2" → {"a": "1", "b": "2"}
    6. Remaining lines are headers: "Key: Value" → {"key": "value"}
       Note: header names should be lowercased for consistency
    7. Body is everything after the blank line

    Hints:
    - raw.split(b"\r\n\r\n", 1) splits at the first blank line
    - b"GET /path HTTP/1.1".decode() converts bytes to string
    - "Key: Value".split(": ", 1) splits on the FIRST ": " only
    """
    # YOUR CODE HERE
    pass


def parse_response(raw: bytes) -> HttpResponse:
    """
    Parse raw HTTP response bytes into an HttpResponse object.

    A raw response looks like:
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"ok\"}"

    Steps:
    1. Split headers from body on \r\n\r\n
    2. First line: "HTTP/1.1 200 OK" → parse version, code, text
    3. Parse remaining header lines
    4. Body is the rest

    Note: status code should be an int.
    """
    # YOUR CODE HERE
    pass


def build_response(status_code: int, body: str, content_type: str = "application/json") -> bytes:
    """
    Build a raw HTTP response.

    The output should look like:
        HTTP/1.1 {code} {text}\r\n
        Content-Type: {content_type}; charset=utf-8\r\n
        Content-Length: {len(body.encode())}\r\n
        \r\n
        {body}

    Status text lookup:
        200 → OK
        201 → Created
        204 → No Content
        400 → Bad Request
        401 → Unauthorized
        403 → Forbidden
        404 → Not Found
        405 → Method Not Allowed
        500 → Internal Server Error
    """
    STATUS_TEXTS = {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        500: "Internal Server Error",
    }
    # YOUR CODE HERE
    pass


# ─── TESTS ───────────────────────────────────────────────────────────────────

def run_tests():
    passed = 0
    failed = 0

    def check(name, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name}")
            print(f"    Expected: {expected!r}")
            print(f"    Got:      {actual!r}")
            failed += 1

    print("\n─── parse_request ───")

    raw1 = b"GET /users HTTP/1.1\r\nHost: localhost\r\nAccept: application/json\r\n\r\n"
    req = parse_request(raw1)
    check("method GET", req.method, "GET")
    check("path /users", req.path, "/users")
    check("version", req.http_version, "HTTP/1.1")
    check("host header", req.headers.get("host"), "localhost")
    check("accept header", req.headers.get("accept"), "application/json")
    check("empty query params", req.query_params, {})
    check("empty body", req.body, b"")

    raw2 = b"POST /search?q=python&page=2 HTTP/1.1\r\nContent-Type: application/json\r\n\r\n{\"filter\":\"active\"}"
    req2 = parse_request(raw2)
    check("method POST", req2.method, "POST")
    check("path no query", req2.path, "/search")
    check("query param q", req2.query_params.get("q"), "python")
    check("query param page", req2.query_params.get("page"), "2")
    check("body bytes", req2.body, b'{"filter":"active"}')

    raw3 = b"DELETE /users/42 HTTP/1.1\r\nAuthorization: Bearer token123\r\n\r\n"
    req3 = parse_request(raw3)
    check("method DELETE", req3.method, "DELETE")
    check("path with id", req3.path, "/users/42")
    check("auth header lowercase", req3.headers.get("authorization"), "Bearer token123")

    print("\n─── parse_response ───")

    raw_resp = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 15\r\n\r\n{\"status\":\"ok\"}"
    resp = parse_response(raw_resp)
    check("status code int", resp.status_code, 200)
    check("status text", resp.status_text, "OK")
    check("content-type header", resp.headers.get("content-type"), "application/json")
    check("body", resp.body, '{"status":"ok"}')

    raw_404 = b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot found"
    resp404 = parse_response(raw_404)
    check("404 status code", resp404.status_code, 404)
    check("404 status text", resp404.status_text, "Not Found")

    print("\n─── build_response ───")

    r = build_response(200, '{"ok": true}')
    check("build 200 starts correctly", r.startswith(b"HTTP/1.1 200 OK"), True)
    check("build contains body", b'{"ok": true}' in r, True)
    check("build contains content-type", b"Content-Type: application/json" in r, True)
    check("build contains content-length", b"Content-Length: 12" in r, True)
    check("build has blank line separator", b"\r\n\r\n" in r, True)

    r404 = build_response(404, "not here", "text/plain")
    check("build 404 status", r404.startswith(b"HTTP/1.1 404 Not Found"), True)

    print(f"\nResults: {passed} passed, {failed} failed")

    print("\n─── BONUS: Round-trip test ───")
    print("Building a response, then parsing it back:")
    original_body = '{"users": [{"id": 1, "name": "Alice"}]}'
    raw_built = build_response(200, original_body)
    if raw_built:
        parsed = parse_response(raw_built)
        if parsed:
            check("round-trip status code", parsed.status_code, 200)
            check("round-trip body", parsed.body, original_body)
        else:
            print("  (skipped — build_response or parse_response not implemented)")
    else:
        print("  (skipped — build_response not implemented)")


if __name__ == "__main__":
    run_tests()
