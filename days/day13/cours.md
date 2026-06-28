# Jour 13 — Middleware WSGI : La chaîne de traitements (9 juillet 2026)

---

## Table des matières

1. [Qu'est-ce qu'un middleware ?](#1-quest-ce-quun-middleware)
2. [Le pattern décorateur appliqué à WSGI](#2-le-pattern-décorateur)
3. [Anatomie d'un middleware WSGI](#3-anatomie-dun-middleware-wsgi)
4. [Middleware de logging](#4-middleware-de-logging)
5. [Middleware de timing](#5-middleware-de-timing)
6. [Middleware d'authentification](#6-middleware-dauthentification)
7. [La pile de middlewares : ordre et flux](#7-la-pile-de-middlewares)
8. [Middlewares en Django et Flask](#8-middlewares-en-django-et-flask)
9. [Résumé et bonnes pratiques](#9-résumé)

---

## 1. Qu'est-ce qu'un middleware ?

### La définition

Un **middleware** est un composant logiciel qui se place **entre** le client et l'application principale pour intercepter et modifier les requêtes entrantes et/ou les réponses sortantes.

Le terme vient littéralement de "milieu" (middle) + "logiciel" (ware). C'est du code qui vit *au milieu* du flux de traitement.

### L'analogie du bureau de poste

Imaginez une lettre qui va de Paris à Lyon :

```
Expéditeur → Tri Paris → Camion → Tri Lyon → Facteur → Destinataire
```

Chaque étape peut :
- **Lire** le contenu de la lettre (logging)
- **Modifier** la lettre (ajout de tampon)
- **Retarder** la livraison (rate limiting)
- **Rejeter** la lettre (censure, authentification)
- **Dupliquer** la lettre (copie de sauvegarde)

Un middleware WSGI fonctionne exactement de la même façon, mais avec des requêtes HTTP.

### L'analogie de la cuisine

```
Client
  │
  ▼
┌─────────────────────┐
│  Middleware 1       │  Hôte d'accueil : vérifie la réservation (auth)
│  (Auth)             │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Middleware 2       │  Chef de rang : note l'heure d'arrivée (timing)
│  (Timing)           │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Middleware 3       │  Caméra de surveillance : enregistre tout (logging)
│  (Logging)          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Application        │  Cuisine : prépare le plat (votre logique métier)
│  (Votre code)       │
└─────────────────────┘
```

La requête descend, la réponse remonte. Chaque middleware peut intervenir dans les deux sens.

---

## 2. Le pattern décorateur

### Le décorateur Python classique

```python
# Décorateur classique Python
def log_appel(func):
    def wrapper(*args, **kwargs):
        print(f"Appel de {func.__name__}")
        resultat = func(*args, **kwargs)
        print(f"Retour de {func.__name__}")
        return resultat
    return wrapper

@log_appel
def bonjour(nom):
    return f"Bonjour, {nom} !"

# bonjour est maintenant remplacé par wrapper
# wrapper connait bonjour via la closure
```

### Le middleware WSGI EST un décorateur

Un middleware WSGI applique exactement le même pattern, mais à une application WSGI :

```python
# Middleware WSGI = décorateur pour applications WSGI
def middleware_log(app):
    """
    Prend une app WSGI, retourne une nouvelle app WSGI
    qui logue avant et après.
    """
    def nouvelle_app(environ, start_response):
        print(f"→ Requete entrante : {environ['REQUEST_METHOD']} {environ['PATH_INFO']}")
        resultat = app(environ, start_response)  # appel de l'app originale
        print(f"← Reponse envoyee")
        return resultat
    
    return nouvelle_app  # retourne un nouveau callable WSGI


# Application originale
def mon_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Hello"]

# Application + middleware
app_avec_log = middleware_log(mon_app)
# app_avec_log est maintenant un callable WSGI
# qui log puis appelle mon_app

# Empilement de plusieurs middlewares
from autre_module import middleware_auth, middleware_timing

app_complete = middleware_log(
    middleware_auth(
        middleware_timing(
            mon_app
        )
    )
)
```

### Lecture de l'empilement

Il faut lire l'empilement **de l'intérieur vers l'extérieur** pour la construction, mais les requêtes entrent **par l'extérieur** :

```
Construction :  middleware_log( middleware_auth( middleware_timing( mon_app ) ) )
                ←──────────────────────────────────────────────────────────────
                                    (l'intérieur est enroulé en premier)

Flux requête :  middleware_log → middleware_auth → middleware_timing → mon_app
                ──────────────────────────────────────────────────────────────→

Flux réponse :  middleware_log ← middleware_auth ← middleware_timing ← mon_app
                ←──────────────────────────────────────────────────────────────
```

---

## 3. Anatomie d'un middleware WSGI

### Structure complète d'un middleware

```python
class MiddlewareTemplate:
    """
    Template générique pour un middleware WSGI.
    
    Utiliser une classe plutôt qu'une closure présente plusieurs avantages :
    - Configuration dans __init__
    - État persistant entre les requêtes
    - Méthodes utilitaires
    - Héritage possible
    """
    
    def __init__(self, app, **options):
        """
        app     : l'application WSGI suivante dans la chaîne
        options : configuration du middleware
        """
        self.app = app
        # Stocker les options de configuration
        self.options = options
    
    def __call__(self, environ, start_response):
        """
        Point d'entrée pour chaque requête.
        Doit respecter le contrat WSGI.
        """
        # === PHASE 1 : Traitement de la REQUÊTE ===
        # On peut lire, modifier ou rejeter la requête ici
        self.avant_requete(environ)
        
        # === PHASE 2 : Intercepter start_response ===
        # Pour modifier les en-têtes de réponse, on doit wrapper start_response
        statut_capture = []
        headers_capture = []
        
        def start_response_interceptee(status, response_headers, exc_info=None):
            # Modifier les en-têtes ici si nécessaire
            response_headers_modifies = self.modifier_headers(response_headers, environ)
            statut_capture.append(status)
            headers_capture.extend(response_headers_modifies)
            return start_response(status, response_headers_modifies, exc_info)
        
        # === PHASE 3 : Appeler l'application suivante ===
        try:
            resultat = self.app(environ, start_response_interceptee)
        except Exception as e:
            # Gérer les erreurs si nécessaire
            return self.gerer_erreur(environ, start_response, e)
        
        # === PHASE 4 : Traitement de la RÉPONSE ===
        # On peut modifier le body ici
        resultat_modifie = self.apres_reponse(
            resultat, 
            statut_capture[0] if statut_capture else "???",
            environ
        )
        
        return resultat_modifie
    
    def avant_requete(self, environ):
        """Hook appelé avant de transmettre la requête. À surcharger."""
        pass
    
    def modifier_headers(self, response_headers, environ):
        """Hook pour modifier les en-têtes. À surcharger."""
        return response_headers
    
    def apres_reponse(self, resultat, status, environ):
        """Hook appelé après avoir reçu la réponse. À surcharger."""
        return resultat
    
    def gerer_erreur(self, environ, start_response, erreur):
        """Hook pour gérer les exceptions. À surcharger."""
        import json
        body = json.dumps({"erreur": str(erreur)}).encode()
        start_response("500 Internal Server Error", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ])
        return [body]
```

---

## 4. Middleware de logging

### Version simple (fonction)

```python
import time
import sys

def logging_middleware_simple(app):
    """
    Middleware de logging simple.
    Affiche chaque requête et son statut de réponse.
    """
    def wsgi_app(environ, start_response):
        debut = time.time()
        
        method = environ.get("REQUEST_METHOD", "?")
        path   = environ.get("PATH_INFO", "/")
        query  = environ.get("QUERY_STRING", "")
        
        url = f"{path}?{query}" if query else path
        
        # Capturer le statut de la réponse
        statut_reponse = []
        
        def start_response_log(status, headers, exc_info=None):
            statut_reponse.append(status)
            return start_response(status, headers, exc_info)
        
        resultat = app(environ, start_response_log)
        
        duree_ms = (time.time() - debut) * 1000
        status   = statut_reponse[0] if statut_reponse else "???"
        
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"{method:6s} {url:30s} "
            f"{status:20s} "
            f"{duree_ms:.1f}ms",
            file=sys.stderr
        )
        
        return resultat
    
    return wsgi_app
```

### Version avancée (classe)

```python
import time
import sys
import json
from io import BytesIO

class LoggingMiddleware:
    """
    Middleware de logging complet.
    
    Fonctionnalités :
    - Log chaque requête avec méthode, path, status, durée
    - Log optionnel du body des requêtes POST/PUT
    - Log optionnel du body des réponses
    - Niveaux de verbosité configurables
    - Format JSON pour l'intégration avec des outils de log
    """
    
    NIVEAUX = {0: "MINIMAL", 1: "NORMAL", 2: "VERBOSE", 3: "DEBUG"}
    
    def __init__(self, app, niveau=1, format_json=False, fichier=None):
        """
        app         : app WSGI suivante
        niveau      : 0=minimal, 1=normal, 2=verbose (body), 3=debug (tout)
        format_json : True pour des logs en JSON (pour Splunk, ELK, etc.)
        fichier     : objet fichier pour les logs (défaut: stderr)
        """
        self.app         = app
        self.niveau      = niveau
        self.format_json = format_json
        self.sortie      = fichier or sys.stderr
    
    def __call__(self, environ, start_response):
        debut     = time.time()
        method    = environ.get("REQUEST_METHOD", "?")
        path      = environ.get("PATH_INFO", "/")
        query     = environ.get("QUERY_STRING", "")
        remote    = environ.get("REMOTE_ADDR", "-")
        user_agent= environ.get("HTTP_USER_AGENT", "-")
        
        # Si debug : lire et logger le body de la requête
        body_requete = b""
        if self.niveau >= 3 and method in ("POST", "PUT", "PATCH"):
            body_requete = self._lire_body(environ)
        
        statut_capture  = []
        headers_capture = []
        
        def start_response_log(status, response_headers, exc_info=None):
            statut_capture.append(status)
            headers_capture.extend(response_headers)
            return start_response(status, response_headers, exc_info)
        
        # Appel de l'app
        try:
            resultat = self.app(environ, start_response_log)
        except Exception as e:
            self._logger_erreur(method, path, str(e))
            raise
        
        duree_ms = (time.time() - debut) * 1000
        status   = statut_capture[0] if statut_capture else "???"
        
        # Collecter le body de réponse si verbose
        body_reponse = b""
        if self.niveau >= 2:
            body_reponse, resultat = self._capturer_body(resultat)
        
        # Logger
        self._logger(
            method=method,
            path=path,
            query=query,
            status=status,
            duree_ms=duree_ms,
            remote=remote,
            user_agent=user_agent,
            body_req=body_requete,
            body_resp=body_reponse,
        )
        
        return resultat
    
    def _lire_body(self, environ):
        """Lit le body sans le consommer (le remet dans wsgi.input)."""
        try:
            length = int(environ.get("CONTENT_LENGTH", 0) or 0)
            body = environ["wsgi.input"].read(length)
            environ["wsgi.input"] = BytesIO(body)  # remettre pour l'app
            return body
        except Exception:
            return b""
    
    def _capturer_body(self, resultat):
        """Collecte les bytes du body de réponse."""
        parties = list(resultat)  # matérialiser le générateur
        body = b"".join(parties)
        return body, [body]  # retourner un itérable avec les données
    
    def _logger(self, **kwargs):
        """Formater et écrire le log."""
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if self.format_json:
            log = {
                "timestamp": ts,
                "method":    kwargs["method"],
                "path":      kwargs["path"],
                "query":     kwargs["query"],
                "status":    kwargs["status"],
                "duree_ms":  round(kwargs["duree_ms"], 2),
                "remote":    kwargs["remote"],
            }
            if self.niveau >= 3:
                log["body_request"] = kwargs["body_req"].decode("utf-8", errors="replace")
            if self.niveau >= 2:
                log["body_response"] = kwargs["body_resp"].decode("utf-8", errors="replace")[:500]
            
            print(json.dumps(log, ensure_ascii=False), file=self.sortie)
        
        else:
            url = kwargs["path"]
            if kwargs["query"]:
                url += "?" + kwargs["query"]
            
            ligne = (
                f"[{ts}] "
                f"{kwargs['method']:7s} "
                f"{url:35s} "
                f"{kwargs['status']:20s} "
                f"{kwargs['duree_ms']:7.1f}ms "
                f"[{kwargs['remote']}]"
            )
            print(ligne, file=self.sortie)
            
            if self.niveau >= 2 and kwargs["body_resp"]:
                extrait = kwargs["body_resp"][:200].decode("utf-8", errors="replace")
                print(f"  Response body (200 chars): {extrait}", file=self.sortie)
    
    def _logger_erreur(self, method, path, message):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] ERREUR {method} {path} : {message}", file=self.sortie)
```

---

## 5. Middleware de timing

```python
import time

class TimingMiddleware:
    """
    Middleware de timing.
    
    Ajoute les en-têtes de performance à la réponse :
    - X-Response-Time : durée totale en millisecondes
    - X-Start-Time    : timestamp Unix du début du traitement
    
    Utilisé par les outils de monitoring (Datadog, New Relic, etc.)
    pour mesurer la latence des endpoints.
    """
    
    def __init__(self, app, seuil_alerte_ms=500):
        """
        app              : app WSGI suivante
        seuil_alerte_ms  : si la requête prend plus que ce seuil,
                           un avertissement est affiché
        """
        self.app             = app
        self.seuil_alerte_ms = seuil_alerte_ms
    
    def __call__(self, environ, start_response):
        debut = time.perf_counter()
        start_time = time.time()
        
        # On doit intercepter start_response pour ajouter nos en-têtes
        headers_modifies = []
        
        def start_response_timing(status, response_headers, exc_info=None):
            # Calculer la durée au moment où les en-têtes sont envoyés
            duree_ms = (time.perf_counter() - debut) * 1000
            
            # Ajouter nos en-têtes de timing
            nouveaux_headers = list(response_headers) + [
                ("X-Response-Time", f"{duree_ms:.2f}ms"),
                ("X-Start-Time",    str(int(start_time * 1000))),
            ]
            
            # Alerte si trop lent
            if duree_ms > self.seuil_alerte_ms:
                path = environ.get("PATH_INFO", "?")
                method = environ.get("REQUEST_METHOD", "?")
                print(
                    f"[TIMING WARNING] {method} {path} : "
                    f"{duree_ms:.0f}ms > seuil {self.seuil_alerte_ms}ms"
                )
            
            return start_response(status, nouveaux_headers, exc_info)
        
        return self.app(environ, start_response_timing)


# Version fonctionnelle simple
def timing_middleware(app, seuil_ms=1000):
    """Version fonctionnelle du TimingMiddleware."""
    def wsgi_app(environ, start_response):
        debut = time.perf_counter()
        
        def sr_timing(status, headers, exc_info=None):
            duree = (time.perf_counter() - debut) * 1000
            headers_augmentes = list(headers) + [
                ("X-Response-Time", f"{duree:.2f}ms"),
            ]
            return start_response(status, headers_augmentes, exc_info)
        
        return app(environ, sr_timing)
    
    return wsgi_app
```

---

## 6. Middleware d'authentification

```python
import json
import time
import hashlib
import hmac

class AuthMiddleware:
    """
    Middleware d'authentification par token Bearer.
    
    Vérifie que chaque requête possède un en-tête Authorization valide,
    sauf pour les routes exclues (liste blanche).
    
    Format attendu : Authorization: Bearer <token>
    """
    
    def __init__(self, app, tokens_valides, routes_publiques=None):
        """
        app              : app WSGI suivante
        tokens_valides   : set ou dict de tokens valides
                           Si dict : {'token123': {'user': 'alice', 'role': 'admin'}}
        routes_publiques : liste de paths accessibles sans auth
                           ex: ['/', '/health', '/login']
        """
        self.app             = app
        self.tokens_valides  = tokens_valides
        self.routes_publiques = set(routes_publiques or ["/", "/health"])
    
    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "/")
        
        # Routes publiques : pas besoin d'auth
        if path in self.routes_publiques:
            return self.app(environ, start_response)
        
        # Extraire le token
        auth_header = environ.get("HTTP_AUTHORIZATION", "")
        
        if not auth_header.startswith("Bearer "):
            return self._reponse_401(
                start_response,
                "Authorization manquant ou format invalide (Bearer <token> requis)"
            )
        
        token = auth_header[len("Bearer "):]
        
        # Vérifier le token
        if isinstance(self.tokens_valides, dict):
            user_info = self.tokens_valides.get(token)
            if user_info is None:
                return self._reponse_401(start_response, "Token invalide")
            # Injecter les infos utilisateur dans environ
            environ["AUTH_USER"]  = user_info.get("user", "unknown")
            environ["AUTH_ROLE"]  = user_info.get("role", "user")
            environ["AUTH_TOKEN"] = token
        
        elif isinstance(self.tokens_valides, (set, list)):
            if token not in self.tokens_valides:
                return self._reponse_401(start_response, "Token invalide")
            environ["AUTH_TOKEN"] = token
        
        else:
            raise TypeError("tokens_valides doit être un dict ou un set")
        
        # Token valide : on continue
        return self.app(environ, start_response)
    
    def _reponse_401(self, start_response, message):
        body = json.dumps(
            {"erreur": "Non autorise", "details": message},
            ensure_ascii=False
        ).encode("utf-8")
        
        start_response("401 Unauthorized", [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("WWW-Authenticate", 'Bearer realm="API"'),
        ])
        return [body]


class CORSMiddleware:
    """
    Middleware CORS (Cross-Origin Resource Sharing).
    
    Ajoute les en-têtes nécessaires pour autoriser les requêtes
    cross-origin depuis un navigateur (ex: frontend React sur port 3000
    qui appelle l'API sur port 8000).
    """
    
    def __init__(self, app, origines_autorisees=None, methodes=None):
        self.app = app
        self.origines = origines_autorisees or ["*"]
        self.methodes = methodes or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    
    def __call__(self, environ, start_response):
        origin = environ.get("HTTP_ORIGIN", "")
        method = environ.get("REQUEST_METHOD", "GET")
        
        # Requête OPTIONS = preflight CORS (le navigateur vérifie avant d'envoyer)
        if method == "OPTIONS":
            start_response("200 OK", self._headers_cors(origin))
            return [b""]
        
        def start_response_cors(status, response_headers, exc_info=None):
            headers_avec_cors = list(response_headers) + self._headers_cors(origin)
            return start_response(status, headers_avec_cors, exc_info)
        
        return self.app(environ, start_response_cors)
    
    def _headers_cors(self, origin):
        origine_autorisee = "*"
        if "*" not in self.origines:
            origine_autorisee = origin if origin in self.origines else self.origines[0]
        
        return [
            ("Access-Control-Allow-Origin",  origine_autorisee),
            ("Access-Control-Allow-Methods", ", ".join(self.methodes)),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
            ("Access-Control-Max-Age",       "86400"),
        ]
```

---

## 7. La pile de middlewares : ordre et flux

### L'ordre est critique

L'ordre dans lequel vous empilez les middlewares change le comportement de votre application.

```python
# Exemple : quelle différence entre ces deux configurations ?

# Configuration A
app_A = AuthMiddleware(
    LoggingMiddleware(
        mon_app
    ),
    tokens_valides=TOKENS
)

# Configuration B
app_B = LoggingMiddleware(
    AuthMiddleware(
        mon_app,
        tokens_valides=TOKENS
    )
)
```

**Configuration A** : Auth d'abord, puis Log
- Si non authentifié → Auth rejette → LoggingMiddleware ne voit PAS la requête rejetée
- Le log ne contient que les requêtes authentifiées

**Configuration B** : Log d'abord, puis Auth
- Toutes les requêtes sont loggées (même les non-authentifiées)
- Vous voyez les tentatives d'accès non autorisées dans les logs

**La bonne configuration dépend de vos besoins.**

### Pile complète recommandée

```python
def construire_app(app_principale):
    """
    Construit la pile de middlewares dans l'ordre recommandé.
    
    L'ordre de lecture ici est l'ordre dans lequel les requêtes arrivent.
    """
    # 1. CORS (tout en haut : répond aux preflight OPTIONS immédiatement)
    app = CORSMiddleware(app_principale)
    
    # 2. Auth (avant le log pour ne pas loguer les requêtes rejetées)
    app = AuthMiddleware(app, tokens_valides=TOKENS, routes_publiques=["/", "/health"])
    
    # 3. Timing (mesure le temps de traitement de l'app + auth)
    app = TimingMiddleware(app, seuil_alerte_ms=500)
    
    # 4. Logging (tout en dehors : voit tout, y compris les erreurs)
    app = LoggingMiddleware(app, niveau=1)
    
    return app

# Construit comme ça, une requête passe par :
# LoggingMiddleware → TimingMiddleware → AuthMiddleware → CORSMiddleware → app

# Et la réponse remonte dans l'autre sens :
# app → CORSMiddleware → AuthMiddleware → TimingMiddleware → LoggingMiddleware
```

### Visualiser le flux

```
REQUÊTE ENTRANTE
       │
       ▼
┌─────────────────────────────────────────────────┐
│                 LoggingMiddleware               │
│  avant: note l'heure de début                  │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │            TimingMiddleware             │   │
│  │  avant: time.perf_counter()             │   │
│  │                                         │   │
│  │  ┌───────────────────────────────────┐  │   │
│  │  │         AuthMiddleware            │  │   │
│  │  │  vérifie Authorization header    │  │   │
│  │  │  ── si invalide → 401 ──────────> │  │   │
│  │  │                                   │  │   │
│  │  │  ┌─────────────────────────────┐  │  │   │
│  │  │  │      CORSMiddleware         │  │  │   │
│  │  │  │  ajoute les en-têtes CORS  │  │  │   │
│  │  │  │                             │  │  │   │
│  │  │  │  ┌───────────────────────┐  │  │  │   │
│  │  │  │  │    VOTRE APPLICATION  │  │  │  │   │
│  │  │  │  │    (la logique métier)│  │  │  │   │
│  │  │  │  └───────────────────────┘  │  │  │   │
│  │  │  │                             │  │  │   │
│  │  │  └─────────────────────────────┘  │  │   │
│  │  │                                   │  │   │
│  │  └───────────────────────────────────┘  │   │
│  │                                         │   │
│  │  après: ajoute X-Response-Time          │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  après: log "GET /api 200 42.3ms"              │
└─────────────────────────────────────────────────┘
       │
       ▼
RÉPONSE SORTANTE
```

---

## 8. Middlewares en Django et Flask

### Comment Django implémente les middlewares

Django a son propre système de middleware, légèrement différent du WSGI pur. Chaque middleware Django est une classe avec des méthodes hook optionnelles :

```python
# Exemple d'un middleware Django (myapp/middleware.py)

class MonMiddlewareDjango:
    """
    Middleware Django (pas WSGI pur, mais le même principe).
    
    Django appelle get_response(request) pour passer à la suite.
    """
    
    def __init__(self, get_response):
        # get_response est l'équivalent de self.app dans WSGI
        self.get_response = get_response
        # Configuration unique au démarrage (pas par requête)
        print("Middleware initialise (une seule fois)")
    
    def __call__(self, request):
        # Code exécuté AVANT la vue
        print(f"Avant la vue : {request.method} {request.path}")
        
        # Appel de la suite (prochain middleware ou vue)
        response = self.get_response(request)
        
        # Code exécuté APRÈS la vue
        response["X-Custom-Header"] = "valeur"
        print(f"Apres la vue : {response.status_code}")
        
        return response
    
    # Hooks optionnels Django :
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Appelé juste avant la vue (après URL resolution)."""
        # Retourner None = continuer normalement
        # Retourner une Response = court-circuiter la vue
        return None
    
    def process_exception(self, request, exception):
        """Appelé si une exception est levée dans la vue."""
        print(f"Exception capturee : {exception}")
        return None  # None = laisser Django gérer
    
    def process_template_response(self, request, response):
        """Appelé si la vue retourne une TemplateResponse."""
        return response


# Dans settings.py, l'ordre des middlewares Django :
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',      # En-têtes de sécurité
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',           # Redirections, slash
    'django.middleware.csrf.CsrfViewMiddleware',          # Protection CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # request.user
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Votre middleware custom (à la fin = proche de la vue)
    'myapp.middleware.MonMiddlewareDjango',
]
```

### Comment Flask implémente les middlewares

Flask n'a pas de système de middleware officiel (comme Django). On utilise les hooks `before_request`/`after_request` ou on compose directement des apps WSGI :

```python
from flask import Flask, request, g
import time

app = Flask(__name__)

# Approche 1 : before_request / after_request
@app.before_request
def avant_requete():
    g.debut = time.perf_counter()

@app.after_request
def apres_requete(response):
    duree_ms = (time.perf_counter() - g.debut) * 1000
    response.headers["X-Response-Time"] = f"{duree_ms:.2f}ms"
    return response


# Approche 2 : middleware WSGI pur avec Flask
# Flask est lui-même une app WSGI !
from mon_middleware import TimingMiddleware, LoggingMiddleware

app_flask = Flask(__name__)
# Entourer l'app Flask avec nos middlewares WSGI
app_avec_middlewares = LoggingMiddleware(
    TimingMiddleware(app_flask)
)
# app_avec_middlewares est ce qu'on donne à Gunicorn
```

### La différence fondamentale

```
WSGI Middleware (pur)           Django Middleware
─────────────────────           ─────────────────
callable(environ, sr)           class avec __call__(self, request)
Travaille avec bytes            Travaille avec objets Django (HttpRequest)
Avant/après la réponse          Hooks spécifiques (view, exception, template)
Framework-agnostique            Lié à Django
Peut modifier le body           Peut modifier request et response Django
```

---

## 9. Résumé et bonnes pratiques

### Ce que vous devez retenir

```
┌─────────────────────────────────────────────────────────────┐
│               MIDDLEWARE WSGI EN RÉSUMÉ                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Un middleware est un callable WSGI qui :                    │
│    1. Reçoit (environ, start_response)                      │
│    2. Peut modifier environ (requête)                        │
│    3. Appelle l'app suivante : self.app(environ, sr)        │
│    4. Peut modifier la réponse avant de la retourner         │
│                                                              │
│  L'ordre des middlewares IMPORTE :                           │
│    Extérieur → Intérieur pour les requêtes                  │
│    Intérieur → Extérieur pour les réponses                  │
│                                                              │
│  Cas d'usage classiques :                                    │
│    - Logging : enregistrer toutes les requêtes              │
│    - Auth    : vérifier les tokens                          │
│    - Timing  : mesurer la performance                        │
│    - CORS    : gérer les en-têtes cross-origin              │
│    - Rate limiting : limiter le nombre de requêtes          │
│    - Gzip   : compresser les réponses                        │
│    - Cache  : mettre en cache les réponses                  │
│                                                              │
│  Conseil : préférez les classes aux fonctions               │
│  (configuration dans __init__, état partagé possible)        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Bonnes pratiques

1. **Un middleware = une responsabilité**. Ne pas mélanger logging et auth dans le même middleware.

2. **Toujours remettre `wsgi.input`** si vous lisez le body d'une requête, pour que les middlewares suivants puissent le lire aussi.

3. **Ne pas matérialiser le body de réponse sauf nécessité**. Les réponses peuvent être des générateurs (streaming). Les collecter en mémoire avec `list()` peut causer des problèmes de mémoire sur de gros fichiers.

4. **Propager `exc_info`**. Si vous interceptez `start_response`, transmettez `exc_info` correctement.

5. **Tester chaque middleware indépendamment** avant de les empiler.

---

*Jour 13 — 9 juillet 2026 — Programme Backend Python/Django*
