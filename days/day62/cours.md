# Jour 62 — Project Production : Dockeriser l'application (27 août 2026)

## Contexte du projet

Depuis le début de ce parcours, tu as construit une API Blog complète avec Django REST Framework. Tu as appris :
- Les bases de Django et DRF (Projects 01 & 02)
- L'authentification JWT, les permissions, les tests
- Les optimisations de requêtes et la mise en cache

**Aujourd'hui commence Project 03 — Production Ready.**

L'objectif : prendre cette API et la déployer en production de façon professionnelle. Au programme des 5 prochains jours :

| Jour | Sujet |
|------|-------|
| 62 | Dockerisation de l'application |
| 63 | Nginx + Gunicorn en production |
| 64 | Caching et performance |
| 65 | Monitoring, health checks, logs |
| 66 | Déploiement final + révision du parcours |

---

## Pourquoi Docker ?

Sans Docker, déployer une application Django implique :
- Installer Python, pip, virtualenv sur le serveur
- Configurer PostgreSQL, Redis manuellement
- Gérer les différences entre dev et prod
- "Ça marche sur ma machine" devient un vrai problème

Avec Docker :
- L'application tourne dans des conteneurs identiques partout
- Les dépendances sont encapsulées
- Le déploiement se résume à `docker-compose up`
- Les environnements dev/prod sont reproductibles

---

## Structure du projet

Voici la structure que nous allons créer :

```
blog_api/
├── blog/                      # Application Django
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   └── ...
├── blog_api/                  # Projet Django
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py            # Paramètres communs
│   │   ├── development.py     # Paramètres de dev
│   │   └── production.py      # Paramètres de prod
│   ├── urls.py
│   └── wsgi.py
├── nginx/
│   ├── nginx.conf             # Config Nginx (dev)
│   └── nginx.prod.conf        # Config Nginx (prod)
├── scripts/
│   └── entrypoint.sh          # Script de démarrage
├── static/                    # Fichiers statiques collectés
├── media/                     # Uploads utilisateurs
├── .env                       # Variables d'environnement (ne pas committer !)
├── .env.example               # Template des variables (à committer)
├── .dockerignore
├── Dockerfile
├── docker-compose.yml         # Dev
├── docker-compose.prod.yml    # Production
└── requirements/
    ├── base.txt               # Dépendances communes
    ├── development.txt        # Dépendances de dev
    └── production.txt         # Dépendances de prod
```

---

## Étape 1 : Organiser les requirements

### requirements/base.txt
```
Django==4.2.13
djangorestframework==3.15.1
djangorestframework-simplejwt==5.3.1
psycopg2-binary==2.9.9
django-cors-headers==4.3.1
Pillow==10.3.0
python-decouple==3.8
```

### requirements/development.txt
```
-r base.txt
django-debug-toolbar==4.3.0
factory-boy==3.3.0
faker==25.2.0
pytest-django==4.8.0
pytest-cov==5.0.0
ipython==8.24.0
```

### requirements/production.txt
```
-r base.txt
gunicorn==22.0.0
redis==5.0.4
django-redis==5.4.0
sentry-sdk==2.3.1
django-prometheus==2.3.1
python-json-logger==2.0.7
whitenoise==6.6.0
```

---

## Étape 2 : Séparer les settings

### blog_api/settings/base.py
```python
"""
Paramètres communs à tous les environnements.
"""
import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    # Local
    'blog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'blog_api.urls'
WSGI_APPLICATION = 'blog_api.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='blog_db'),
        'USER': config('DB_USER', default='blog_user'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='db'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 60,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000'
).split(',')
```

### blog_api/settings/development.py
```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']

# Utiliser la base de données locale en dev
DATABASES['default']['HOST'] = config('DB_HOST', default='db')

# Email dans la console en développement
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Cache simple en mémoire pour le dev
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
```

### blog_api/settings/production.py
```python
from .base import *
import sentry_sdk

DEBUG = False

# Sécurité
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'

# WhiteNoise pour les fichiers statiques
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Cache Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
        }
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Sentry — error tracking
sentry_sdk.init(
    dsn=config('SENTRY_DSN', default=''),
    traces_sample_rate=0.1,
    environment='production',
)

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
```

---

## Étape 3 : Le Dockerfile (multi-stage build)

Le **multi-stage build** permet de créer une image finale légère en séparant la phase de build (compilation des dépendances) de la phase d'exécution.

### Dockerfile
```dockerfile
# ============================================================
# STAGE 1 : Builder — installation des dépendances
# ============================================================
FROM python:3.11-slim AS builder

# Variables d'environnement pour Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Installer les dépendances système nécessaires pour la compilation
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les requirements
COPY requirements/ requirements/
RUN pip install --prefix=/install -r requirements/production.txt

# ============================================================
# STAGE 2 : Runtime — image finale légère
# ============================================================
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=blog_api.settings.production

WORKDIR /app

# Installer seulement les dépendances runtime (pas gcc, etc.)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier les packages Python installés depuis le builder
COPY --from=builder /install /usr/local

# Créer un utilisateur non-root pour la sécurité
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

# Copier le code de l'application
COPY --chown=appuser:appgroup . .

# Créer les répertoires nécessaires
RUN mkdir -p /app/static /app/media && \
    chown -R appuser:appgroup /app/static /app/media

# Rendre le script d'entrée exécutable
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
```

**Points clés du multi-stage build :**
- Stage `builder` : installe gcc et compile les dépendances (psycopg2, etc.)
- Stage `runtime` : copie seulement les packages compilés, sans gcc
- Résultat : image ~30% plus petite et plus sécurisée
- L'utilisateur non-root `appuser` limite les risques de sécurité

---

## Étape 4 : Le script d'entrée

### scripts/entrypoint.sh
```bash
#!/bin/bash

# Arrêter le script si une commande échoue
set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[ENTRYPOINT] Démarrage de l'application...${NC}"

# -------------------------------------------------------
# Attendre que la base de données soit prête
# -------------------------------------------------------
echo -e "${YELLOW}[ENTRYPOINT] Attente de la base de données...${NC}"

MAX_RETRIES=30
RETRY_COUNT=0

until python -c "
import psycopg2, os, sys
try:
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ.get('DB_NAME', 'blog_db'),
        user=os.environ.get('DB_USER', 'blog_user'),
        password=os.environ.get('DB_PASSWORD', '')
    )
    conn.close()
    print('DB OK')
except Exception as e:
    print(f'DB not ready: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo -e "${RED}[ENTRYPOINT] Impossible de joindre la base de données après $MAX_RETRIES tentatives${NC}"
        exit 1
    fi
    echo -e "${YELLOW}[ENTRYPOINT] Base de données non prête, attente 2 secondes... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

echo -e "${GREEN}[ENTRYPOINT] Base de données prête !${NC}"

# -------------------------------------------------------
# Appliquer les migrations
# -------------------------------------------------------
echo -e "${YELLOW}[ENTRYPOINT] Application des migrations...${NC}"
python manage.py migrate --noinput
echo -e "${GREEN}[ENTRYPOINT] Migrations appliquées !${NC}"

# -------------------------------------------------------
# Collecter les fichiers statiques (prod seulement)
# -------------------------------------------------------
if [ "$DJANGO_SETTINGS_MODULE" = "blog_api.settings.production" ]; then
    echo -e "${YELLOW}[ENTRYPOINT] Collecte des fichiers statiques...${NC}"
    python manage.py collectstatic --noinput --clear
    echo -e "${GREEN}[ENTRYPOINT] Fichiers statiques collectés !${NC}"
fi

# -------------------------------------------------------
# Créer un superutilisateur si défini en variables d'env
# -------------------------------------------------------
if [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo -e "${YELLOW}[ENTRYPOINT] Création du superutilisateur...${NC}"
    python manage.py createsuperuser \
        --noinput \
        --username "${DJANGO_SUPERUSER_USERNAME:-admin}" \
        --email "$DJANGO_SUPERUSER_EMAIL" \
        2>/dev/null || echo -e "${YELLOW}[ENTRYPOINT] Superutilisateur existe déjà${NC}"
fi

# -------------------------------------------------------
# Lancer la commande passée en argument (gunicorn ou autre)
# -------------------------------------------------------
echo -e "${GREEN}[ENTRYPOINT] Lancement de la commande : $@${NC}"
exec "$@"
```

---

## Étape 5 : docker-compose.yml (développement)

### docker-compose.yml
```yaml
version: '3.9'

services:
  # -------------------------------------------------------
  # Application Django (serveur de développement)
  # -------------------------------------------------------
  web:
    build:
      context: .
      target: builder   # Utiliser le stage builder pour le dev
    image: blog_api:dev
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app           # Mount du code pour le hot-reload
      - dev_static:/app/static
      - dev_media:/app/media
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DJANGO_SETTINGS_MODULE=blog_api.settings.development
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  # -------------------------------------------------------
  # Base de données PostgreSQL
  # -------------------------------------------------------
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    environment:
      POSTGRES_DB: ${DB_NAME:-blog_db}
      POSTGRES_USER: ${DB_USER:-blog_user}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"   # Exposé en dev pour pgAdmin/DBeaver
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-blog_user} -d ${DB_NAME:-blog_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # -------------------------------------------------------
  # Cache Redis
  # -------------------------------------------------------
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"   # Exposé en dev
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  dev_static:
  dev_media:
```

---

## Étape 6 : docker-compose.prod.yml (production)

### docker-compose.prod.yml
```yaml
version: '3.9'

services:
  # -------------------------------------------------------
  # Application Django avec Gunicorn
  # -------------------------------------------------------
  web:
    build:
      context: .
      target: runtime   # Image finale légère
    image: blog_api:prod
    command: gunicorn blog_api.wsgi:application --config /app/gunicorn.conf.py
    volumes:
      - static_volume:/app/static
      - media_volume:/app/media
    env_file:
      - .env.prod
    environment:
      - DJANGO_SETTINGS_MODULE=blog_api.settings.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    expose:
      - 8000    # Pas de port exposé directement, passe par Nginx
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          memory: 256M

  # -------------------------------------------------------
  # Nginx — reverse proxy
  # -------------------------------------------------------
  nginx:
    image: nginx:1.25-alpine
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/conf.d/default.conf:ro
      - static_volume:/var/www/static:ro
      - media_volume:/var/www/media:ro
      - certbot_certs:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - web
    restart: always

  # -------------------------------------------------------
  # Certbot pour SSL Let's Encrypt
  # -------------------------------------------------------
  certbot:
    image: certbot/certbot:latest
    volumes:
      - certbot_certs:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

  # -------------------------------------------------------
  # Base de données PostgreSQL
  # -------------------------------------------------------
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    # Pas de port exposé en prod !
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: always

  # -------------------------------------------------------
  # Cache Redis
  # -------------------------------------------------------
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --requirepass ${REDIS_PASSWORD}
    # Pas de port exposé en prod !
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: always

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
  certbot_certs:
  certbot_www:
```

---

## Étape 7 : Variables d'environnement

### .env (développement — NE PAS committer)
```bash
# Django
SECRET_KEY=dev-secret-key-change-in-production-please
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Base de données
DB_NAME=blog_db
DB_USER=blog_user
DB_PASSWORD=dev_password_123
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### .env.prod (production — stocker de façon sécurisée)
```bash
# Django
SECRET_KEY=votre-cle-secrete-tres-longue-et-aleatoire-ici
DEBUG=False
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com

# Base de données
DB_NAME=blog_db_prod
DB_USER=blog_user_prod
DB_PASSWORD=mot_de_passe_tres_securise_64_caracteres
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_PASSWORD=redis_mot_de_passe_securise

# Sentry
SENTRY_DSN=https://xxx@sentry.io/xxx

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=votre@email.com
EMAIL_HOST_PASSWORD=votre_app_password

# Superutilisateur initial
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@votre-domaine.com
DJANGO_SUPERUSER_PASSWORD=admin_mot_de_passe_securise

# CORS
CORS_ALLOWED_ORIGINS=https://votre-domaine.com
```

### .env.example (committer celui-ci)
```bash
# Django
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=

# Base de données
DB_NAME=blog_db
DB_USER=blog_user
DB_PASSWORD=
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=

# Sentry
SENTRY_DSN=

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Superutilisateur
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=
DJANGO_SUPERUSER_PASSWORD=
```

---

## Étape 8 : .dockerignore

### .dockerignore
```
# Git
.git
.gitignore
.github

# Python
__pycache__
*.py[cod]
*$py.class
*.so
.Python
*.egg
*.egg-info
dist
build
eggs
lib
lib64
parts
sdist
var
wheels
*.pyc
*.pyo
*.pyd

# Environnements virtuels
.venv
env/
venv/
ENV/

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
/static/
/media/

# Tests
.coverage
.pytest_cache
htmlcov/
.tox/

# IDEs
.idea/
.vscode/
*.swp
*.swo

# Docker
docker-compose.override.yml
.dockerignore

# Docs
docs/
*.md
README*

# Secrets — ne jamais inclure dans l'image
.env
.env.prod
.env.*
!.env.example
```

---

## Récapitulatif des commandes Docker

### Développement
```bash
# Construire les images
docker-compose build

# Démarrer tous les services
docker-compose up

# Démarrer en arrière-plan (detached)
docker-compose up -d

# Voir les logs
docker-compose logs -f web

# Accéder au shell Django
docker-compose exec web python manage.py shell

# Lancer les tests
docker-compose exec web python manage.py test

# Arrêter les services
docker-compose down

# Arrêter et supprimer les volumes (reset complet)
docker-compose down -v
```

### Production
```bash
# Construire pour la prod
docker-compose -f docker-compose.prod.yml build

# Démarrer en prod
docker-compose -f docker-compose.prod.yml up -d

# Voir l'état des services
docker-compose -f docker-compose.prod.yml ps

# Logs de la prod
docker-compose -f docker-compose.prod.yml logs -f

# Déployer une mise à jour
git pull
docker-compose -f docker-compose.prod.yml build web
docker-compose -f docker-compose.prod.yml up -d web

# Backup de la base de données
docker-compose -f docker-compose.prod.yml exec db \
    pg_dump -U blog_user blog_db > backup_$(date +%Y%m%d).sql
```

---

## Concepts clés à retenir

| Concept | Explication |
|---------|-------------|
| Multi-stage build | Sépare build et runtime pour des images plus petites |
| Health checks | Docker sait quand un service est vraiment prêt |
| Volumes | Persistance des données entre redémarrages |
| Networks | Les services se parlent par leur nom (ex: `db`, `redis`) |
| `expose` vs `ports` | `expose` = entre conteneurs ; `ports` = vers l'extérieur |
| `depends_on` | Ordre de démarrage + condition de santé |
| `.dockerignore` | Ce qui n'est pas copié dans l'image (comme `.gitignore`) |

---

## Prochain cours

Demain (Jour 63), on configure **Nginx et Gunicorn** pour servir l'application en production avec SSL, gestion des fichiers statiques et headers de sécurité.
