# Exercice Jour 47 — Audit de sécurité Django

## Le settings.py à auditer

Ci-dessous un `settings.py` de production avec **15 problèmes de sécurité**.
Trouve-les tous et propose une correction pour chacun.

```python
# config/settings.py — À AUDITER

SECRET_KEY = "django-insecure-my-dev-key-1234567890"

DEBUG = True

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "myapp",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "myapp_db",
        "USER": "postgres",
        "PASSWORD": "admin",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

AUTH_PASSWORD_VALIDATORS = []

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
    ],
}

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

X_FRAME_OPTIONS = "ALLOWALL"

MEDIA_ROOT = "/tmp/uploads"
MEDIA_URL = "/media/"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST_PASSWORD = "mon-mot-de-passe-email"
```

---

## Ta mission

Pour chaque problème, complète ce tableau dans `notes.md` :

| # | Problème | Risque | Correction |
|---|---------|--------|------------|
| 1 | `SECRET_KEY` hardcodée | ... | ... |
| 2 | ... | ... | ... |
| ... | | | |

---

## Vérification automatique

```bash
# Dans un projet Django réel, lance :
python manage.py check --deploy --settings=config.settings_production
```

Note tous les avertissements et leur signification.

---

## Questions dans `notes.md`

1. Pourquoi `DEBUG = True` en production est-il dangereux ? Que peut voir un attaquant ?
2. Que se passe-t-il si `SECRET_KEY` est compromise ?
3. Pourquoi `CORS_ALLOW_ALL_ORIGINS = True` avec `CORS_ALLOW_CREDENTIALS = True` est-il particulièrement dangereux ?
4. Quelle est la différence entre `SESSION_COOKIE_SECURE` et `SESSION_COOKIE_HTTPONLY` ?
5. Pourquoi `BasicAuthentication` en prod sans HTTPS est-il dangereux ?
