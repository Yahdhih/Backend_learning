# Jour 59 — Configuration 12-factor et Variables d'environnement (24 août 2026)

## La méthodologie 12-factor app

La méthodologie **12-factor** (douze facteurs) a été publiée par les équipes d'Heroku en 2012. Elle définit 12 principes pour construire des applications modernes, faciles à déployer, scalables et maintenables. Ces principes sont devenus des standards de l'industrie pour les applications cloud-native.

Vous trouverez la documentation complète sur https://12factor.net

---

### Facteur I : Codebase (Base de code)

**Principe :** Une seule base de code suivie dans le contrôle de version, déployée en plusieurs environnements.

```
               ┌────────────┐
               │   Repo Git │
               └─────┬──────┘
                      │
           ┌──────────┼──────────┐
           ▼          ▼          ▼
        Dev         Staging    Production
     (local)       (serveur)   (serveur)
```

**À éviter :** Avoir des repos git séparés pour production et développement. **Un seul repo, plusieurs déploiements.**

```bash
# Bon : même code, différentes configs via env vars
git clone https://github.com/user/monprojet.git

# Mauvais : branches séparées pour prod/dev (anti-pattern)
git checkout prod-branch   # NE FAITES PAS ÇA
```

---

### Facteur II : Dependencies (Dépendances)

**Principe :** Déclarer et isoler explicitement toutes les dépendances.

```bash
# requirements.txt avec versions fixées
Django==4.2.14          # version exacte
gunicorn==21.2.0
psycopg2-binary==2.9.9

# Jamais de dépendances implicites sur des bibliothèques système
# Toujours utiliser un virtualenv ou un conteneur Docker
```

```bash
# Générer requirements.txt depuis l'environnement actuel
pip freeze > requirements.txt

# Encore mieux : utiliser pip-tools pour séparer les dépendances directes
# requirements.in
Django>=4.2,<5.0
gunicorn

# pip-compile génère requirements.txt avec toutes les dépendances transitives
pip-compile requirements.in
```

---

### Facteur III : Config (Configuration)

**Principe :** Stocker la configuration dans l'environnement, pas dans le code.

C'est le facteur le plus impactant pour Django. **Toute valeur qui change entre les environnements (dev, staging, prod) doit être une variable d'environnement.**

Ce qui appartient aux variables d'environnement :
- `SECRET_KEY`
- `DEBUG`
- Connexions aux bases de données (`DATABASE_URL`)
- Clés API tierces (Stripe, SendGrid, AWS...)
- `ALLOWED_HOSTS`
- Connexions Redis/Celery

Ce qui **ne** change pas entre environnements (et peut être dans le code) :
- Structure des URLs
- Définitions des modèles
- Logique métier

---

### Facteur IV : Backing Services (Services de support)

**Principe :** Traiter les services de support (bases de données, queues, cache, email) comme des ressources attachables.

```python
# Bon : configuré via URL, facilement remplaçable
DATABASES = {'default': dj_database_url.parse(os.environ['DATABASE_URL'])}
CACHES = {'default': {'BACKEND': 'django_redis.cache.RedisCache',
                       'LOCATION': os.environ['REDIS_URL']}}

# Mauvais : hardcodé, impossible à changer sans modifier le code
DATABASES = {
    'default': {
        'HOST': 'localhost',
        'NAME': 'monprojet_prod',
        ...
    }
}
```

---

### Facteur V : Build, Release, Run (Construction, publication, exécution)

**Principe :** Séparer strictement les étapes de build, release et run.

```
Code source + Config
       │
  ┌────▼────┐   ┌──────────────┐   ┌──────────┐
  │  Build  │──▶│   Release    │──▶│   Run    │
  │(pip,    │   │(image Docker │   │(gunicorn,│
  │collectst│   │+ config env) │   │worker...)│
  └─────────┘   └──────────────┘   └──────────┘
```

En pratique avec Docker : le Dockerfile = build, l'image + docker-compose = release, `docker-compose up` = run.

---

### Facteur VI : Processes (Processus)

**Principe :** Exécuter l'application comme un ou plusieurs processus sans état.

```python
# Mauvais : stocker l'état dans la mémoire du processus
cache_local = {}  # module-level, pas thread-safe, pas partagé entre workers

def get_user(user_id):
    if user_id not in cache_local:
        cache_local[user_id] = User.objects.get(pk=user_id)
    return cache_local[user_id]

# Bon : stocker l'état dans un service partagé (Redis, DB)
from django.core.cache import cache

def get_user(user_id):
    user = cache.get(f'user:{user_id}')
    if user is None:
        user = User.objects.get(pk=user_id)
        cache.set(f'user:{user_id}', user, timeout=300)
    return user
```

---

### Facteur VII : Port Binding (Liaison de port)

**Principe :** Exposer les services via une liaison de port.

L'application est autonome et écoute sur un port. Elle n'a pas besoin d'un serveur web externe pour fonctionner.

```bash
# Django+Gunicorn expose le port 8000
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

---

### Facteur VIII : Concurrency (Concurrence)

**Principe :** Scaler via le modèle de processus.

```
                   Load Balancer
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
     Gunicorn(1)   Gunicorn(2)  Gunicorn(3)
     4 workers     4 workers    4 workers
```

Au lieu d'avoir un seul processus énorme, on scale horizontalement en ajoutant des processus/machines.

---

### Facteur IX : Disposability (Jetabilité)

**Principe :** Maximiser la robustesse avec des démarrages rapides et des arrêts gracieux.

```python
# gunicorn.conf.py
graceful_timeout = 30   # attendre 30s avant de forcer l'arrêt
# Gunicorn répond au signal SIGTERM par un arrêt gracieux
```

---

### Facteur X : Dev/Prod Parity (Parité dev/prod)

**Principe :** Garder dev, staging et production aussi similaires que possible.

```bash
# Mauvais : SQLite en dev, PostgreSQL en prod
# Les différences de comportement créent des surprises

# Bon : PostgreSQL partout, via Docker
docker-compose up db   # même base de données en dev
```

---

### Facteur XI : Logs

**Principe :** Traiter les logs comme des flux d'événements.

```python
# L'application écrit sur stdout
import logging
import sys

LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# C'est l'infrastructure (systemd, Docker, ELK) qui collecte et stocke les logs
# Pas l'application elle-même
```

---

### Facteur XII : Admin Processes (Processus d'administration)

**Principe :** Lancer les tâches d'admin comme des processus one-off.

```bash
# Migrations : one-off process
python manage.py migrate

# Créer des fixtures : one-off process
python manage.py loaddata initial_data.json

# Shell Django : one-off process
python manage.py shell

# Ces processus s'exécutent dans le même environnement que l'application
docker-compose exec web python manage.py migrate
```

---

## Facteur III en détail : Variables d'environnement avec Django

### La bibliothèque python-decouple

**python-decouple** lit les variables d'environnement (et les fichiers `.env`). C'est une bibliothèque légère et idiomatique.

```bash
pip install python-decouple
```

```python
# settings.py avec python-decouple
from decouple import config, Csv

# Lecture simple
SECRET_KEY = config('SECRET_KEY')

# Avec valeur par défaut
DEBUG = config('DEBUG', default=False, cast=bool)

# Type casting
PORT = config('PORT', default=8000, cast=int)

# Liste (séparée par des virgules dans le .env)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())
# .env : ALLOWED_HOSTS=mondomaine.com,www.mondomaine.com

# Valeur optionnelle (None si absente)
SENTRY_DSN = config('SENTRY_DSN', default=None)
```

### La bibliothèque django-environ

Alternative populaire avec plus de fonctionnalités (parsing DATABASE_URL, etc.) :

```bash
pip install django-environ
```

```python
# settings.py avec django-environ
import environ

env = environ.Env(
    # Valeurs par défaut et types
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost']),
)

# Lire le fichier .env (optionnel)
environ.Env.read_env('.env')

# Lecture des variables
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# DATABASE_URL auto-parsé !
DATABASES = {'default': env.db('DATABASE_URL')}
# DATABASE_URL=postgresql://user:pass@localhost:5432/mydb

# CACHE_URL auto-parsé
CACHES = {'default': env.cache('REDIS_URL')}
# REDIS_URL=redis://localhost:6379/0

# EMAIL_URL auto-parsé
EMAIL_CONFIG = env.email('EMAIL_URL')
# EMAIL_URL=smtp://user:pass@smtp.gmail.com:587
vars().update(EMAIL_CONFIG)
```

---

## Fichiers d'environnement

### .env — le fichier local (jamais commité)

```bash
# .env — local uniquement, dans .gitignore

# Django
DEBUG=True
SECRET_KEY=django-insecure-dev-only-key-abc123xyz
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données
DATABASE_URL=postgresql://monprojet:devpass@localhost:5432/monprojet_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Email (Mailtrap pour le dev)
EMAIL_URL=smtp://user:pass@sandbox.smtp.mailtrap.io:2525

# Services tiers
STRIPE_SECRET_KEY=sk_test_...
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

### .env.example — le modèle (commité)

```bash
# .env.example — à commiter dans le repo
# Ce fichier documente toutes les variables nécessaires
# NE PAS mettre de vraies valeurs ici

DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com

DATABASE_URL=postgresql://user:password@localhost:5432/dbname

REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_URL=smtp://user:pass@smtp.example.com:587

# AWS (pour S3)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Sentry
SENTRY_DSN=
```

```bash
# .gitignore — toujours inclure
.env
.env.local
.env.production
*.env
!.env.example  # mais garder .env.example
```

---

## Découpage des fichiers settings

Pour une application sérieuse, on sépare les settings selon l'environnement.

### Structure recommandée

```
config/
├── settings/
│   ├── __init__.py      # vide ou exporte base
│   ├── base.py          # paramètres communs à tous les environnements
│   ├── local.py         # développement local
│   ├── production.py    # production
│   └── test.py          # tests automatisés
├── urls.py
└── wsgi.py
```

### base.py — paramètres communs

```python
# config/settings/base.py
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Sécurité
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=lambda v: [s.strip() for s in v.split(',')])

# Applications Django
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'django_celery_beat',
]

LOCAL_APPS = [
    'apps.users',
    'apps.products',
    'apps.orders',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # doit être en 2e position
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Internationalisation
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

# Fichiers statiques
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Fichiers media
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Auth
AUTH_USER_MODEL = 'users.User'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging commun
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

### local.py — développement

```python
# config/settings/local.py
from .base import *
from decouple import config

DEBUG = True

# Base de données locale (PostgreSQL ou SQLite)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='monprojet_dev'),
        'USER': config('POSTGRES_USER', default='monprojet'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='devpass'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Cache en mémoire (simple pour le dev)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Email : afficher dans la console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Django Debug Toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
INTERNAL_IPS = ['127.0.0.1']

# Logs détaillés en dev
LOGGING['loggers']['django']['level'] = 'DEBUG'

# CORS permissif en dev
CORS_ALLOW_ALL_ORIGINS = True
```

### production.py — production

```python
# config/settings/production.py
from .base import *
from decouple import config
import dj_database_url

DEBUG = False

# Sécurité
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

# Base de données via DATABASE_URL
DATABASE_URL = config('DATABASE_URL')
DATABASES = {
    'default': dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,           # connexions persistantes
        conn_health_checks=True,
    )
}

# Cache Redis
REDIS_URL = config('REDIS_URL')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 100},
        },
        'TIMEOUT': 300,
    }
}

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Sécurité HTTP
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000         # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Fichiers statiques avec WhiteNoise
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Email en production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@mondomaine.com')

# Sentry (monitoring des erreurs)
SENTRY_DSN = config('SENTRY_DSN', default=None)
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,  # 10% des transactions
        send_default_pii=False,
    )

# CORS en production
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)
```

### test.py — tests

```python
# config/settings/test.py
from .base import *

DEBUG = False

SECRET_KEY = 'test-secret-key-not-for-production'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # SQLite en mémoire, très rapide
    }
}

# Désactiver les migrations (plus rapide)
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Cache dummy
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Email
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Pas de Celery en test : exécution synchrone
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Mot de passe hashé rapidement (accélère les tests)
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
```

### Choisir le bon settings

```bash
# Variable DJANGO_SETTINGS_MODULE
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py runserver

# En production
export DJANGO_SETTINGS_MODULE=config.settings.production
gunicorn config.wsgi:application

# Pour les tests
export DJANGO_SETTINGS_MODULE=config.settings.test
python manage.py test

# Avec pytest
# pytest.ini ou setup.cfg
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.test
```

---

## Ne jamais commiter de secrets

### Ce qui ne doit jamais être dans le repo

```python
# MAUVAIS — secrets dans le code
SECRET_KEY = "ma-clé-secrète-hardcodée"
DATABASES = {'default': {'PASSWORD': 'motdepasse123'}}
STRIPE_KEY = "sk_live_abc123"
```

### Comment générer une SECRET_KEY Django sécurisée

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Sortie : quelque chose comme "w*7v2$pk(z9!j1..."

# Ou avec secrets (Python stdlib)
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### Outils pour auditer les secrets

```bash
# git-secrets : prévient les commits accidentels de secrets
git secrets --install
git secrets --register-aws  # patterns AWS

# trufflehog : scanner un repo pour trouver des secrets
pip install trufflehog
trufflehog git https://github.com/user/monprojet

# detect-secrets : audit des secrets dans le code
pip install detect-secrets
detect-secrets scan > .secrets.baseline
```

---

## Parsing de DATABASE_URL

Le format `DATABASE_URL` est une URL complète qui encode toutes les infos de connexion. C'est le standard 12-factor pour les bases de données.

```
postgresql://utilisateur:motdepasse@hote:5432/nomdb?sslmode=require
```

```bash
pip install dj-database-url
```

```python
import dj_database_url

# Parsing simple
DATABASE_URL = "postgresql://user:pass@localhost:5432/mydb"
DATABASES = {'default': dj_database_url.parse(DATABASE_URL)}

# Avec options de connexion
DATABASES = {
    'default': dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,        # connexions persistantes (0 = nouvelle connexion à chaque requête)
        conn_health_checks=True, # vérifier que la connexion est vivante
        ssl_require=True,        # forcer SSL
    )
}

# Ou via config() directement depuis l'env
import os
DATABASES = {'default': dj_database_url.config(default=os.environ['DATABASE_URL'])}
```

**Formats d'URL supportés :**
```
# PostgreSQL
postgresql://user:pass@host:5432/db
postgres://user:pass@host/db

# MySQL
mysql://user:pass@host:3306/db

# SQLite
sqlite:///path/to/db.sqlite3
sqlite://:memory:
```

---

## Gestion des secrets en production

### Option 1 : Variables d'environnement (simple, standard 12-factor)

Définir les variables directement dans l'environnement du processus :

```bash
# systemd : EnvironmentFile dans le service
EnvironmentFile=/etc/monprojet/env

# Docker : fichier .env ou --env-file
docker run --env-file .env.production myapp

# Shell
export SECRET_KEY="valeur-secrète"
gunicorn config.wsgi:application
```

### Option 2 : AWS Secrets Manager

```python
# Charger les secrets depuis AWS Secrets Manager
import boto3
import json
from functools import lru_cache

@lru_cache(maxsize=None)
def get_secret(secret_name: str) -> dict:
    client = boto3.client('secretsmanager', region_name='eu-west-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Dans settings.py
secrets = get_secret('monprojet/production')
SECRET_KEY = secrets['SECRET_KEY']
DB_PASSWORD = secrets['DB_PASSWORD']
```

### Option 3 : HashiCorp Vault

```python
import hvac

client = hvac.Client(url='https://vault.monentreprise.com')
client.auth.approle.login(role_id=ROLE_ID, secret_id=SECRET_ID)

secret = client.secrets.kv.v2.read_secret_version(
    path='monprojet/production',
    mount_point='secret'
)
values = secret['data']['data']
```

### Option 4 : Google Cloud Secret Manager

```python
from google.cloud import secretmanager

def access_secret(secret_id: str, version: str = "latest") -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/mon-projet/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

---

## Récapitulatif : les bonnes pratiques de configuration

1. **Jamais de secrets dans le code** — utilisez des variables d'environnement
2. **Utilisez python-decouple ou django-environ** — pas `os.environ` directement (moins robuste)
3. **Commiter `.env.example`** mais jamais `.env`
4. **Séparer les settings** en base/local/production/test
5. **`DEBUG=False` en production** — toujours
6. **Valeurs par défaut sûres** — default=False pour DEBUG, pas de default pour SECRET_KEY
7. **Valider au démarrage** — django.core.checks peut valider la config
8. **Utiliser `DATABASE_URL`** — format standard, facile à changer de serveur de DB
9. **Rotations régulières des secrets** — surtout après une fuite potentielle
10. **Audit des secrets** — utiliser trufflehog ou detect-secrets dans la CI
