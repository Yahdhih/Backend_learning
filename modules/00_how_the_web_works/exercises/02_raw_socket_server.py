"""
Exercise 02 — Raw Socket Server

Goal: Build the simplest possible web server using only Python sockets.
No HTTP library. No Django. Just raw TCP + manually written HTTP text.

This teaches you what Django (and every web framework) does under the hood.

HOW TO RUN:
    python3 02_raw_socket_server.py

Then in another terminal:
    curl -v http://localhost:8888/
    curl -v http://localhost:8888/hello
    curl -v http://localhost:8888/json

WHAT YOU'LL SEE:
    The raw HTTP request your browser/curl sends, and the raw HTTP response
    you manually craft.
"""

import socket
import json
from datetime import datetime

HOST = "127.0.0.1"
PORT = 8888


def parse_request(raw_request: bytes) -> dict:
    """
    Parse raw HTTP bytes into a usable dict.

    A raw request looks like:
        GET /hello HTTP/1.1\r\n
        Host: localhost:8888\r\n
        User-Agent: curl/7.64.1\r\n
        \r\n

    The \r\n is CRLF (carriage return + line feed).
    The blank line (\r\n\r\n) separates headers from body.
    """
    text = raw_request.decode("utf-8", errors="replace")

    # Split headers from body
    if "\r\n\r\n" in text:
        header_section, body = text.split("\r\n\r\n", 1)
    else:
        header_section, body = text, ""

    lines = header_section.split("\r\n")

    # First line: "GET /path HTTP/1.1"
    request_line = lines[0]
    parts = request_line.split(" ")
    method = parts[0] if len(parts) > 0 else "GET"
    path = parts[1] if len(parts) > 1 else "/"
    version = parts[2] if len(parts) > 2 else "HTTP/1.1"

    # Parse headers
    headers = {}
    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key.lower()] = value

    return {
        "method": method,
        "path": path,
        "version": version,
        "headers": headers,
        "body": body,
    }


def make_response(status_code: int, status_text: str, body: str, content_type: str = "text/plain") -> bytes:
    """
    Build a raw HTTP response as bytes.

    Structure:
        HTTP/1.1 [code] [text]\r\n
        Content-Type: [type]\r\n
        Content-Length: [length]\r\n
        \r\n
        [body]
    """
    body_bytes = body.encode("utf-8")

    response_line = f"HTTP/1.1 {status_code} {status_text}"
    headers = [
        f"Content-Type: {content_type}; charset=utf-8",
        f"Content-Length: {len(body_bytes)}",
        f"Date: {datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}",
        "Connection: close",
        "Server: MySuperTinyServer/1.0",
    ]

    header_block = "\r\n".join([response_line] + headers)
    full_response = header_block + "\r\n\r\n" + body
    return full_response.encode("utf-8")


def handle_request(request: dict) -> bytes:
    """Route the request to the right handler."""
    path = request["path"]
    method = request["method"]

    print(f"\n→ {method} {path}")
    print(f"  Headers: {request['headers']}")

    if path == "/":
        body = "<h1>Hello from my raw socket server!</h1><p>No Django. No Flask. Just TCP.</p>"
        return make_response(200, "OK", body, "text/html")

    elif path == "/hello":
        body = "Hello, world! This is plain text."
        return make_response(200, "OK", body, "text/plain")

    elif path == "/json":
        data = {
            "message": "This is JSON",
            "server": "raw socket",
            "time": datetime.utcnow().isoformat(),
        }
        body = json.dumps(data)
        return make_response(200, "OK", body, "application/json")

    elif path == "/echo":
        body = json.dumps(request, indent=2)
        return make_response(200, "OK", body, "application/json")

    else:
        body = json.dumps({"error": "Not found", "path": path})
        return make_response(404, "Not Found", body, "application/json")


def run_server():
    """The main server loop."""

    # AF_INET = IPv4, SOCK_STREAM = TCP
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # SO_REUSEADDR lets us restart the server without waiting for the OS
    # to release the port (avoids "Address already in use" errors)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))

    # listen(5) = allow up to 5 connections in the queue
    server_socket.listen(5)

    print(f"Server listening on http://{HOST}:{PORT}")
    print("Routes:")
    print(f"  http://{HOST}:{PORT}/        → HTML")
    print(f"  http://{HOST}:{PORT}/hello   → plain text")
    print(f"  http://{HOST}:{PORT}/json    → JSON")
    print(f"  http://{HOST}:{PORT}/echo    → echoes your request back as JSON")
    print("\nPress Ctrl+C to stop.\n")

    try:
        while True:
            # accept() blocks until a client connects
            # Returns: (socket_for_this_connection, client_address)
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")

            try:
                # recv(4096) reads up to 4096 bytes
                raw_data = client_socket.recv(4096)

                if raw_data:
                    request = parse_request(raw_data)
                    response = handle_request(request)
                    client_socket.sendall(response)

            finally:
                client_socket.close()

    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server_socket.close()


# ─────────────────────────────────────────────────────────────────────────────
# EXERCISES — modify this file to complete these:
#
# 1. Add a /time route that returns the current server time as JSON.
#
# 2. Add a /status route that returns:
#    {"status": "ok", "uptime_seconds": X}
#    where X is how many seconds the server has been running.
#    Hint: use time.time() at startup and subtract.
#
# 3. Add basic routing for query parameters.
#    For GET /greet?name=Alice, return {"message": "Hello, Alice!"}
#    Hint: parse the path string — it'll look like "/greet?name=Alice"
#    Split on "?" to get the query string, then parse it.
#
# 4. CHALLENGE: Make the server handle POST /echo — read the request body
#    and return it back as JSON with {"method": "POST", "body": ...}
#    Test with: curl -X POST -d '{"test":1}' http://localhost:8888/echo
#
# 5. DEEP CHALLENGE: Make it handle multiple concurrent requests.
#    Right now it handles one at a time (single-threaded).
#    Use threading.Thread to handle each client in a separate thread.
#    This is exactly what Gunicorn workers do.
# ─────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    run_server()
