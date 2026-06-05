# Module 10 — Deployment

> Your app runs on your laptop. Deployment makes it run on a real server, for real users, without breaking.

---

## Learning Objectives

- Understand the full production stack: Nginx + Gunicorn + Django
- Configure Django for production (settings, static files, env vars)
- Containerize with Docker
- Set up proper logging
- Write a health check endpoint

---

## 1. The Production Stack

```
Internet
   │
   ▼ :80/:443
┌──────────────────────────────────────────────────────┐
│  Nginx                                                │
│  - Handles SSL/TLS termination                        │
│  - Serves static files directly (no Django involved)  │
│  - Reverse-proxies dynamic requests to Gunicorn        │
│  - Load balancing across multiple Gunicorn workers     │
└────────────────────────┬─────────────────────────────┘
                         │ :8000 (localhost only)
                         ▼
┌──────────────────────────────────────────────────────┐
│  Gunicorn                                             │
│  - WSGI server: manages Python worker processes       │
│  - Each worker handles one request at a time          │
│  - Typically: 2-4 workers per CPU core                │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│  Django                                               │
│  - Runs in each Gunicorn worker                       │
│  - Speaks plain HTTP (Nginx handles HTTPS)            │
└────────────────────────┬─────────────────────────────┘
                         │
                         ▼
┌──────────────────┐   ┌───────────────────────────────┐
│  PostgreSQL       │   │  Redis                         │
│  (persistent DB)  │   │  (sessions, cache, queue)      │
└──────────────────┘   └───────────────────────────────┘
```

---

## 2. Gunicorn

```bash
pip install gunicorn

# Run with 4 workers
gunicorn myproject.wsgi:application --workers 4 --bind 0.0.0.0:8000

# Common options:
# --workers: number of worker processes (rule: 2-4 × CPU cores)
# --timeout: kill workers that take longer than N seconds
# --access-logfile: log each request
# --error-logfile: log errors
# --log-level: debug/info/warning/error

# Full production command:
gunicorn myproject.wsgi:application \
  --workers 4 \
  --bind unix:/tmp/gunicorn.sock \
  --timeout 30 \
  --access-logfile /var/log/gunicorn/access.log \
  --error-logfile /var/log/gunicorn/error.log \
  --log-level info
```

---

## 3. Production Settings

```python
# settings_production.py (or use environment variables)
import os

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = os.environ["ALLOWED_HOSTS"].split(",")

# Static files
STATIC_ROOT = "/app/staticfiles"
STATIC_URL = "/static/"

# Database from env
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ["DB_HOST"],
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
```

---

## 4. Docker

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "myproject.wsgi:application", "--workers", "4", "--bind", "0.0.0.0:8000"]
```

```yaml
# docker-compose.yml
version: "3.9"
services:
  web:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypassword
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  postgres_data:
```

---

## 5. Health Check Endpoint

Every production API needs a health check:

```python
from django.db import connection
from django.core.cache import cache
from django.http import JsonResponse

def health_check(request):
    checks = {}

    # DB check
    try:
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Cache check
    try:
        cache.set("health_check", "ok", timeout=10)
        checks["cache"] = "ok" if cache.get("health_check") == "ok" else "error"
    except Exception as e:
        checks["cache"] = f"error: {e}"

    status = 200 if all(v == "ok" for v in checks.values()) else 503
    return JsonResponse({"status": "ok" if status == 200 else "degraded", **checks}, status=status)
```

---

## Exercises

1. [Exercise 01 — Gunicorn Setup](exercises/01_gunicorn_setup.md)
2. [Exercise 02 — Docker](exercises/02_docker.md)
3. [Exercise 03 — Environment Config](exercises/03_env_config.md)

---

## Congratulations — Now Build Something Real

Proceed to the [Projects](../../projects/) directory.
