# Project 03 — Production Ready

**Prerequisites:** Complete all modules

**Time estimate:** 4–5 hours

Take Project 01 (Blog API) and make it production-ready.

---

## What You'll Add

1. **Docker**: Containerize the entire stack (web + db + redis + nginx)
2. **Caching**: Cache popular posts list, user profiles
3. **Background tasks**: Use Celery + Redis for sending emails async
4. **Logging**: Structured JSON logs, request IDs
5. **Health checks**: `/health/` endpoint that checks DB, Redis, migrations
6. **Environment config**: All secrets from environment variables
7. **Static files**: Nginx serves them, WhiteNoise for simpler setups

---

## docker-compose.yml

You'll build a `docker-compose.yml` that spins up:
- `web`: Gunicorn running Django
- `db`: PostgreSQL
- `redis`: Redis (cache + Celery broker)
- `nginx`: reverse proxy
- `celery`: background task worker
- `celery-beat`: scheduled tasks

---

## Acceptance Criteria

- [ ] `docker compose up` starts the entire stack
- [ ] All tests pass inside Docker: `docker compose run web python manage.py test`
- [ ] `/health/` returns 200 when all services are healthy, 503 if any are down
- [ ] Popular posts endpoint cached with Redis (verify: second request has 0 DB queries)
- [ ] No secrets hardcoded — all from `.env` file
- [ ] Nginx serves `/static/` files directly (Django not involved)
- [ ] Emails sent via Celery (async, non-blocking)
- [ ] Migrations run automatically on startup
