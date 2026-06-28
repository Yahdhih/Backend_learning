# Jour 61 — Déploiement : Docker, Gunicorn, Nginx
📅 26 août 2026 · Module : Déploiement

---

## L'architecture de production

```
Internet
  ↓ HTTPS (port 443)
Nginx (reverse proxy)
  ├── /static/ → fichiers statiques (servis directement)
  ├── /media/  → fichiers uploadés (servis directement)
  └── /        → Gunicorn (workers Python)
                   ↓
                Django Application
                   ↓
                PostgreSQL / Redis
```

---

## Gunicorn — le serveur WSGI

```bash
pip install gunicorn

# Lancer
gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \           # cpu_count * 2 + 1
    --worker-class sync \   # ou gevent/uvicorn pour async
    --timeout 30 \
    --log-level info \
    --access-logfile -      # stdout
```

**Calcul workers** : `(2 × nb_cpus) + 1` pour les I/O-bound (DB, réseau)

---

## Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dépendances Python (couche séparée pour le cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif
COPY . .

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput

# Pas root en prod
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

---

## docker-compose.yml

```yaml
version: "3.9"

services:
  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    env_file:
      - .env.production
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: monsite_db
      POSTGRES_USER: monsite
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine

  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - static_volume:/static
      - media_volume:/media
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - web

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

---

## nginx.conf

```nginx
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name monsite.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name monsite.com;

    ssl_certificate /etc/ssl/certs/monsite.crt;
    ssl_certificate_key /etc/ssl/private/monsite.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    client_max_body_size 20M;  # taille max upload

    location /static/ {
        alias /static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /media/;
        expires 7d;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

---

## Migrations en production

```bash
# Toujours faire les migrations AVANT de déployer le code nouveau
# Sinon le code cherche des colonnes qui n'existent pas encore

# Dans docker-compose, utiliser un entrypoint
# entrypoint.sh
#!/bin/bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec "$@"
```

```dockerfile
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## Variables d'environnement en prod

```bash
# .env.production (ne jamais commiter)
DJANGO_SECRET_KEY=votre-vraie-secret-key-aleatoire-256bits
DEBUG=False
ALLOWED_HOSTS=monsite.com,www.monsite.com
DATABASE_URL=postgresql://monsite:${DB_PASSWORD}@db:5432/monsite_db
REDIS_URL=redis://redis:6379/0
```
