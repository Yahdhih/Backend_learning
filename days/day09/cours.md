# Jour 09 — Headers HTTP : Content-Type, Accept, Authorization, CORS, Cookie (5 juillet 2026)

> **Durée estimée :** 30 minutes de lecture  
> **Prérequis :** Jour 08 (méthodes HTTP, codes de statut)  
> **Objectif :** Maîtriser les headers HTTP les plus importants et comprendre leur rôle dans la communication client/serveur

---

## 1. Qu'est-ce qu'un header HTTP ?

Les headers HTTP sont des **métadonnées** qui accompagnent chaque requête ou réponse. Ils voyagent dans l'entête du message HTTP, avant le corps (body).

Structure d'un message HTTP avec headers :
```
GET /api/users/42 HTTP/1.1         ← Ligne de requête
Host: api.exemple.com              ← ┐
Accept: application/json           ← │ Headers (un par ligne)
Authorization: Bearer eyJ...       ← │ Format : Nom: Valeur
User-Agent: MonApp/1.0             ← ┘
                                   ← Ligne vide (séparateur obligatoire)
                                   ← Body (vide pour GET)
```

Les headers sont **insensibles à la casse** (`Content-Type` = `content-type`), mais la convention est d'utiliser le "Title-Case".

### Catégories de headers

| Catégorie           | Direction       | Exemples |
|---------------------|-----------------|----------|
| Headers de requête  | Client → Serveur| Accept, Authorization, Cookie, User-Agent |
| Headers de réponse  | Serveur → Client| Set-Cookie, WWW-Authenticate, Location |
| Headers généraux    | Les deux        | Cache-Control, Connection, Date |
| Headers d'entité    | Les deux        | Content-Type, Content-Length, ETag |

---

## 2. Content-Type et Content-Négociation

### 2.1 Content-Type — Quel format est le body ?

`Content-Type` annonce le **format** du body. Sans ce header, le destinataire ne sait pas comment interpréter les octets reçus.

```
POST /api/users HTTP/1.1
Content-Type: application/json

{"nom": "Alice"}
```

Format : `type/sous-type; paramètres`

| Content-Type                     | Quand l'utiliser |
|----------------------------------|------------------|
| `application/json`               | APIs REST, données structurées |
| `application/x-www-form-urlencoded` | Formulaires HTML classiques |
| `multipart/form-data`            | Upload de fichiers |
| `text/html; charset=utf-8`       | Pages web |
| `text/plain; charset=utf-8`      | Texte brut |
| `application/xml`                | APIs SOAP, données XML |
| `image/jpeg`, `image/png`        | Images |
| `application/pdf`                | PDF |
| `application/octet-stream`       | Données binaires génériques |

**Le paramètre `charset` :**
```
Content-Type: text/html; charset=utf-8
              ─────────  ────────────
              type       paramètre d'encodage
```

### 2.2 Accept — Quel format le client veut recevoir ?

Le client annonce au serveur dans quel format il préfère la réponse :

```
GET /api/users/42 HTTP/1.1
Accept: application/json, text/html;q=0.9, */*;q=0.8
```

Le paramètre `q` est le **facteur de qualité** (0 à 1) — la préférence du client :
- `application/json` → q=1.0 (préféré, valeur par défaut)
- `text/html;q=0.9` → deuxième choix
- `*/*;q=0.8` → accepte n'importe quoi en dernier recours

**Négociation de contenu côté serveur :**
```python
# Exemple Django
def ma_vue(request):
    donnees = {"utilisateur": "Alice", "age": 30}
    
    accept = request.META.get("HTTP_ACCEPT", "application/json")
    
    if "text/html" in accept:
        return render(request, "profil.html", donnees)
    else:
        return JsonResponse(donnees)
```

Si le serveur ne peut pas fournir le format demandé → `406 Not Acceptable`.

### 2.3 Content-Language et Accept-Language

```
Accept-Language: fr-FR, fr;q=0.9, en;q=0.8
Content-Language: fr
```

Même mécanisme pour la langue. Utile pour les APIs multilingues.

---

## 3. Authorization — Authentification HTTP

### 3.1 Le mécanisme général

```
1. Client envoie une requête sans credentials
   GET /api/profil HTTP/1.1

2. Serveur répond 401 avec le schéma d'auth supporté
   HTTP/1.1 401 Unauthorized
   WWW-Authenticate: Bearer realm="API"

3. Client renvoie avec ses credentials
   GET /api/profil HTTP/1.1
   Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...
```

Le header `WWW-Authenticate` indique au client **comment s'authentifier**.

### 3.2 Basic Authentication

Format : `Authorization: Basic base64(username:password)`

```python
import base64

# Encodage
username = "alice"
password = "motdepasse123"
credentials = f"{username}:{password}"
encoded = base64.b64encode(credentials.encode()).decode()
header = f"Basic {encoded}"
print(header)
# Basic YWxpY2U6bW90ZGVwYXNzZTEyMw==

# Décodage
decoded = base64.b64decode("YWxpY2U6bW90ZGVwYXNzZTEyMw==").decode()
print(decoded)  # alice:motdepasse123
```

**Attention :** Basic Auth encode en base64 (pas de chiffrement !). Utilisez **toujours** HTTPS avec Basic Auth.

En Django REST Framework :
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
    ]
}
```

### 3.3 Bearer Token (JWT)

Format : `Authorization: Bearer <token>`

```
GET /api/profil HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQyLCJleHAiOjE3NTE2NzAwMDB9.signature
```

Un JWT (JSON Web Token) est composé de 3 parties encodées en base64, séparées par des points :
```
header.payload.signature
  ↑       ↑       ↑
algo   données  vérification
```

```python
import base64
import json

jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQyLCJleHAiOjE3NTE2NzAwMDB9.signature"

parties = jwt_token.split(".")
# Décoder le payload (attention : pas de vérification de signature ici !)
payload_b64 = parties[1]
# Ajouter le padding base64 si nécessaire
payload_b64 += "=" * (4 - len(payload_b64) % 4)
payload = json.loads(base64.b64decode(payload_b64).decode())
print(payload)  # {'userId': 42, 'exp': 1751670000}
```

### 3.4 API Key

Moins standardisé, souvent dans un header custom :
```
GET /api/data HTTP/1.1
X-API-Key: sk_live_abc123def456
```

Ou parfois en query parameter (déconseillé — les URLs sont loggées) :
```
GET /api/data?api_key=sk_live_abc123def456
```

### 3.5 Proxy-Authorization

Même mécanisme mais pour les proxies. Le proxy retourne `407 Proxy Authentication Required` et le client répond avec `Proxy-Authorization`.

---

## 4. CORS — Cross-Origin Resource Sharing

### 4.1 Pourquoi CORS existe-t-il ?

Les navigateurs web appliquent la **Same-Origin Policy (SOP)** : une page web ne peut faire des requêtes AJAX qu'**vers son propre domaine**.

```
Exemple de VIOLATION de Same-Origin Policy (bloquée par le navigateur) :
  - Page web : https://monapp.com
  - Requête AJAX vers : https://api.autredomaine.com/data
  ↑ BLOQUÉ ! Origines différentes.

CORS permet au serveur d'indiquer explicitement quels autres domaines
sont autorisés à faire des requêtes.
```

Une "origine" = protocole + domaine + port :
```
https://exemple.com:443  ≠  http://exemple.com:80   (protocole différent)
https://exemple.com:443  ≠  https://api.exemple.com  (sous-domaine différent)
https://exemple.com:443  ≠  https://exemple.com:8080 (port différent)
https://exemple.com      =  https://exemple.com:443  (port 443 = HTTPS par défaut)
```

### 4.2 Requête CORS simple vs Preflight

**Requête simple** (pas de preflight) :
- Méthode : GET, POST, ou HEAD
- Headers : seulement les headers standards simples (Accept, Content-Type avec valeur simple)
- Content-Type : seulement `text/plain`, `multipart/form-data`, ou `application/x-www-form-urlencoded`

Le navigateur envoie la requête directement avec le header `Origin` :
```
GET /api/data HTTP/1.1
Origin: https://monapp.com
```

Le serveur répond avec :
```
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://monapp.com
```

**Requête preflight** (pour les requêtes non-simples) :
Avant d'envoyer la vraie requête, le navigateur envoie automatiquement une requête OPTIONS :

```
OPTIONS /api/users HTTP/1.1
Origin: https://monapp.com
Access-Control-Request-Method: PUT
Access-Control-Request-Headers: Authorization, Content-Type
```

Le serveur répond au preflight :
```
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://monapp.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: Authorization, Content-Type
Access-Control-Max-Age: 86400
```

Si le preflight est accepté, le navigateur envoie la vraie requête.

### 4.3 Les headers CORS en détail

**Headers de réponse (ce que le serveur renvoie) :**

| Header                         | Description | Exemple |
|--------------------------------|-------------|---------|
| `Access-Control-Allow-Origin`  | Origines autorisées | `https://monapp.com` ou `*` |
| `Access-Control-Allow-Methods` | Méthodes autorisées | `GET, POST, PUT` |
| `Access-Control-Allow-Headers` | Headers autorisés dans la requête | `Authorization, Content-Type` |
| `Access-Control-Max-Age`       | Durée de cache du preflight (secondes) | `86400` (1 jour) |
| `Access-Control-Allow-Credentials` | Autoriser cookies/auth | `true` |
| `Access-Control-Expose-Headers` | Headers exposés au JS | `X-Custom-Header` |

**`*` (wildcard) et credentials :**
```
# ATTENTION : Vous ne pouvez PAS combiner ces deux headers !
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
# → ERREUR ! Le navigateur refusera.
# Avec credentials, vous devez spécifier l'origine exacte.
```

### 4.4 CORS en Django

```python
# settings.py — avec django-cors-headers
INSTALLED_APPS = [
    ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Doit être en premier !
    'django.middleware.common.CommonMiddleware',
    ...
]

# Permettre seulement votre frontend
CORS_ALLOWED_ORIGINS = [
    "https://monapp.com",
    "http://localhost:3000",  # En développement
]

# Ou laisser passer tout le monde (DANGEREUX en production !)
# CORS_ALLOW_ALL_ORIGINS = True

# Autoriser les credentials (cookies, Authorization header)
CORS_ALLOW_CREDENTIALS = True

# Headers autorisés dans les requêtes
CORS_ALLOW_HEADERS = [
    "authorization",
    "content-type",
    "x-requested-with",
]
```

### 4.5 Erreur CORS courante — Diagnostic

```
Access to XMLHttpRequest at 'https://api.exemple.com/data' from origin
'https://monapp.com' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**Ce que ça veut dire :** Le serveur n'a pas renvoyé le header `Access-Control-Allow-Origin`.  
**Ce que ça ne veut pas dire :** Ce n'est pas une erreur réseau — la requête a bien atteint le serveur, mais le **navigateur** bloque la réponse.

Astuce de debug : Ouvrez l'onglet Network dans les DevTools → regardez si la réponse a le header `Access-Control-Allow-Origin`.

---

## 5. Cookie — Gestion de session

### 5.1 Le cycle de vie d'un cookie

```
1. Serveur → Client (Set-Cookie)
   HTTP/1.1 200 OK
   Set-Cookie: session_id=abc123; HttpOnly; Secure; SameSite=Strict; Max-Age=3600

2. Client → Serveur (Cookie)
   GET /api/profil HTTP/1.1
   Cookie: session_id=abc123

3. Client stocke le cookie et le renvoie automatiquement à chaque requête
   vers le même domaine
```

### 5.2 Attributs de Set-Cookie

```
Set-Cookie: nom=valeur; attributs
```

| Attribut          | Description |
|-------------------|-------------|
| `Domain=.exemple.com` | Domaine où le cookie est envoyé (y compris sous-domaines si `.`) |
| `Path=/api`       | Chemin où le cookie est envoyé |
| `Max-Age=3600`    | Durée de vie en secondes (préféré à Expires) |
| `Expires=date`    | Date d'expiration absolue |
| `HttpOnly`        | JavaScript **ne peut pas** lire ce cookie (protection XSS) |
| `Secure`          | Cookie envoyé seulement en HTTPS |
| `SameSite=Strict` | Cookie jamais envoyé dans les requêtes cross-site |
| `SameSite=Lax`    | Cookie envoyé en navigation top-level (valeur par défaut) |
| `SameSite=None`   | Cookie envoyé en cross-site (requiert Secure) |

### 5.3 HttpOnly — Protection contre le vol de session

```javascript
// Sans HttpOnly : JavaScript peut lire le cookie
document.cookie  // → "session_id=abc123"
// Un script malveillant injecté via XSS peut voler la session !

// Avec HttpOnly : JavaScript ne peut PAS lire ce cookie
document.cookie  // → "" (le cookie est là mais invisible au JS)
```

Toujours mettre `HttpOnly` sur les cookies de session !

### 5.4 SameSite — Protection contre le CSRF

CSRF (Cross-Site Request Forgery) : un site malveillant fait effectuer des requêtes à votre nom en exploitant le fait que les cookies sont envoyés automatiquement.

```
Scénario d'attaque sans SameSite :
1. Vous êtes connecté sur banque.com (cookie de session actif)
2. Vous visitez site-malveillant.com
3. Ce site contient : <img src="https://banque.com/virement?vers=pirate&montant=1000">
4. Votre navigateur fait GET /virement... ET envoie automatiquement votre cookie !
5. La banque croit que vous avez fait cette requête → virement effectué

Avec SameSite=Strict :
→ Le cookie n'est PAS envoyé pour les requêtes depuis site-malveillant.com
→ Attaque bloquée !
```

### 5.5 Cookies en Django

```python
# views.py
def connexion(request):
    # Définir un cookie
    reponse = HttpResponse("Connecté !")
    reponse.set_cookie(
        key="session_id",
        value="abc123",
        max_age=3600,      # 1 heure
        httponly=True,
        secure=True,       # Seulement en HTTPS
        samesite="Lax"     # Protection CSRF
    )
    return reponse

def profil(request):
    # Lire un cookie
    session_id = request.COOKIES.get("session_id")
    if not session_id:
        return HttpResponse("Non connecté", status=401)
    return HttpResponse(f"Bonjour, session: {session_id}")

def deconnexion(request):
    # Supprimer un cookie (en mettant Max-Age=0)
    reponse = HttpResponse("Déconnecté")
    reponse.delete_cookie("session_id")
    return reponse
```

---

## 6. Cache-Control, ETag et Last-Modified

### 6.1 Cache-Control — Politique de mise en cache

Le header `Cache-Control` contrôle comment les réponses sont mises en cache par les navigateurs et les proxies.

**Dans les réponses :**
```
Cache-Control: max-age=3600             → En cache pendant 1 heure
Cache-Control: no-cache                 → Toujours vérifier au serveur avant d'utiliser le cache
Cache-Control: no-store                 → Ne jamais mettre en cache
Cache-Control: private                  → Cache uniquement dans le navigateur (pas les proxies)
Cache-Control: public                   → Cache dans navigateurs ET proxies
Cache-Control: must-revalidate          → Vérifier le cache expiré avant d'utiliser
Cache-Control: max-age=3600, public     → Combinaison de directives
```

**Dans les requêtes :**
```
Cache-Control: no-cache    → Ne pas utiliser le cache — aller au serveur
Cache-Control: max-age=0   → Identique à no-cache
```

### 6.2 ETag — Identifiant de version d'une ressource

Un ETag est un **identifiant unique** qui représente la version actuelle d'une ressource.

```
1. Première requête :
   GET /api/articles/42 HTTP/1.1

   HTTP/1.1 200 OK
   ETag: "abc123def456"
   Content-Type: application/json
   {"titre": "Mon article", ...}

2. Requêtes suivantes — le client envoie l'ETag qu'il a :
   GET /api/articles/42 HTTP/1.1
   If-None-Match: "abc123def456"

3a. Si la ressource N'A PAS changé :
    HTTP/1.1 304 Not Modified
    ETag: "abc123def456"
    (pas de body → économie de bande passante !)

3b. Si la ressource A changé :
    HTTP/1.1 200 OK
    ETag: "xyz789"
    {"titre": "Titre modifié", ...}
```

### 6.3 Last-Modified — Date de dernière modification

Alternative à ETag basée sur la date :

```
1. Réponse initiale :
   HTTP/1.1 200 OK
   Last-Modified: Sat, 04 Jul 2026 10:00:00 GMT

2. Requête suivante :
   GET /article/42 HTTP/1.1
   If-Modified-Since: Sat, 04 Jul 2026 10:00:00 GMT

3. Réponse si non modifié :
   HTTP/1.1 304 Not Modified
```

**ETag vs Last-Modified :**
- ETag : plus précis (détecte les changements dans la même seconde)
- Last-Modified : plus simple à générer (timestamp de la BDD)
- En pratique : utilisez les deux ensemble

### 6.4 Exemple Django — Réponses avec cache

```python
from django.views.decorators.http import condition
from django.utils.http import http_date
import hashlib
import json

def etag_article(request, article_id):
    """Calcule l'ETag d'un article."""
    from .models import Article
    article = Article.objects.get(id=article_id)
    contenu = json.dumps({"titre": article.titre, "modifie": str(article.date_modification)})
    return hashlib.md5(contenu.encode()).hexdigest()

def last_modified_article(request, article_id):
    """Retourne la date de dernière modification."""
    from .models import Article
    article = Article.objects.get(id=article_id)
    return article.date_modification

@condition(etag_func=etag_article, last_modified_func=last_modified_article)
def vue_article(request, article_id):
    from .models import Article
    article = Article.objects.get(id=article_id)
    reponse = JsonResponse({"titre": article.titre, "contenu": article.contenu})
    reponse["Cache-Control"] = "public, max-age=300"
    return reponse
```

---

## 7. Autres headers importants

### 7.1 Host — Obligatoire en HTTP/1.1

```
GET /index.html HTTP/1.1
Host: www.exemple.com
```

Permet à un serveur d'héberger plusieurs sites sur la même IP (Virtual Hosting).

### 7.2 User-Agent — Identification du client

```
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
User-Agent: python-urllib/3.11
User-Agent: MonApplication/2.1 (backend-learning; contact@exemple.com)
```

### 7.3 X-Forwarded-For — IP réelle derrière un proxy

```
# Nginx (reverse proxy) ajoute :
X-Forwarded-For: 203.0.113.42, 10.0.0.1
                 ↑ IP réelle    ↑ IP du proxy
```

En Django :
```python
# settings.py
USE_X_FORWARDED_HOST = True

# views.py
ip_client = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
# ou plus simplement si REMOTE_ADDR est fiable :
ip_client = request.META["REMOTE_ADDR"]
```

### 7.4 Vary — Indiquer aux caches que la réponse varie

```
Vary: Accept-Language
```
Indique aux caches qu'il faut maintenir des versions séparées selon la langue.

```
Vary: Accept, Accept-Encoding, Accept-Language
```

---

## 8. Exemples Python — Travailler avec les headers

### 8.1 Envoyer des headers personnalisés avec urllib

```python
import urllib.request
import json
import base64

def requete_avec_auth_bearer(url, token):
    """Requête avec authentification Bearer."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "MonApp/1.0")
    
    with urllib.request.urlopen(req) as r:
        return r.status, dict(r.headers), json.loads(r.read())

def requete_avec_basic_auth(url, username, password):
    """Requête avec Basic Authentication."""
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {credentials}")
    
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())
```

### 8.2 Lire les headers de réponse

```python
import urllib.request

def inspecter_headers(url):
    """Affiche tous les headers de réponse."""
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req) as r:
        print(f"Statut : {r.status}")
        print(f"\nHeaders de réponse :")
        for nom, valeur in r.headers.items():
            print(f"  {nom}: {valeur}")

inspecter_headers("https://httpbin.org/get")
```

### 8.3 Négociation de contenu

```python
import urllib.request
import json

def requete_json_ou_html(url, preferer_json=True):
    """Démontre la négociation de contenu via Accept."""
    accept = "application/json" if preferer_json else "text/html, */*;q=0.9"
    
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("Accept-Language", "fr-FR, fr;q=0.9, en;q=0.8")
    
    with urllib.request.urlopen(req) as r:
        content_type = r.headers.get("Content-Type", "")
        body = r.read().decode()
        print(f"Accept envoyé : {accept}")
        print(f"Content-Type reçu : {content_type}")
        return content_type, body
```

### 8.4 Analyser un cookie depuis les headers

```python
def analyser_set_cookie(header_value):
    """Parse un header Set-Cookie."""
    parties = [p.strip() for p in header_value.split(";")]
    
    # Première partie = nom=valeur
    nom, valeur = parties[0].split("=", 1)
    
    attributs = {}
    for partie in parties[1:]:
        if "=" in partie:
            k, v = partie.split("=", 1)
            attributs[k.strip().lower()] = v.strip()
        else:
            attributs[partie.strip().lower()] = True
    
    return {
        "nom": nom,
        "valeur": valeur,
        "attributs": attributs
    }

# Exemple :
cookie_header = "session=abc123; HttpOnly; Secure; SameSite=Strict; Max-Age=3600"
parsed = analyser_set_cookie(cookie_header)
print(parsed)
# {'nom': 'session', 'valeur': 'abc123',
#  'attributs': {'httponly': True, 'secure': True, 'samesite': 'Strict', 'max-age': '3600'}}
```

---

## 9. Headers de sécurité importants

Ces headers renforcent la sécurité des applications web :

| Header | Description |
|--------|-------------|
| `X-Content-Type-Options: nosniff` | Empêche le navigateur de deviner le Content-Type |
| `X-Frame-Options: DENY` | Empêche l'intégration dans des iframes (anti-clickjacking) |
| `Strict-Transport-Security: max-age=31536000` | Force HTTPS (HSTS) |
| `Content-Security-Policy: default-src 'self'` | Contrôle les sources de contenu (anti-XSS) |
| `Referrer-Policy: no-referrer` | Contrôle les infos de referrer envoyées |

En Django, `django.middleware.security.SecurityMiddleware` gère plusieurs de ces headers automatiquement avec les paramètres `SECURE_*` dans `settings.py`.

---

## 10. Résumé

```
Headers de requête importants :
  Host            → Domaine cible (obligatoire en HTTP/1.1)
  Accept          → Format souhaité pour la réponse
  Content-Type    → Format du body envoyé
  Authorization   → Credentials d'authentification
  Cookie          → Cookies stockés pour ce domaine
  User-Agent      → Identification du client

Headers de réponse importants :
  Content-Type    → Format du body renvoyé
  Set-Cookie      → Définit un cookie côté client
  Location        → URL de redirection (3xx) ou ressource créée (201)
  WWW-Authenticate → Comment s'authentifier (avec 401)
  Cache-Control   → Politique de cache
  ETag            → Version de la ressource
  Access-Control-* → Headers CORS

Principes clés :
  Content-Type + Accept → négociation du format des données
  Authorization         → 3 schémas principaux : Basic, Bearer, API Key
  CORS                  → le serveur autorise explicitement les origines croisées
  Cookie                → toujours HttpOnly + Secure + SameSite en production
  Cache-Control + ETag  → éviter des transferts inutiles
```

---

*Prochain cours (Jour 10) : HTTPS et TLS — Comment le chiffrement fonctionne*
