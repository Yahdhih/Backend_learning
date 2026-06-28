# Jour 46 — Rate Limiting et Headers de sécurité
📅 11 août 2026 · Module : Sécurité

---

## Rate Limiting : pourquoi ?

Sans rate limiting, un attaquant peut :
- **Brute-forcer** les mots de passe (10 000 tentatives/minute)
- **Scraper** toute ta DB via l'API
- Lancer une **attaque DDoS** applicative (surcharge le serveur)

---

## Algorithmes de rate limiting

### Token Bucket

```
Capacité : 10 tokens
Recharge : 1 token par seconde

Chaque requête consomme 1 token.
Quand le seau est vide → 429 Too Many Requests.
```

```python
import time

class TokenBucket:
    def __init__(self, capacite, tokens_par_seconde):
        self.capacite = capacite
        self.tokens = capacite
        self.tokens_par_seconde = tokens_par_seconde
        self.dernier_remplissage = time.time()

    def consommer(self, tokens=1):
        now = time.time()
        elapsed = now - self.dernier_remplissage
        self.tokens = min(
            self.capacite,
            self.tokens + elapsed * self.tokens_par_seconde
        )
        self.dernier_remplissage = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False  # rate limited
```

### Sliding Window

Au lieu de compter depuis le début de la fenêtre (qui crée des pics), la fenêtre glisse avec le temps.

```python
from collections import deque

class SlidingWindowRateLimiter:
    def __init__(self, max_requetes, fenetre_secondes):
        self.max_requetes = max_requetes
        self.fenetre = fenetre_secondes
        self.requetes = {}  # {user_id: deque de timestamps}

    def est_autorise(self, user_id):
        now = time.time()
        if user_id not in self.requetes:
            self.requetes[user_id] = deque()

        dq = self.requetes[user_id]
        # Retire les requêtes hors de la fenêtre
        while dq and dq[0] < now - self.fenetre:
            dq.popleft()

        if len(dq) < self.max_requetes:
            dq.append(now)
            return True
        return False
```

---

## Rate Limiting avec DRF Throttling

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",  # utilisateurs anonymes
        "rest_framework.throttling.UserRateThrottle",  # utilisateurs connectés
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",      # 100 requêtes par jour pour les anonymes
        "user": "1000/day",     # 1000 pour les authentifiés
    }
}
```

**Throttle custom par vue :**

```python
from rest_framework.throttling import AnonRateThrottle

class LoginThrottle(AnonRateThrottle):
    rate = "5/min"   # seulement 5 tentatives de login par minute

class LoginView(APIView):
    throttle_classes = [LoginThrottle]
    permission_classes = [AllowAny]

    def post(self, request):
        ...
```

---

## Headers de sécurité HTTP

Ces headers disent au navigateur comment se comporter de façon sécurisée.

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
→ Force HTTPS pour 1 an (HSTS)

Content-Security-Policy: default-src 'self'; script-src 'self' cdn.example.com
→ Bloque XSS en limitant les sources de scripts/images/etc.

X-Frame-Options: DENY
→ Empêche l'embed dans une iframe (clickjacking)

X-Content-Type-Options: nosniff
→ Empêche le navigateur de "deviner" le Content-Type (MIME sniffing)

Referrer-Policy: strict-origin-when-cross-origin
→ Limite les infos dans le header Referer

Permissions-Policy: geolocation=(), camera=(), microphone=()
→ Désactive les APIs sensibles du navigateur
```

---

## Middleware de sécurité Django

```python
# Django's SecurityMiddleware ajoute automatiquement :
# - Strict-Transport-Security (si SECURE_HSTS_SECONDS défini)
# - X-Content-Type-Options: nosniff (si SECURE_CONTENT_TYPE_NOSNIFF = True)
# - X-Frame-Options (selon X_FRAME_OPTIONS)
# - Referrer-Policy (selon SECURE_REFERRER_POLICY)

# Middleware custom pour CSP
class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "frame-ancestors 'none';"
        )
        return response
```

---

## Détecter et bloquer les tentatives répétées

```python
# django-axes : bloque les IPs après N échecs
pip install django-axes

# settings.py
INSTALLED_APPS += ["axes"]
MIDDLEWARE = ["axes.middleware.AxesMiddleware"] + MIDDLEWARE
AUTHENTICATION_BACKENDS = ["axes.backends.AxesStandaloneBackend", ...]
AXES_FAILURE_LIMIT = 5           # bloquer après 5 échecs
AXES_COOLOFF_TIME = 1            # pendant 1 heure
AXES_LOCK_OUT_AT_FAILURE = True
```
