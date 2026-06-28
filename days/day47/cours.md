# Jour 47 — Django Security Checklist
📅 12 août 2026 · Module : Sécurité

---

## La commande de vérification Django

```bash
python manage.py check --deploy
```

Django vérifie automatiquement des dizaines de points de sécurité. Corrige **toutes** les erreurs avant de mettre en production.

---

## Les settings de production essentiels

```python
# ❌ Jamais en prod
DEBUG = False

# ✅ Toujours défini
SECRET_KEY = os.environ["SECRET_KEY"]  # depuis les variables d'env, jamais en dur
ALLOWED_HOSTS = ["monsite.com", "www.monsite.com"]  # pas ["*"] en prod

# HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000          # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = True            # cookie session via HTTPS seulement
CSRF_COOKIE_SECURE = True               # cookie CSRF via HTTPS seulement
SESSION_COOKIE_HTTPONLY = True          # pas accessible via JavaScript
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"      # pas envoyé dans les requêtes cross-site

# Headers
SECURE_CONTENT_TYPE_NOSNIFF = True      # X-Content-Type-Options: nosniff
X_FRAME_OPTIONS = "DENY"               # pas d'embed dans des iframes
SECURE_BROWSER_XSS_FILTER = True       # X-XSS-Protection (vieux navigateurs)
```

---

## Gestion des secrets

```python
# ❌ JAMAIS ça
SECRET_KEY = "django-insecure-abc123"
DATABASE_URL = "postgresql://user:motdepasse@localhost/db"

# ✅ Toujours via variables d'environnement
import os
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DATABASE_URL = os.environ["DATABASE_URL"]

# Ou avec python-decouple
from decouple import config
SECRET_KEY = config("DJANGO_SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
```

Génère une vraie SECRET_KEY :
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Mots de passe : hashers Django

```python
# settings.py — ordre de préférence
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",   # recommandé
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",   # défaut
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

# Validation des mots de passe
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

---

## CORS (Cross-Origin Resource Sharing)

```bash
pip install django-cors-headers
```

```python
INSTALLED_APPS = ["corsheaders", ...]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware", ...other...]

# ❌ Trop permissif
CORS_ALLOW_ALL_ORIGINS = True

# ✅ Restrictif
CORS_ALLOWED_ORIGINS = [
    "https://monapp.com",
    "https://www.monapp.com",
]
CORS_ALLOW_CREDENTIALS = True  # si tu utilises des cookies
```

---

## Fichiers uploadés : valider

```python
from django.core.exceptions import ValidationError

def valider_fichier(valeur):
    # Taille max : 5 MB
    if valeur.size > 5 * 1024 * 1024:
        raise ValidationError("Fichier trop volumineux (max 5MB)")

    # Types autorisés (vérifier le MIME type, pas juste l'extension)
    types_autorises = ["image/jpeg", "image/png", "image/webp"]
    if valeur.content_type not in types_autorises:
        raise ValidationError(f"Type non autorisé : {valeur.content_type}")

class Document(models.Model):
    fichier = models.FileField(upload_to="uploads/", validators=[valider_fichier])
```

---

## Rate limiting sur les vues sensibles

```python
# django-ratelimit
pip install django-ratelimit

from ratelimit.decorators import ratelimit

@ratelimit(key="ip", rate="5/m", block=True)
def login_view(request):
    ...
```

---

## Logging des événements de sécurité

```python
LOGGING = {
    "version": 1,
    "handlers": {
        "security": {
            "class": "logging.FileHandler",
            "filename": "security.log",
        }
    },
    "loggers": {
        "django.security": {
            "handlers": ["security"],
            "level": "INFO",
            "propagate": False,
        }
    }
}
```

---

## Checklist résumée

```
☐ DEBUG = False
☐ SECRET_KEY depuis les variables d'env
☐ ALLOWED_HOSTS défini strictement
☐ HTTPS activé (SECURE_SSL_REDIRECT)
☐ HSTS configuré
☐ Cookies sécurisés (SECURE + HTTPONLY + SAMESITE)
☐ python manage.py check --deploy → 0 erreur
☐ Mots de passe : Argon2 ou bcrypt
☐ CORS restrictif
☐ Fichiers uploadés validés
☐ Rate limiting sur login/register/reset
☐ Logs de sécurité activés
☐ Dépendances à jour (pip audit)
☐ pas de secrets dans le code ou git
```
