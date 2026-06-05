# Exercise 01 — curl Exploration

`curl` is a command-line tool that speaks HTTP. It's the best way to see raw HTTP without a browser hiding things from you.

---

## Part A: Your First curl Request

Run this in your terminal:

```bash
curl -v https://httpbin.org/get
```

The `-v` flag means "verbose" — show everything.

**Look for these in the output:**
- Lines starting with `>` are your **request headers**
- Lines starting with `<` are the **response headers**
- The JSON body at the end is the **response body**

**Questions to answer:**
1. What HTTP method was used?
2. What is the `Content-Type` of the response?
3. What HTTP version is being used?
4. What status code did you get?

---

## Part B: Inspect the Request Headers

```bash
curl -v -H "Accept: application/json" -H "X-My-Header: hello" https://httpbin.org/headers
```

httpbin.org/headers echoes back the headers it received.

**Question:** Do you see `X-My-Header` in the response body? What does this tell you about headers?

---

## Part C: POST Request with a Body

```bash
curl -v -X POST https://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "age": 30}'
```

**Questions:**
1. What does `-X POST` do?
2. What does `-d` do?
3. Why must you include `Content-Type: application/json`?
4. Look at the `Content-Length` header in your request — what is it? Calculate it yourself.

---

## Part D: Status Codes

Run each of these and note the status code:

```bash
# 200 OK
curl -v https://httpbin.org/status/200

# 404 Not Found
curl -v https://httpbin.org/status/404

# 500 Internal Server Error
curl -v https://httpbin.org/status/500

# 301 Redirect (use -L to follow)
curl -v https://httpbin.org/redirect/1
curl -vL https://httpbin.org/redirect/1   # compare with -L flag
```

**Question:** When you use `-L`, curl follows the redirect. Look at the verbose output — how many HTTP requests are made?

---

## Part E: Response Timing

```bash
curl -w "\n\nDNS: %{time_namelookup}s\nTCP: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" \
  -o /dev/null -s https://httpbin.org/get
```

This shows you timing for each phase.

**Questions:**
1. What does TTFB (Time To First Byte) measure?
2. Why is DNS time separate from TCP time?
3. Run it 3 times. Does DNS time drop on subsequent requests? Why?

---

## Part F: Seeing Headers Only

```bash
curl -I https://httpbin.org/get
```

`-I` sends a `HEAD` request — response headers only, no body.

**Question:** When would a `HEAD` request be useful in a real application?

---

## Challenge

Write a curl command that:
1. Makes a PUT request
2. Sends JSON body `{"name": "updated"}`
3. Includes an `Authorization: Bearer fake-token` header
4. Shows only the response headers (no body)
5. Follows redirects if any

<details>
<summary>Answer (try first)</summary>

```bash
curl -v -X PUT \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer fake-token" \
  -d '{"name": "updated"}' \
  -I \
  -L \
  https://httpbin.org/put
```

Note: `-I` with a body doesn't quite work as expected — the proper way is `-X HEAD` or just use `-v` and read only the response headers. In practice you'd use `-o /dev/null` and `-D -` to dump headers only.
</details>

---

## Key Takeaway

HTTP is just **text** sent over a TCP connection. curl proves this — it builds that text, sends it, and prints what it gets back. Django does the same thing, just automatically.
