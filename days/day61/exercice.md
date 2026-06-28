# Exercice Jour 61 — Déploiement avec Docker + Gunicorn + Nginx

## Objectif

Dockeriser le projet blog (ou n'importe quel projet Django existant) et le déployer avec Gunicorn derrière Nginx.

---

## Étape 1 : Préparer le projet

```bash
# Structure cible
monblog/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   └── articles/
├── static/
├── templates/
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── nginx.conf
├── entrypoint.sh
├── requirements.txt
└── .env.production.example
```

---

## Étape 2 : Séparer les settings

[config/settings/base.py](config/settings/base.py) :
```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
INSTALLED_APPS = [...]
```

[config/settings/production.py](config/settings/production.py) :
```python
from .base import *

DEBUG = False
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", ...}}
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
```

---

## Étape 3 : Écrire le Dockerfile

Crée [Dockerfile](Dockerfile) :

```dockerfile
FROM python:3.12-slim

# TODO : installer libpq-dev pour PostgreSQL
# TODO : copier requirements.txt et pip install
# TODO : copier le code
# TODO : collectstatic
# TODO : créer un user non-root
# TODO : CMD gunicorn
```

---

## Étape 4 : Écrire docker-compose.yml

Crée [docker-compose.yml](docker-compose.yml) :

```yaml
version: "3.9"
services:
  web:
    # TODO : build, volumes pour static/media, env_file, depends_on db

  db:
    image: postgres:15
    # TODO : volumes, environment

  nginx:
    image: nginx:alpine
    # TODO : volumes nginx.conf + static + media, ports 80:80
    depends_on: [web]

volumes:
  # TODO : postgres_data, static_volume, media_volume
```

---

## Étape 5 : Configurer Nginx

Crée [nginx.conf](nginx.conf) avec :
- Redirection HTTP → HTTPS
- Location `/static/` → alias vers `/static/`
- Location `/media/` → alias vers `/media/`
- Location `/` → proxy_pass vers `web:8000`

---

## Étape 6 : entrypoint.sh

Crée [entrypoint.sh](entrypoint.sh) :
```bash
#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static..."
python manage.py collectstatic --noinput

exec "$@"
```

---

## Étape 7 : Lancer et tester

```bash
# Build et démarrer
docker-compose up --build

# Vérifier les logs
docker-compose logs web
docker-compose logs nginx

# Lancer les tests dans le container
docker-compose exec web python manage.py test

# Créer un superuser
docker-compose exec web python manage.py createsuperuser

# Arrêter
docker-compose down
```

---

## Vérifications

- [ ] `http://localhost` → redirige vers HTTPS (ou affiche l'app)
- [ ] `/static/admin/` est servi par Nginx, pas Django
- [ ] Upload d'image → fichier dans `media/`
- [ ] `docker-compose exec web python manage.py check --deploy` → 0 erreur critique
- [ ] Les logs Nginx montrent les accès aux statiques séparément de l'app

---

## Questions pour `notes.md`

1. Pourquoi utiliser Gunicorn au lieu du serveur de dev Django ?
2. Pourquoi Nginx devant Gunicorn plutôt que Gunicorn directement exposé ?
3. Que se passe-t-il si les migrations ne sont pas faites avant le déploiement ?
4. Combien de workers Gunicorn pour un serveur 2 vCPU ?
