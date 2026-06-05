# Backend Learning — Deep Understanding Track

> Stack: **Python + Django** | Goal: **Deep web understanding**

This is not a tutorial to copy-paste. It is a system to build genuine understanding. Every module has theory, a diagram, hands-on exercises, and a challenge that forces you to think.

---

## How to Use This Repo

1. Work through modules **in order** — each one builds on the last
2. Read the theory **before** running any code
3. Do **all exercises** — understanding only clicks through doing
4. Mark your progress in [PROGRESS.md](PROGRESS.md)
5. Each module ends with a **"What just happened?"** question — answer it in your own words before moving on

---

## The Full Map

```
THE INTERNET
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 00 — How the Web Works                              │
│  DNS · TCP/IP · HTTP · The request/response cycle           │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 01 — Python Crash Course                            │
│  For people who already know a language                     │
│  Types · Functions · Classes · Decorators · Async           │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 02 — HTTP In Depth                                  │
│  Methods · Headers · Status codes · Content negotiation     │
│  HTTPS · Cookies · CORS                                     │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 03 — WSGI: Before Django Exists                     │
│  What sits between the web server and Python                │
│  Build a raw WSGI app by hand                               │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 04 — Django Fundamentals                            │
│  MTV pattern · URL routing · Views · Templates · ORM intro  │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 05 — Databases & The ORM                            │
│  SQL from scratch · PostgreSQL · Django ORM · Migrations    │
│  Queries · N+1 problem · Indexes                            │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 06 — REST APIs with DRF                             │
│  REST constraints · Serializers · ViewSets · Routers        │
│  Pagination · Filtering · Versioning                        │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 07 — Auth & Sessions                                │
│  Session-based auth · JWT · OAuth2 · Permissions            │
│  Password hashing · Token rotation                          │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 08 — Security                                       │
│  CSRF · XSS · SQL injection · Rate limiting                 │
│  Django security checklist                                  │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 09 — Caching & Performance                          │
│  Redis · Django cache framework · Cache strategies          │
│  DB query optimization · select_related / prefetch_related  │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 10 — Deployment                                     │
│  Gunicorn · Nginx · Docker · Environment variables          │
│  Static files · Logs · Health checks                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Projects (Apply Everything)

| Project | After Module | What You Build |
|---------|-------------|----------------|
| [Blog API](projects/project_01_blog_api/) | 06 | Full CRUD REST API with pagination |
| [Auth System](projects/project_02_auth_system/) | 07 | JWT auth + permissions + user roles |
| [Production Ready](projects/project_03_production_ready/) | 10 | Dockerized, cached, deployed app |

---

## Prerequisites

- You know at least one programming language (loops, functions, classes)
- Python installed: `python3 --version` (need 3.10+)
- A terminal you're comfortable with
- `curl` installed (comes with macOS/Linux)

---

## Estimated Time

| Module | Time |
|--------|------|
| 00 | 2–3 hours |
| 01 | 3–4 hours |
| 02 | 3–4 hours |
| 03 | 2–3 hours |
| 04 | 5–6 hours |
| 05 | 6–8 hours |
| 06 | 5–6 hours |
| 07 | 4–5 hours |
| 08 | 3–4 hours |
| 09 | 3–4 hours |
| 10 | 4–5 hours |
| Projects | 10–15 hours |
| **Total** | **~55–65 hours** |

Work 2 hours/day → done in about 1 month with deep understanding.

---

## Start Here → [Module 00: How the Web Works](modules/00_how_the_web_works/README.md)
