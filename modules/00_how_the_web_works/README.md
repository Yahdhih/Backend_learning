# Module 00 — How the Web Works

> Before writing a single line of Django, you must understand what happens before your code even runs.

---

## Learning Objectives

By the end of this module you will be able to:
- Trace a URL request from the browser to a server and back
- Explain what DNS is and why it exists
- Describe TCP/IP in plain language
- Read a raw HTTP request and response
- Know what a port is and why servers listen on one

---

## 1. The Big Picture

When you type `https://api.example.com/users` into a browser and press Enter, about **8 things** happen before you see a response.

```
YOU (browser)                           INTERNET                   SERVER
    │                                                                  │
    │  1. "Where is api.example.com?"                                  │
    │──────────────────────────────────────────────► DNS Resolver      │
    │◄──────────────────────────────────────────── "93.184.216.34"     │
    │                                                                  │
    │  2. TCP handshake to 93.184.216.34:443                           │
    │──────────── SYN ──────────────────────────────────────────────►  │
    │◄─────────── SYN-ACK ──────────────────────────────────────────   │
    │──────────── ACK ──────────────────────────────────────────────►  │
    │                                                                  │
    │  3. TLS handshake (because HTTPS)                                │
    │◄──────────────── encrypted channel established ───────────────   │
    │                                                                  │
    │  4. HTTP Request sent over the encrypted channel                 │
    │──────────── GET /users HTTP/1.1 ──────────────────────────────►  │
    │             Host: api.example.com                                │
    │             Accept: application/json                             │
    │                                                                  │
    │  5. Server receives request → routes to Django                   │
    │     Django runs your code, queries database                      │
    │                                                                  │
    │  6. HTTP Response sent back                                      │
    │◄─────────── HTTP/1.1 200 OK ──────────────────────────────────   │
    │             Content-Type: application/json                       │
    │             [{"id":1,"name":"Alice"},...]                        │
    │                                                                  │
    │  7. TCP connection closed (or kept alive)                        │
    │  8. Browser renders the response                                 │
```

Let's go through each step.

---

## 2. DNS — The Phone Book of the Internet

IP addresses are how computers actually find each other: `93.184.216.34`. But humans use names: `api.example.com`. DNS (Domain Name System) translates one to the other.

```
Browser                DNS Resolver              Root NS          .com NS         example.com NS
   │                        │                        │                │                   │
   │─── "api.example.com?" ─►                        │                │                   │
   │                        │─── "example.com?" ────►│                │                   │
   │                        │◄── "ask .com NS" ───────                │                   │
   │                        │─────────────────────── "example.com?" ─►│                   │
   │                        │◄────────────────────── "ask NS at X" ───                    │
   │                        │──────────────────────────────────── "api.example.com?" ────►│
   │                        │◄─────────────────────────────────── "93.184.216.34" ─────── │
   │◄── "93.184.216.34" ────                         │                │                   │
```

**Key facts:**
- This happens for every new domain you visit
- Results are **cached** (your OS, router, and ISP all cache DNS)
- `TTL` (Time To Live) controls how long a DNS result is cached
- Run `dig api.example.com` in your terminal to see this happen

---

## 3. TCP/IP — The Delivery System

IP (Internet Protocol) routes packets between machines. TCP (Transmission Control Protocol) ensures they arrive in order, without errors.

Think of it like this:
- **IP** = postal addresses and routing
- **TCP** = registered mail with confirmation of delivery

**The TCP 3-way handshake** establishes a connection before any data flows:

```
Client                    Server
  │                         │
  │──── SYN ───────────────►│   "I want to connect, starting seq #100"
  │◄─── SYN-ACK ────────────│   "OK, my seq is #200, I got your #100"
  │──── ACK ───────────────►│   "Got it, we're connected"
  │                         │
  │  [data flows both ways] │
  │                         │
  │──── FIN ───────────────►│   "I'm done"
  │◄─── ACK ────────────────│   "OK"
  │◄─── FIN ────────────────│   "Me too"
  │──── ACK ───────────────►│   "OK, goodbye"
```

**Ports** are like apartment numbers — the IP address finds the building, the port finds the right service:
- Port 80 = HTTP
- Port 443 = HTTPS
- Port 5432 = PostgreSQL
- Port 6379 = Redis
- Port 8000 = Django dev server (by convention)

---

## 4. HTTP — The Language Servers Speak

HTTP (HyperText Transfer Protocol) is a text-based protocol. A request looks exactly like this:

```
GET /users?page=2 HTTP/1.1
Host: api.example.com
Accept: application/json
Authorization: Bearer eyJhbGci...
User-Agent: Mozilla/5.0
Connection: keep-alive
                              ← blank line marks end of headers
```

A response looks like this:

```
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 82
Cache-Control: max-age=60
Date: Thu, 05 Jun 2026 10:00:00 GMT
                              ← blank line marks end of headers
[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"}]
```

The structure is always:
```
[METHOD] [PATH] [HTTP VERSION]
[Header-Name]: [Header-Value]
[Header-Name]: [Header-Value]
... (as many headers as needed)
                              ← one blank line
[body - optional]
```

**HTTP is stateless.** Each request is completely independent. The server has no memory of previous requests. This is why cookies and sessions exist — they're workarounds for statelessness.

---

## 5. How Django Fits In

When a request reaches your server, multiple layers of software handle it before your Django code runs:

```
Internet
   │
   ▼
┌──────────────────┐
│   Nginx           │  ← "Reverse proxy" — handles SSL, serves static files,
│   (web server)    │    passes dynamic requests to Gunicorn
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Gunicorn        │  ← "WSGI server" — spawns Python workers,
│   (WSGI server)   │    translates HTTP into Python function calls
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Django          │  ← Your code: URL routing, views, ORM, response
│   (WSGI app)      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   PostgreSQL      │  ← Database — stores the actual data
└──────────────────┘
```

In **development**, `python manage.py runserver` collapses Nginx + Gunicorn into one simple dev server. That's why you never use it in production — it's not built for real traffic.

---

## Key Concepts to Commit to Memory

| Concept | One-liner |
|---------|-----------|
| DNS | Translates domain names to IP addresses |
| IP | Routes packets across the internet |
| TCP | Guarantees reliable, ordered delivery |
| Port | Identifies which service on a machine |
| HTTP | Text protocol for request/response communication |
| Stateless | HTTP has no memory between requests |
| WSGI | The interface between Python and web servers |

---

## What Just Happened?

Before going to the exercises, answer this in your own words:

> "A user's browser requests `GET https://shop.example.com/products`. Describe every step that happens, from the user pressing Enter to the browser displaying JSON data. Include DNS, TCP, HTTP, and what the server does."

Write it down. If you can't, re-read sections 2–5.

---

## Exercises

1. [Exercise 01 — curl Exploration](exercises/01_curl_exploration.md)
2. [Exercise 02 — Raw Socket Server](exercises/02_raw_socket_server.py)
3. [Exercise 03 — DNS Deep Dive](exercises/03_dns_deep_dive.md)

---

## Next → [Module 01: Python Crash Course](../01_python_crash_course/README.md)
