# Exercise 01 — HTTP Methods Lab

Using `curl` and `httpbin.org`, explore each HTTP method in depth.

---

## Part A: GET with Query Parameters

```bash
curl -v "https://httpbin.org/get?page=2&limit=10&sort=desc"
```

Look at the response body. httpbin echoes back what you sent.

**Questions:**
1. Where do the query parameters appear in the request?
2. Are query parameters part of the URL or the body?
3. Why should you never put sensitive data (passwords, tokens) in query strings?

---

## Part B: POST vs PUT vs PATCH

```bash
# POST — create
curl -X POST https://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@test.com"}'

# PUT — replace entirely
curl -X PUT https://httpbin.org/put \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Updated", "email": "alice@test.com", "age": 30}'

# PATCH — partial update
curl -X PATCH https://httpbin.org/patch \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice New Name"}'
```

**Questions:**
1. For a `PUT /users/1`, the client must send ALL fields (not just changed ones). Why?
2. If you send `PATCH /users/1 {"name": "Alice"}`, what happens to the `email` field?
3. A blog platform has posts. User changes only the title. Which method should the client use?

---

## Part C: DELETE and Idempotency

```bash
# We'll simulate this against a local server from Module 00
# For now, observe the concept:

# First DELETE: user exists, gets deleted → 204 No Content
# Second DELETE: user already gone → 404 Not Found

# Both calls result in the same state: user does not exist
# That's idempotency: the end state is the same regardless of how many times you call it
```

**Question:** `POST /users` is NOT idempotent. Calling it twice creates two users. Design a way to make creating a resource idempotent. (Hint: think about unique identifiers)

---

## Part D: HEAD — Check Without Downloading

```bash
# Full GET — downloads the body
curl -v https://httpbin.org/get

# HEAD — only headers, no body
curl -I https://httpbin.org/get
```

**When is HEAD useful in a real app?**

```bash
# Check if a large file has changed before downloading it
curl -I https://httpbin.org/image/png
# Look at Content-Length and ETag
```

**Question:** A mobile app needs to check if a user's avatar has changed (to decide whether to re-download it). Design the HTTP interaction using HEAD and ETags. What headers are involved?

---

## Part E: OPTIONS — Discover What's Allowed

```bash
curl -X OPTIONS -v https://httpbin.org/get \
  -H "Origin: https://myapp.com" \
  -H "Access-Control-Request-Method: POST"
```

**Questions:**
1. What does the `Allow` header in the response tell you?
2. What CORS-related headers do you see?
3. When does a browser automatically send an OPTIONS request?

---

## Part F: Build a RESTful URL Design

Given this data model:
- Blog with Posts
- Each Post has Comments
- Users can Like posts

Design the URL structure for a REST API. For each resource, list all the endpoints with their method and what they do.

Example format:
```
GET    /posts           → list all posts
POST   /posts           → create a post
GET    /posts/{id}      → get a specific post
PUT    /posts/{id}      → replace a post
PATCH  /posts/{id}      → partially update a post
DELETE /posts/{id}      → delete a post
```

Now add comments and likes. Where do they go in the URL hierarchy?

---

## Challenge: The N+1 URL Problem

Consider two designs for getting a user's posts:

**Design A:**
```
GET /users/5/posts      → returns user 5's posts
```

**Design B:**
```
GET /posts?user_id=5    → filter posts by user
```

Research and answer:
1. What are the trade-offs between these two designs?
2. Which is more "RESTful"?
3. When would you prefer one over the other?
