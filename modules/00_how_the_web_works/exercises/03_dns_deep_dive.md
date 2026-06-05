# Exercise 03 — DNS Deep Dive

DNS is the first thing that happens for every web request. Understanding it will save you hours of debugging "why can't my server be reached?" issues.

---

## Part A: Basic DNS Lookup

```bash
# Basic lookup
dig google.com

# Shorter output
dig +short google.com

# Look up a specific record type
dig google.com A        # IPv4 address records
dig google.com AAAA     # IPv6 address records
dig google.com MX       # Mail server records
dig google.com TXT      # Text records (often used for domain verification)
dig google.com NS       # Name server records
```

**Questions:**
1. What is the TTL on google.com's A record?
2. Run `dig +short google.com` three times in a row. Do you get the same IPs? Why might you get different ones?
3. What are MX records used for?

---

## Part B: Trace the Full DNS Resolution

```bash
dig +trace google.com
```

This shows the full recursive resolution from root servers down.

**Look for:**
- Which root servers are queried (they're labeled `.`)
- Which `.com` nameservers respond
- Which `google.com` nameservers give the final answer

**Question:** How many DNS servers are involved in resolving `google.com`? Name each "level."

---

## Part C: DNS Caching in Action

```bash
# First lookup (might be slow — fetching from root)
time dig google.com

# Run immediately again
time dig google.com

# Check what's actually cached on your machine
dig google.com | grep "Query time"
```

**Question:** Why is the second query faster? Where is the cache?

---

## Part D: Reverse DNS (PTR records)

Forward DNS: domain → IP
Reverse DNS: IP → domain

```bash
# Find the IP for httpbin.org
dig +short httpbin.org

# Now reverse lookup that IP
dig -x [the IP you got]

# Shortcut
host [the IP you got]
```

**Question:** Does the reverse lookup return the same domain? (It often doesn't — explain why.)

---

## Part E: Local DNS Resolution

Your machine has a `hosts` file that takes priority over DNS:

```bash
# View it (macOS/Linux)
cat /etc/hosts
```

You'll see entries like `127.0.0.1 localhost`.

**Exercise:** Understand what would happen if you added:
```
127.0.0.1 myapp.local
```

You don't need to add it, but: if you did, what would happen when you visited `http://myapp.local` in a browser? This is how developers fake local domains.

---

## Part F: DNS in the Context of Backend Deployments

When you deploy a Django app to a server:

1. You buy a domain (`myapi.com`) from a registrar (Namecheap, GoDaddy)
2. You create an **A record**: `myapi.com → 1.2.3.4` (your server's IP)
3. You wait for TTL (can be 30 min to 48 hours for propagation)
4. Now `myapi.com` resolves to your server worldwide

```bash
# You can check propagation from multiple global DNS servers
dig @8.8.8.8 google.com    # Use Google's DNS
dig @1.1.1.1 google.com    # Use Cloudflare's DNS
dig @8.8.4.4 google.com    # Use Google's secondary DNS
```

**Question:** If you change an A record with TTL=3600 at 2pm, when is it safe to expect everyone in the world has the new IP?

---

## Challenge

```bash
# What DNS record type does this query?
dig _dmarc.google.com TXT

# What is DMARC? Why is it a TXT record?
# Hint: it's email-related

# Also try:
dig _dmarc.github.com TXT
```

Research: what is the difference between a CNAME record and an A record? When would you use a CNAME for your API?

---

## Key Takeaway

DNS is a globally distributed, cached database. Every domain name query follows a tree structure from root → TLD → domain. Caching makes it fast but also means changes take time to propagate. In backend development you'll deal with DNS when deploying, debugging, and configuring infrastructure.
