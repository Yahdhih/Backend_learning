# Jour 51 — Durcissement de sécurité (Hardening)
📅 16 août 2026 · Module : Sécurité

---

## Qu'est-ce que le hardening ?

Réduire la **surface d'attaque** d'une application : désactiver ce qui est inutile, limiter les privilèges, supprimer les defaults dangereux.

---

## Headers HTTP : configuration complète

```python
# settings.py — sécurité maximale
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000           # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_NAME = "__Host-sessionid"  # préfixe __Host- = plus sécurisé
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_USE_SESSIONS = True   # stocker CSRF token en session, pas cookie
```

---

## Désactiver l'admin Django en prod

```python
# Si tu n'as pas besoin de l'admin :
INSTALLED_APPS = [
    # "django.contrib.admin",  # supprimer
    ...
]

# Sinon, changer l'URL par défaut
# urls.py
urlpatterns = [
    path("super-secret-admin-url/", admin.site.urls),  # pas /admin/
]
```

---

## Limiter les informations exposées

```python
# Ne jamais afficher les détails d'erreur en prod
DEBUG = False

# Handler d'erreurs DRF — réponse générique
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and response.status_code == 500:
        # Logguer mais ne pas exposer
        import logging
        logging.error(str(exc))
        response.data = {"error": "Erreur interne du serveur"}
    return response

# settings.py
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "monapp.exceptions.custom_exception_handler"
}
```

---

## Protection contre le timing attack

```python
# MAUVAIS — vulnerable au timing attack
if user.password == password_hash:
    ...

# BON — comparaison en temps constant
import hmac
if hmac.compare_digest(user.password, password_hash):
    ...

# Django le fait automatiquement dans check_password()
user.check_password(raw_password)  # utilise hmac.compare_digest en interne
```

---

## Validation stricte des entrées

```python
# serializers.py
class ArticleSerializer(serializers.ModelSerializer):
    titre = serializers.CharField(
        max_length=200,
        min_length=5,
        strip_whitespace=True,
    )
    contenu = serializers.CharField(max_length=50000)

    def validate_titre(self, valeur):
        # Refuser les caractères potentiellement dangereux
        import re
        if re.search(r"[<>\"']", valeur):
            raise serializers.ValidationError("Caractères non autorisés")
        return valeur

    def validate(self, data):
        # Validation cross-field
        if data.get("date_fin") and data["date_fin"] < data["date_debut"]:
            raise serializers.ValidationError("date_fin doit être après date_debut")
        return data
```

---

## Limiter les méthodes HTTP

```python
from django.views.decorators.http import require_http_methods, require_POST

@require_POST   # accepte seulement POST
def creer_article(request):
    ...

@require_http_methods(["GET", "POST"])
def ma_vue(request):
    ...

# DRF — limiter les actions du ViewSet
class ArticleViewSet(ModelViewSet):
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
    # retirer "put" si on ne veut que PATCH :
    # http_method_names = ["get", "post", "patch", "delete"]
```

---

## Audit des dépendances

```bash
# Scanner les vulnérabilités connues
pip install pip-audit
pip-audit

# Ou avec safety
pip install safety
safety check

# Mettre à jour les dépendances
pip list --outdated
pip install --upgrade django djangorestframework
```

---

## Variables d'environnement : checklist

```bash
# Ne jamais mettre ces valeurs dans le code :
DJANGO_SECRET_KEY=...
DATABASE_URL=...
REDIS_URL=...
EMAIL_HOST_PASSWORD=...
AWS_SECRET_ACCESS_KEY=...
STRIPE_SECRET_KEY=...
SENTRY_DSN=...

# Vérifier que .env n'est pas dans git
echo ".env" >> .gitignore
git rm --cached .env  # si déjà trackée

# Vérifier les secrets déjà commis
git log --all -S "password" --source --all
```
