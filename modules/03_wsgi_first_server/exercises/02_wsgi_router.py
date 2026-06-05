"""
Exercise 02 — Router From Scratch

Build a URL router that mimics Django's URL dispatcher.
This is the core of what Django's urls.py does.

Run the app:
    python3 02_wsgi_router.py

Then test:
    curl http://localhost:8002/
    curl http://localhost:8002/users
    curl http://localhost:8002/users/42
    curl http://localhost:8002/users/42/posts
    curl -X POST -H "Content-Type: application/json" \
         -d '{"name":"Alice"}' http://localhost:8002/users
"""

import json
import re
from wsgiref.simple_server import make_server


# ─── The Router class ────────────────────────────────────────────────────────

class Router:
    """
    A URL router.

    Usage:
        router = Router()

        @router.get("/users")
        def list_users(request):
            return 200, [{"id": 1, "name": "Alice"}]

        @router.get("/users/<int:id>")
        def get_user(request, id):
            return 200, {"id": id, "name": "Alice"}

    URL parameters:
        <str:name>  — matches any path segment (no slashes), captured as str
        <int:id>    — matches digits only, captured as int
        <path:rest> — matches anything including slashes

    The view function receives `request` (a dict) and any URL params.
    It returns: (status_code, body_dict_or_string)
    """

    def __init__(self):
        self._routes: list[tuple] = []
        # Each entry: (method, regex_pattern, param_names_and_types, view_func)

    def _add_route(self, method: str, pattern: str, func):
        """
        Convert a URL pattern like "/users/<int:id>/posts" into a regex.

        "<int:id>"  → group that matches \d+ (captured as "id", converted to int)
        "<str:name>" → group that matches [^/]+ (captured as "name", as str)
        "<path:rest>" → group that matches .+ (captured as "rest", as str)

        "/users/<int:id>/posts"
        becomes: ^/users/(?P<id>\d+)/posts$
        with converters: {"id": int}
        """
        # YOUR CODE HERE — convert pattern to regex and store
        pass

    def get(self, pattern: str):
        """Decorator for GET routes."""
        def decorator(func):
            self._add_route("GET", pattern, func)
            return func
        return decorator

    def post(self, pattern: str):
        def decorator(func):
            self._add_route("POST", pattern, func)
            return func
        return decorator

    def put(self, pattern: str):
        def decorator(func):
            self._add_route("PUT", pattern, func)
            return func
        return decorator

    def delete(self, pattern: str):
        def decorator(func):
            self._add_route("DELETE", pattern, func)
            return func
        return decorator

    def route(self, pattern: str, methods=("GET",)):
        """Decorator that registers for multiple methods."""
        def decorator(func):
            for method in methods:
                self._add_route(method.upper(), pattern, func)
            return func
        return decorator

    def dispatch(self, environ, start_response):
        """
        Given a WSGI environ, find the matching route and call it.

        Steps:
        1. Extract method and path from environ
        2. Loop through registered routes
        3. Try to match path with each route's regex
        4. If match found with matching method: extract params, call view
        5. If path matches but wrong method: 405 Method Not Allowed
        6. No match at all: 404 Not Found

        The request dict passed to views:
            {
                "method": "GET",
                "path": "/users/42",
                "query_params": {"page": "2"},
                "headers": {"authorization": "Bearer ..."},
                "body": b"...",
                "environ": environ,
            }
        """
        # YOUR CODE HERE
        pass

    def _build_request(self, environ: dict) -> dict:
        """Build the request dict from environ."""
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        qs = environ.get("QUERY_STRING", "")

        query_params = {}
        if qs:
            for part in qs.split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    query_params[k] = v

        headers = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].lower().replace("_", "-")
                headers[header_name] = value

        content_length = int(environ.get("CONTENT_LENGTH") or 0)
        body = environ["wsgi.input"].read(content_length) if content_length else b""

        return {
            "method": method,
            "path": path,
            "query_params": query_params,
            "headers": headers,
            "body": body,
            "environ": environ,
        }

    def _send_json(self, start_response, status_code: int, data) -> list:
        """Helper to send a JSON response."""
        STATUS_MAP = {
            200: "200 OK",
            201: "201 Created",
            204: "204 No Content",
            400: "400 Bad Request",
            404: "404 Not Found",
            405: "405 Method Not Allowed",
            500: "500 Internal Server Error",
        }
        body = json.dumps(data, indent=2).encode("utf-8")
        status = STATUS_MAP.get(status_code, f"{status_code} Unknown")
        start_response(status, [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ])
        return [body]


# ─── Set up the app ───────────────────────────────────────────────────────────

router = Router()

# Fake in-memory "database"
USERS = {
    1: {"id": 1, "name": "Alice", "email": "alice@test.com"},
    2: {"id": 2, "name": "Bob",   "email": "bob@test.com"},
}
NEXT_ID = [3]

POSTS = {
    1: [{"id": 1, "title": "Hello World", "user_id": 1}],
    2: [{"id": 2, "title": "My First Post", "user_id": 2}],
}


@router.get("/")
def index(request):
    return 200, {
        "message": "API running",
        "endpoints": [
            "GET /users",
            "POST /users",
            "GET /users/<id>",
            "PUT /users/<id>",
            "DELETE /users/<id>",
            "GET /users/<id>/posts",
        ]
    }


@router.get("/users")
def list_users(request):
    return 200, list(USERS.values())


@router.post("/users")
def create_user(request):
    try:
        data = json.loads(request["body"])
    except (json.JSONDecodeError, ValueError):
        return 400, {"error": "Invalid JSON"}

    if "name" not in data or "email" not in data:
        return 400, {"error": "name and email are required"}

    user_id = NEXT_ID[0]
    NEXT_ID[0] += 1
    user = {"id": user_id, "name": data["name"], "email": data["email"]}
    USERS[user_id] = user
    return 201, user


@router.get("/users/<int:id>")
def get_user(request, id):
    user = USERS.get(id)
    if not user:
        return 404, {"error": f"User {id} not found"}
    return 200, user


@router.put("/users/<int:id>")
def update_user(request, id):
    if id not in USERS:
        return 404, {"error": f"User {id} not found"}

    try:
        data = json.loads(request["body"])
    except (json.JSONDecodeError, ValueError):
        return 400, {"error": "Invalid JSON"}

    USERS[id].update(data)
    return 200, USERS[id]


@router.delete("/users/<int:id>")
def delete_user(request, id):
    if id not in USERS:
        return 404, {"error": f"User {id} not found"}
    del USERS[id]
    return 204, {}


@router.get("/users/<int:id>/posts")
def user_posts(request, id):
    if id not in USERS:
        return 404, {"error": f"User {id} not found"}
    posts = POSTS.get(id, [])
    return 200, posts


# ─── WSGI entry point ─────────────────────────────────────────────────────────

def application(environ, start_response):
    return router.dispatch(environ, start_response)


if __name__ == "__main__":
    print("Router WSGI server at http://localhost:8002")
    print("\nTest commands:")
    print("  curl http://localhost:8002/")
    print("  curl http://localhost:8002/users")
    print("  curl http://localhost:8002/users/1")
    print("  curl http://localhost:8002/users/1/posts")
    print("  curl -X POST -H 'Content-Type: application/json' \\")
    print("       -d '{\"name\":\"Carol\",\"email\":\"carol@test.com\"}' \\")
    print("       http://localhost:8002/users")
    print("  curl -X DELETE http://localhost:8002/users/2")
    print("\nPress Ctrl+C to stop.\n")

    with make_server("", 8002, application) as httpd:
        httpd.serve_forever()
