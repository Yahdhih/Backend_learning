# Jour 14 — Router WSGI from scratch (10 juillet 2026)

---

## Table des matières

1. [Qu'est-ce que le routing URL ?](#1-quest-ce-que-le-routing-url)
2. [Lire PATH_INFO depuis environ](#2-lire-path_info)
3. [Stratégies de matching d'URL](#3-stratégies-de-matching)
4. [Construire un Router simple](#4-construire-un-router-simple)
5. [Dispatching par méthode HTTP](#5-dispatching-par-méthode)
6. [Paramètres dynamiques dans l'URL](#6-paramètres-dynamiques)
7. [Router basé sur les regex](#7-router-regex)
8. [Router avec décorateurs (style Flask)](#8-router-avec-décorateurs)
9. [Gestion du 404 et du 405](#9-gestion-des-erreurs)
10. [Implémentation complète et commentée](#10-implémentation-complète)
11. [Résumé](#11-résumé)

---

## 1. Qu'est-ce que le routing URL ?

### Le problème

Votre application WSGI reçoit toutes les requêtes via un seul point d'entrée : `application(environ, start_response)`. Comment savoir quelle logique exécuter en fonction de l'URL demandée ?

```python
# Sans routing : if/elif interminable
def application(environ, start_response):
    path = environ['PATH_INFO']
    if path == '/':
        ...
    elif path == '/users':
        ...
    elif path == '/products':
        ...
    elif path.startswith('/users/') and path.count('/') == 2:
        ...
    elif path.startswith('/products/') and ...:
        ...
    # 50 elif plus tard...
```

C'est ingérable. D'où la nécessité d'un **routeur** : un composant qui fait correspondre des patterns d'URL à des fonctions de traitement (les *handlers* ou *vues*).

### Ce que fait un routeur

```
Requête : GET /users/42

Router consulte sa table de routes :
  "/" + GET          →  handler_accueil
  "/users" + GET     →  handler_liste_users
  "/users" + POST    →  handler_creer_user
  "/users/{id}" + GET →  handler_detail_user  ← MATCH !
  "/users/{id}" + PUT →  handler_maj_user

Extraction des paramètres : id = 42
Appel : handler_detail_user(environ, start_response, id=42)
```

### L'anatomie d'une route

```
GET  /api/users/{user_id}/orders/{order_id}
│    │    │         │           │
│    │    │         │           └── segment dynamique 2
│    │    │         └── segment dynamique 1
│    │    └── segments statiques
│    └── path pattern
└── méthode HTTP
```

---

## 2. Lire PATH_INFO

### Les clés WSGI pour le routing

```python
def inspecter_url(environ):
    """Montrer toutes les clés utiles pour le routing."""
    
    # PATH_INFO : le chemin demandé, toujours présent
    path = environ['PATH_INFO']
    # '/users/42' ou '/' ou '/api/v1/products'
    
    # SCRIPT_NAME : préfixe si l'app est montée sous un sous-chemin
    script = environ.get('SCRIPT_NAME', '')
    # '' (vide) si l'app est à la racine
    # '/api' si l'app est montée sous /api (via un proxy)
    
    # URL complète reconstituée
    url_complete = script + path
    
    # REQUEST_METHOD : la méthode HTTP
    method = environ['REQUEST_METHOD']
    # 'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'
    
    # QUERY_STRING : les paramètres après '?'
    query = environ.get('QUERY_STRING', '')
    # 'page=2&limit=10' (sans le '?')
    
    return {
        'path':     path,
        'script':   script,
        'full_url': url_complete,
        'method':   method,
        'query':    query,
    }
```

### Normaliser le PATH_INFO

```python
def normaliser_path(path):
    """
    Normalise un PATH_INFO pour le matching.
    
    Problèmes courants :
    - "/users/" et "/users" sont la même route
    - "//" double slash
    - Majuscules dans le path
    """
    if not path:
        return "/"
    
    # Supprimer le slash final (sauf pour la racine)
    path = path.rstrip("/") or "/"
    
    # Mettre en minuscules (si votre API est insensible à la casse)
    # path = path.lower()  # décommenter si nécessaire
    
    return path
```

---

## 3. Stratégies de matching

### Matching exact

La stratégie la plus simple : l'URL doit correspondre exactement.

```python
routes_exactes = {
    "/":         handler_accueil,
    "/users":    handler_liste_users,
    "/products": handler_liste_products,
    "/health":   handler_health,
}

def dispatcher_exact(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    handler = routes_exactes.get(path)
    if handler:
        return handler(environ, start_response)
    # 404...
```

**Avantage** : O(1), ultra-rapide (dict lookup).
**Inconvénient** : impossible d'avoir `/users/42` et `/users/99`.

### Matching par préfixe

```python
routes_prefixes = [
    ("/api/v2/", app_v2),
    ("/api/v1/", app_v1),
    ("/static/", servir_fichiers_statiques),
    ("/",        app_principale),
]

def dispatcher_prefixe(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    for prefixe, handler in routes_prefixes:
        if path.startswith(prefixe):
            return handler(environ, start_response)
```

**Avantage** : utile pour monter des sous-applications.
**Inconvénient** : ordre important (mettre les préfixes plus longs en premier).

### Matching par regex

La stratégie la plus puissante. Permet d'extraire des paramètres de l'URL.

```python
import re

routes_regex = [
    (re.compile(r'^/$'),                          'GET',    handler_accueil),
    (re.compile(r'^/users$'),                     'GET',    handler_liste_users),
    (re.compile(r'^/users$'),                     'POST',   handler_creer_user),
    (re.compile(r'^/users/(?P<id>\d+)$'),         'GET',    handler_detail_user),
    (re.compile(r'^/users/(?P<id>\d+)$'),         'PUT',    handler_maj_user),
    (re.compile(r'^/users/(?P<id>\d+)/orders$'),  'GET',    handler_commandes_user),
]

def dispatcher_regex(environ, start_response):
    path   = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')
    
    for pattern, meth, handler in routes_regex:
        match = pattern.match(path)
        if match and meth == method:
            # Les groupes nommés (?P<id>\d+) sont dans match.groupdict()
            kwargs = match.groupdict()
            # Convertir les IDs en entiers
            kwargs = {k: int(v) if v.isdigit() else v for k, v in kwargs.items()}
            return handler(environ, start_response, **kwargs)
    
    # 404
```

---

## 4. Construire un Router simple

### Version minimale : Router basé sur un dict

```python
class RouterSimple:
    """
    Router basique : matching exact + dispatching par méthode.
    
    Utilisation :
        router = RouterSimple()
        
        @router.get("/users")
        def liste_users(environ, start_response):
            ...
        
        @router.post("/users")
        def creer_user(environ, start_response):
            ...
    """
    
    def __init__(self):
        # Structure : {path: {method: handler}}
        self.routes = {}
    
    def ajouter_route(self, path, method, handler):
        """Enregistrer un handler pour (path, method)."""
        path   = path.rstrip("/") or "/"
        method = method.upper()
        
        if path not in self.routes:
            self.routes[path] = {}
        
        self.routes[path][method] = handler
    
    # Décorateurs pour l'ergonomie
    def get(self, path):
        def decorator(func):
            self.ajouter_route(path, "GET", func)
            return func
        return decorator
    
    def post(self, path):
        def decorator(func):
            self.ajouter_route(path, "POST", func)
            return func
        return decorator
    
    def put(self, path):
        def decorator(func):
            self.ajouter_route(path, "PUT", func)
            return func
        return decorator
    
    def delete(self, path):
        def decorator(func):
            self.ajouter_route(path, "DELETE", func)
            return func
        return decorator
    
    def __call__(self, environ, start_response):
        """Point d'entrée WSGI : dispatcher la requête."""
        path   = environ.get("PATH_INFO", "/").rstrip("/") or "/"
        method = environ.get("REQUEST_METHOD", "GET").upper()
        
        if path in self.routes:
            methodes_disponibles = self.routes[path]
            
            if method in methodes_disponibles:
                # Route trouvée, méthode autorisée
                handler = methodes_disponibles[method]
                return handler(environ, start_response)
            else:
                # Route trouvée, mauvaise méthode → 405
                return self._reponse_405(start_response, list(methodes_disponibles.keys()))
        
        # Route inconnue → 404
        return self._reponse_404(start_response, path)
    
    def _reponse_404(self, start_response, path):
        import json
        body = json.dumps({"erreur": f"Route '{path}' introuvable"}).encode()
        start_response("404 Not Found", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ])
        return [body]
    
    def _reponse_405(self, start_response, methodes_autorisees):
        import json
        body = json.dumps({
            "erreur": "Methode non autorisee",
            "methodes_acceptees": methodes_autorisees,
        }).encode()
        start_response("405 Method Not Allowed", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
            ("Allow", ", ".join(methodes_autorisees)),
        ])
        return [body]
```

### Utilisation du RouterSimple

```python
router = RouterSimple()

@router.get("/")
def accueil(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Bienvenue !"]

@router.get("/users")
def liste_users(environ, start_response):
    import json
    data = [{"id": 1, "name": "Alice"}]
    body = json.dumps(data).encode()
    start_response("200 OK", [("Content-Type", "application/json")])
    return [body]

@router.post("/users")
def creer_user(environ, start_response):
    start_response("201 Created", [("Content-Type", "application/json")])
    return [b'{"message": "Utilisateur cree"}']

# router est l'application WSGI
# from wsgiref.simple_server import make_server
# with make_server('', 8000, router) as s: s.serve_forever()
```

---

## 5. Dispatching par méthode

### Plusieurs méthodes, même handler (CBV style)

Parfois, il est pratique de grouper GET et POST d'un même endpoint dans la même classe :

```python
class VueBasee:
    """
    Classe de base pour les vues basées sur des classes (CBV).
    Similaire aux vues Django.
    """
    
    methodes_autorisees = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    
    def dispatch(self, environ, start_response):
        """Dispatcher vers la méthode get(), post(), etc."""
        method = environ.get("REQUEST_METHOD", "GET").upper()
        
        # Chercher une méthode sur self correspondant à la méthode HTTP
        handler = getattr(self, method.lower(), None)
        
        if handler is None:
            return self._methode_non_autorisee(environ, start_response)
        
        return handler(environ, start_response)
    
    def __call__(self, environ, start_response):
        return self.dispatch(environ, start_response)
    
    def _methode_non_autorisee(self, environ, start_response):
        import json
        methodes = [m.lower() for m in dir(self) 
                    if m.upper() in self.methodes_autorisees 
                    and callable(getattr(self, m))]
        body = json.dumps({"erreur": "Methode non autorisee"}).encode()
        start_response("405 Method Not Allowed", [
            ("Content-Type", "application/json"),
            ("Allow", ", ".join(m.upper() for m in methodes)),
        ])
        return [body]


class VueUsers(VueBasee):
    """Vue pour les endpoints /users."""
    
    def get(self, environ, start_response):
        """GET /users → liste des utilisateurs."""
        import json
        data = [{"id": 1, "nom": "Alice"}, {"id": 2, "nom": "Bob"}]
        body = json.dumps(data).encode()
        start_response("200 OK", [("Content-Type", "application/json")])
        return [body]
    
    def post(self, environ, start_response):
        """POST /users → créer un utilisateur."""
        import json
        body = json.dumps({"message": "Utilisateur cree", "id": 3}).encode()
        start_response("201 Created", [("Content-Type", "application/json")])
        return [body]
    
    # DELETE n'est pas défini → retournera 405


# Enregistrement dans le router
router = RouterSimple()
vue_users = VueUsers()
router.ajouter_route("/users", "GET",  vue_users.get)
router.ajouter_route("/users", "POST", vue_users.post)
```

---

## 6. Paramètres dynamiques dans l'URL

### Le problème du segment variable

```
/users/1     →  même handler que
/users/42    →  même handler que
/users/9999  →  même handler
```

Pour cela, il faut un système de pattern matching avec **capture de groupes**.

### Approche 1 : Découpage du path

```python
def extraire_id_depuis_path(path, prefixe):
    """
    Extrait le segment après le préfixe.
    
    ex: extraire_id_depuis_path("/users/42", "/users/") → "42"
    """
    if not path.startswith(prefixe):
        return None
    reste = path[len(prefixe):]
    # Vérifier qu'il n'y a pas de slash supplémentaire
    if "/" in reste:
        return None
    return reste


def dispatcher_avec_id(environ, start_response):
    path = environ['PATH_INFO']
    
    if path.startswith('/users/'):
        id_str = extraire_id_depuis_path(path, '/users/')
        if id_str is not None:
            try:
                user_id = int(id_str)
                return handler_detail_user(environ, start_response, user_id)
            except ValueError:
                pass
    # ...
```

### Approche 2 : Conversion de pattern en regex

C'est l'approche utilisée par Flask, Django et tous les frameworks modernes.

```python
import re

def pattern_vers_regex(pattern):
    """
    Convertit un pattern d'URL avec {parametre} en regex.
    
    Exemples :
      "/users/{id}"           → regex r'^/users/(?P<id>[^/]+)$'
      "/users/{id}/orders"    → regex r'^/users/(?P<id>[^/]+)/orders$'
      "/files/{path:path}"    → regex r'^/files/(?P<path>.+)$'
    
    Types supportés :
      {nom}        → capture [^/]+  (un segment, sans slash)
      {nom:int}    → capture \d+    (entiers seulement)
      {nom:path}   → capture .+     (peut contenir des slashes)
    """
    # Regex pour trouver les paramètres {nom} ou {nom:type}
    param_pattern = re.compile(r'\{(\w+)(?::(\w+))?\}')
    
    # Construire la regex
    regex_str = "^"
    last_end = 0
    
    for match in param_pattern.finditer(pattern):
        nom  = match.group(1)
        type_ = match.group(2) or "str"
        
        # Ajouter la partie statique avant ce paramètre
        regex_str += re.escape(pattern[last_end:match.start()])
        
        # Ajouter la capture selon le type
        if type_ == "int":
            regex_str += f"(?P<{nom}>\\d+)"
        elif type_ == "path":
            regex_str += f"(?P<{nom}>.+)"
        else:  # str par défaut
            regex_str += f"(?P<{nom}>[^/]+)"
        
        last_end = match.end()
    
    # Ajouter le reste statique
    regex_str += re.escape(pattern[last_end:])
    regex_str += "$"
    
    return re.compile(regex_str)


# Test de la fonction
if __name__ == "__main__":
    tests = [
        ("/users/{id}",               "/users/42"),
        ("/users/{id:int}",           "/users/42"),
        ("/users/{id}/orders/{oid}",  "/users/5/orders/101"),
        ("/files/{path:path}",        "/files/docs/readme.txt"),
    ]
    
    for pattern, url in tests:
        regex = pattern_vers_regex(pattern)
        match = regex.match(url)
        if match:
            print(f"  {pattern!r} ← {url!r}  →  {match.groupdict()}")
        else:
            print(f"  {pattern!r} ← {url!r}  →  NO MATCH")
```

---

## 7. Router basé sur les regex

### Implémentation complète

```python
import re
import json
from typing import Callable, Dict, Any, Optional


class Route:
    """Représente une route : pattern compilé + méthode + handler."""
    
    def __init__(self, pattern: str, method: str, handler: Callable, nom: str = None):
        self.pattern_str  = pattern
        self.method       = method.upper()
        self.handler      = handler
        self.nom          = nom or handler.__name__
        self.regex        = self._compiler(pattern)
        self.convertisseurs = self._extraire_convertisseurs(pattern)
    
    def _compiler(self, pattern: str) -> re.Pattern:
        """Convertir le pattern en expression régulière."""
        # Remplacer {param} par (?P<param>[^/]+)
        # Remplacer {param:int} par (?P<param>\d+)
        # Remplacer {param:path} par (?P<param>.+)
        
        def remplacer(match):
            nom   = match.group(1)
            type_ = match.group(2) or "str"
            if type_ == "int":
                return f"(?P<{nom}>\\d+)"
            elif type_ == "path":
                return f"(?P<{nom}>.+)"
            else:
                return f"(?P<{nom}>[^/]+)"
        
        regex_str = re.sub(r'\{(\w+)(?::(\w+))?\}', remplacer, re.escape(pattern))
        # re.escape() échappe les caractères spéciaux MAIS aussi les accolades
        # donc on doit travailler sur le pattern original
        
        # Approche correcte : construire la regex sans re.escape sur le pattern complet
        parts = re.split(r'(\{[^}]+\})', pattern)
        regex_parts = []
        for part in parts:
            if part.startswith('{') and part.endswith('}'):
                interieur = part[1:-1]
                if ':' in interieur:
                    nom, type_ = interieur.split(':', 1)
                else:
                    nom, type_ = interieur, 'str'
                
                if type_ == 'int':
                    regex_parts.append(f"(?P<{nom}>\\d+)")
                elif type_ == 'path':
                    regex_parts.append(f"(?P<{nom}>.+)")
                else:
                    regex_parts.append(f"(?P<{nom}>[^/]+)")
            else:
                regex_parts.append(re.escape(part))
        
        return re.compile("^" + "".join(regex_parts) + "$")
    
    def _extraire_convertisseurs(self, pattern: str) -> Dict[str, type]:
        """Extraire les types des paramètres pour la conversion."""
        convertisseurs = {}
        for match in re.finditer(r'\{(\w+)(?::(\w+))?\}', pattern):
            nom   = match.group(1)
            type_ = match.group(2) or 'str'
            if type_ == 'int':
                convertisseurs[nom] = int
            else:
                convertisseurs[nom] = str
        return convertisseurs
    
    def correspondre(self, path: str):
        """
        Essayer de matcher le path.
        Retourne un dict de kwargs si succès, None si échec.
        """
        match = self.regex.match(path)
        if not match:
            return None
        
        kwargs = match.groupdict()
        
        # Appliquer les conversions de types
        for nom, conv in self.convertisseurs.items():
            if nom in kwargs:
                try:
                    kwargs[nom] = conv(kwargs[nom])
                except (ValueError, TypeError):
                    return None  # Type incorrect → pas de match
        
        return kwargs
    
    def __repr__(self):
        return f"<Route {self.method} {self.pattern_str!r} → {self.nom}>"


class Router:
    """
    Router WSGI complet basé sur les regex.
    
    Fonctionnalités :
    - Enregistrement de routes avec patterns dynamiques
    - Dispatching par méthode HTTP
    - Extraction et conversion de paramètres d'URL
    - Gestion des 404 et 405
    - Décorateurs pour l'ergonomie
    """
    
    def __init__(self):
        self.routes: list[Route] = []
        self._handler_404 = self._defaut_404
        self._handler_405 = self._defaut_405
    
    def ajouter(self, pattern: str, method: str, handler: Callable, nom: str = None):
        """Enregistrer une route."""
        route = Route(pattern, method, handler, nom)
        self.routes.append(route)
        return handler
    
    def route(self, pattern: str, methods: list = None):
        """Décorateur général."""
        if methods is None:
            methods = ["GET"]
        
        def decorator(func):
            for method in methods:
                self.ajouter(pattern, method, func)
            return func
        return decorator
    
    def get(self, pattern: str):
        """Décorateur pour GET."""
        def decorator(func):
            self.ajouter(pattern, "GET", func)
            return func
        return decorator
    
    def post(self, pattern: str):
        """Décorateur pour POST."""
        def decorator(func):
            self.ajouter(pattern, "POST", func)
            return func
        return decorator
    
    def put(self, pattern: str):
        """Décorateur pour PUT."""
        def decorator(func):
            self.ajouter(pattern, "PUT", func)
            return func
        return decorator
    
    def delete(self, pattern: str):
        """Décorateur pour DELETE."""
        def decorator(func):
            self.ajouter(pattern, "DELETE", func)
            return func
        return decorator
    
    def handler_404(self, func):
        """Décorateur pour définir un handler 404 custom."""
        self._handler_404 = func
        return func
    
    def __call__(self, environ, start_response):
        """Point d'entrée WSGI."""
        path   = environ.get("PATH_INFO", "/").rstrip("/") or "/"
        method = environ.get("REQUEST_METHOD", "GET").upper()
        
        # Chercher une route correspondante
        routes_matching_path = []  # routes qui matchent le path (toute méthode)
        
        for route in self.routes:
            kwargs = route.correspondre(path)
            if kwargs is not None:
                routes_matching_path.append((route, kwargs))
                
                if route.method == method:
                    # Match parfait : path ET méthode
                    # Injecter les paramètres URL dans environ
                    environ["url_kwargs"] = kwargs
                    return route.handler(environ, start_response, **kwargs)
        
        if routes_matching_path:
            # Le path existe mais pas avec cette méthode → 405
            methodes_disponibles = [r.method for r, _ in routes_matching_path]
            return self._handler_405(environ, start_response, methodes_disponibles)
        
        # Aucun path correspondant → 404
        return self._handler_404(environ, start_response)
    
    def _defaut_404(self, environ, start_response):
        path = environ.get("PATH_INFO", "?")
        body = json.dumps({"erreur": f"Route '{path}' introuvable"}).encode()
        start_response("404 Not Found", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ])
        return [body]
    
    def _defaut_405(self, environ, start_response, methodes_autorisees):
        body = json.dumps({
            "erreur": "Methode non autorisee",
            "methodes_acceptees": methodes_autorisees,
        }).encode()
        start_response("405 Method Not Allowed", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
            ("Allow", ", ".join(methodes_autorisees)),
        ])
        return [body]
    
    def afficher_routes(self):
        """Debug : afficher toutes les routes enregistrées."""
        print("Routes enregistrées :")
        for route in self.routes:
            print(f"  {route.method:7s} {route.pattern_str:35s} → {route.nom}")
```

---

## 8. Router avec décorateurs (style Flask)

### Utilisation complète du Router

```python
import json
from urllib.parse import parse_qs

# Instanciation du router
app = Router()

# Base de données fictive
USERS_DB = {
    1: {"id": 1, "nom": "Alice", "email": "alice@example.com", "role": "admin"},
    2: {"id": 2, "nom": "Bob",   "email": "bob@example.com",   "role": "user"},
    3: {"id": 3, "nom": "Carol", "email": "carol@example.com", "role": "user"},
}


def json_response(start_response, data, status="200 OK"):
    """Utilitaire : réponse JSON."""
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    start_response(status, [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


# ─── Route racine ────────────────────────────────────────────────────────────

@app.get("/")
def accueil(environ, start_response):
    return json_response(start_response, {
        "message": "API WSGI avec Router",
        "routes":  [str(r) for r in app.routes],
    })


# ─── Collection /users ───────────────────────────────────────────────────────

@app.get("/users")
def liste_users(environ, start_response):
    """GET /users → retourne tous les utilisateurs."""
    query  = environ.get("QUERY_STRING", "")
    params = {k: v[0] for k, v in parse_qs(query).items()}
    
    users = list(USERS_DB.values())
    
    # Filtrage optionnel par rôle
    if "role" in params:
        users = [u for u in users if u["role"] == params["role"]]
    
    return json_response(start_response, {"users": users, "total": len(users)})


@app.post("/users")
def creer_user(environ, start_response):
    """POST /users → crée un utilisateur."""
    try:
        length = int(environ.get("CONTENT_LENGTH", 0) or 0)
        body   = environ["wsgi.input"].read(length)
        data   = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return json_response(start_response, {"erreur": "JSON invalide"}, "400 Bad Request")
    
    if "nom" not in data or "email" not in data:
        return json_response(
            start_response,
            {"erreur": "Champs requis : nom, email"},
            "400 Bad Request"
        )
    
    new_id = max(USERS_DB.keys()) + 1
    nouvel_user = {"id": new_id, "nom": data["nom"], "email": data["email"], "role": "user"}
    USERS_DB[new_id] = nouvel_user
    
    return json_response(start_response, nouvel_user, "201 Created")


# ─── Ressource individuelle /users/{id} ──────────────────────────────────────

@app.get("/users/{id:int}")
def detail_user(environ, start_response, id):
    """GET /users/{id} → détail d'un utilisateur."""
    user = USERS_DB.get(id)
    if user is None:
        return json_response(
            start_response,
            {"erreur": f"Utilisateur {id} introuvable"},
            "404 Not Found"
        )
    return json_response(start_response, user)


@app.put("/users/{id:int}")
def maj_user(environ, start_response, id):
    """PUT /users/{id} → mise à jour d'un utilisateur."""
    if id not in USERS_DB:
        return json_response(
            start_response,
            {"erreur": f"Utilisateur {id} introuvable"},
            "404 Not Found"
        )
    
    try:
        length = int(environ.get("CONTENT_LENGTH", 0) or 0)
        body   = environ["wsgi.input"].read(length)
        data   = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return json_response(start_response, {"erreur": "JSON invalide"}, "400 Bad Request")
    
    USERS_DB[id].update({k: v for k, v in data.items() if k != "id"})
    return json_response(start_response, USERS_DB[id])


@app.delete("/users/{id:int}")
def supprimer_user(environ, start_response, id):
    """DELETE /users/{id} → supprime un utilisateur."""
    if id not in USERS_DB:
        return json_response(
            start_response,
            {"erreur": f"Utilisateur {id} introuvable"},
            "404 Not Found"
        )
    del USERS_DB[id]
    body = b""
    start_response("204 No Content", [("Content-Length", "0")])
    return [body]


# ─── Handler 404 custom ──────────────────────────────────────────────────────

@app.handler_404
def ma_page_404(environ, start_response):
    path = environ.get("PATH_INFO", "?")
    return json_response(
        start_response,
        {
            "erreur": "Page introuvable",
            "chemin": path,
            "conseil": "Consultez GET / pour la liste des routes disponibles",
        },
        "404 Not Found"
    )
```

---

## 9. Gestion des erreurs

### 404 Not Found

```
Règle : PATH_INFO ne correspond à aucune route connue.
Code HTTP : 404
Header recommandé : Content-Type: application/json
```

### 405 Method Not Allowed

```
Règle : PATH_INFO existe, mais la méthode HTTP utilisée n'est pas enregistrée.
Code HTTP : 405
Header OBLIGATOIRE : Allow: GET, POST  (liste des méthodes acceptées)
```

```python
# Exemple : /users existe avec GET et POST
# Envoyer DELETE /users → 405 avec Allow: GET, POST

def demo_405(environ, start_response):
    # Obligatoire selon la RFC 7231 : l'en-tête Allow doit être présent
    start_response("405 Method Not Allowed", [
        ("Content-Type", "application/json"),
        ("Allow", "GET, POST"),  # OBLIGATOIRE !
    ])
    return [b'{"erreur": "Methode non autorisee"}']
```

### Gestion globale des exceptions

```python
class ErrorHandlingMiddleware:
    """
    Middleware qui attrape les exceptions non gérées
    et retourne un 500 propre plutôt qu'un crash serveur.
    """
    
    def __init__(self, app, debug=False):
        self.app   = app
        self.debug = debug
    
    def __call__(self, environ, start_response):
        import sys, traceback
        try:
            return self.app(environ, start_response)
        except Exception as e:
            # Logger l'erreur
            print(f"[ERROR] Exception non géree : {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            
            if self.debug:
                # En développement : afficher le traceback
                detail = traceback.format_exc()
            else:
                # En production : ne pas exposer les détails
                detail = "Une erreur interne s'est produite."
            
            body = json.dumps({
                "erreur": "Erreur interne du serveur",
                "detail": detail,
            }, ensure_ascii=False).encode()
            
            start_response("500 Internal Server Error", [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
            ], sys.exc_info())
            
            return [body]
```

---

## 10. Implémentation complète et commentée

```python
# Voici comment tout s'assemble dans un vrai projet minimal

from router import Router  # notre classe Router ci-dessus
from middleware import LoggingMiddleware, TimingMiddleware  # du jour 13

# 1. Créer le router et enregistrer les routes
api = Router()

@api.get("/")
def racine(environ, start_response):
    ...

@api.get("/users")
def users_list(environ, start_response):
    ...

@api.get("/users/{id:int}")
def user_detail(environ, start_response, id):
    ...

# 2. Entourer le router avec des middlewares
from wsgiref.simple_server import make_server

application = LoggingMiddleware(
    TimingMiddleware(
        ErrorHandlingMiddleware(api, debug=True)
    )
)

# 3. Lancer le serveur
if __name__ == "__main__":
    with make_server("", 8000, application) as httpd:
        print("Serveur sur http://localhost:8000")
        api.afficher_routes()
        httpd.serve_forever()
```

---

## 11. Résumé

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROUTER WSGI EN RÉSUMÉ                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Un router est une application WSGI qui :                        │
│    1. Lit PATH_INFO et REQUEST_METHOD depuis environ             │
│    2. Compare PATH_INFO aux patterns enregistrés                 │
│    3. Extrait les paramètres dynamiques (ex: {id})              │
│    4. Appelle le handler correspondant avec ces paramètres       │
│    5. Retourne 404 si aucun pattern ne matche                    │
│    6. Retourne 405 si le path matche mais pas la méthode         │
│                                                                  │
│  Les stratégies de matching :                                    │
│    - Exact  : dict lookup, O(1), pas de params dynamiques        │
│    - Préfixe: startswith, utile pour monter des sous-apps        │
│    - Regex  : puissant, supporte {id:int}, {path:path}, etc.     │
│                                                                  │
│  En production, utilisez :                                       │
│    - Django URL patterns (similaire mais avec DSL Django)        │
│    - Flask routing (@app.route)                                  │
│    - FastAPI routing (@app.get, avec validation Pydantic)        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*Jour 14 — 10 juillet 2026 — Programme Backend Python/Django*
