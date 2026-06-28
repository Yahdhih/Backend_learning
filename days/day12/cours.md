# Jour 12 — WSGI : Le protocole entre Python et le serveur web (8 juillet 2026)

---

## Table des matières

1. [Pourquoi WSGI existe-t-il ?](#1-pourquoi-wsgi-existe-t-il)
2. [Le contrat WSGI : callable(environ, start_response)](#2-le-contrat-wsgi)
3. [Le dictionnaire environ : toutes les clés expliquées](#3-le-dictionnaire-environ)
4. [La fonction start_response](#4-la-fonction-start_response)
5. [Écrire une application WSGI minimale](#5-écrire-une-application-wsgi-minimale)
6. [Lancer avec wsgiref.simple_server](#6-lancer-avec-wsgiref)
7. [WSGI vs ASGI : une brève introduction](#7-wsgi-vs-asgi)
8. [Résumé et points clés](#8-résumé)

---

## 1. Pourquoi WSGI existe-t-il ?

### Le problème historique

Avant 2003, le monde Python web était fragmenté. Chaque framework (Zope, Twisted, Quixote…) avait sa propre façon de parler aux serveurs web. Pour déployer une application Flask (si elle avait existé à l'époque), vous deviez utiliser le serveur web conçu *pour* Flask. Idem pour Django, idem pour tous les autres.

Cela signifiait :
- Impossible de mélanger les outils (un load balancer Apache avec une appli Twisted, par exemple)
- Chaque serveur réinventait la roue pour parser les requêtes HTTP
- Les développeurs étaient enfermés dans un écosystème fermé

### La solution : PEP 333 (et PEP 3333)

En 2003, Phillip J. Eby propose la **PEP 333 — Python Web Server Gateway Interface**. L'idée est simple et brillante : définir un **contrat universel** entre les serveurs web et les applications Python.

> "WSGI is a simple and universal interface between web servers and web applications or frameworks."
> — PEP 3333

La PEP 3333 (2010) est simplement la mise à jour pour Python 3 (encodage des chaînes, bytes vs str).

### L'analogie parfaite

Pensez à une prise électrique. Peu importe si vous branchez une lampe française, un chargeur américain (avec adaptateur), une perceuse allemande — la prise respecte un standard. WSGI est la "prise électrique" du web Python.

```
SANS WSGI :                    AVEC WSGI :
                               
Django  <-> Apache             Django  ]
Pylons  <-> Nginx              Flask   ] ---- WSGI ---- [ Apache
Twisted <-> Lighttpd           Pyramid ]               [ Nginx
                                                       [ Gunicorn
```

---

## 2. Le contrat WSGI

### La spécification en une phrase

Une application WSGI est **n'importe quel objet Python appelable** (fonction, méthode, classe avec `__call__`) qui accepte exactement **deux arguments** et retourne un **itérable de bytes**.

```python
def application(environ, start_response):
    # ... logique ...
    return [b"Hello, World!"]
```

C'est tout. Voilà WSGI dans sa forme la plus pure.

### Les trois acteurs

```
                    ┌─────────────────────────────────────┐
                    │           FLUX D'UNE REQUÊTE         │
                    └─────────────────────────────────────┘

  ┌─────────┐    HTTP     ┌──────────────┐   WSGI   ┌─────────────────┐
  │         │  ────────>  │  Web Server  │ ───────>  │  Python App     │
  │ Browser │             │  (Nginx /    │           │  (Django /      │
  │         │  <────────  │   Apache)    │ <───────  │   Flask / vous) │
  └─────────┘    HTTP     └──────────────┘   WSGI   └─────────────────┘
                                │
                                │ délègue à
                                ▼
                         ┌──────────────┐
                         │ WSGI Server  │
                         │ (Gunicorn /  │
                         │  uWSGI /     │
                         │  wsgiref)    │
                         └──────────────┘

Rôles :
  Web Server  → reçoit le TCP/HTTP brut, gère TLS, fichiers statiques
  WSGI Server → traduit HTTP en appel Python (l'interface)
  Python App  → votre code : vos vues, votre logique métier
```

### Pourquoi un callable ?

Parce que Python est flexible. Voici quatre formes équivalentes de "application WSGI" :

```python
# Forme 1 : fonction simple (la plus courante pour apprendre)
def app_fonction(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Bonjour depuis une fonction"]


# Forme 2 : classe avec __call__
class AppClasse:
    def __call__(self, environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"Bonjour depuis une classe"]

app_classe = AppClasse()  # l'instance est le callable


# Forme 3 : méthode d'instance
class MonApplication:
    def handle(self, environ, start_response):
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"Bonjour depuis une methode"]

mon_app = MonApplication()
# on passe mon_app.handle comme application WSGI


# Forme 4 : lambda (déconseillée en production, mais légale)
app_lambda = lambda env, sr: (sr("200 OK", [("Content-Type", "text/plain")]) or [b"Bonjour"])
```

Django utilise la forme classe. Flask utilise la forme classe (l'objet `Flask` a un `__call__`). Pour apprendre, on commence par les fonctions.

---

## 3. Le dictionnaire environ

`environ` est un dictionnaire Python standard qui contient **tout ce que le serveur sait sur la requête entrante**. C'est l'équivalent de `$_SERVER` en PHP, ou de `request.META` en Django (qui est littéralement `environ` + quelques ajouts Django).

### Les variables CGI héritées

WSGI s'inspire de l'interface CGI. Ces variables viennent de là :

```python
def inspecter_environ(environ, start_response):
    """Application qui affiche tout l'environ pour comprendre."""
    
    # --- Variables de requête ---
    method      = environ['REQUEST_METHOD']   # 'GET', 'POST', 'PUT', 'DELETE', etc.
    path        = environ['PATH_INFO']        # '/api/users/42'
    query       = environ['QUERY_STRING']     # 'page=2&limit=10' (sans le ?)
    content_type= environ.get('CONTENT_TYPE', '')  # 'application/json'
    content_len = environ.get('CONTENT_LENGTH', '') # '128' (en string !)
    
    # --- Variables de serveur ---
    server_name = environ['SERVER_NAME']      # 'localhost' ou '192.168.1.1'
    server_port = environ['SERVER_PORT']      # '8000' (en string !)
    server_proto= environ['SERVER_PROTOCOL']  # 'HTTP/1.1'
    script_name = environ['SCRIPT_NAME']      # '' ou '/myapp' (si monté sous-chemin)
    
    # --- Variables WSGI ---
    wsgi_version = environ['wsgi.version']    # (1, 0)
    wsgi_url_scheme = environ['wsgi.url_scheme'] # 'http' ou 'https'
    wsgi_input  = environ['wsgi.input']       # objet fichier : le body de la requête
    wsgi_errors = environ['wsgi.errors']      # objet fichier : pour écrire les erreurs
    wsgi_multithread  = environ['wsgi.multithread']  # True si serveur multi-thread
    wsgi_multiprocess = environ['wsgi.multiprocess'] # True si serveur multi-process
    wsgi_run_once     = environ['wsgi.run_once']     # True si mode CGI
    
    # --- En-têtes HTTP : préfixées HTTP_ ---
    # L'en-tête "Accept" devient "HTTP_ACCEPT"
    # L'en-tête "User-Agent" devient "HTTP_USER_AGENT"
    # Les tirets deviennent des underscores, tout en majuscules
    accept      = environ.get('HTTP_ACCEPT', '*/*')
    user_agent  = environ.get('HTTP_USER_AGENT', '')
    host        = environ.get('HTTP_HOST', '')
    auth_header = environ.get('HTTP_AUTHORIZATION', '')  # "Bearer abc123"
    cookie      = environ.get('HTTP_COOKIE', '')
    
    start_response("200 OK", [("Content-Type", "text/plain")])
    
    lignes = [
        f"Methode    : {method}",
        f"Chemin     : {path}",
        f"Query      : {query}",
        f"Host       : {host}",
        f"User-Agent : {user_agent}",
        f"Auth       : {auth_header}",
    ]
    return ["\n".join(lignes).encode("utf-8")]
```

### Lire le body de la requête

Pour les requêtes POST/PUT, le corps de la requête se lit depuis `wsgi.input` :

```python
def lire_body(environ, start_response):
    """Lire le body d'une requête POST."""
    
    method = environ['REQUEST_METHOD']
    
    if method == 'POST':
        # ATTENTION : content_length peut être vide !
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0) or 0)
        except ValueError:
            content_length = 0
        
        # wsgi.input est un objet fichier-like (pas un vrai fichier)
        body_bytes = environ['wsgi.input'].read(content_length)
        body_str = body_bytes.decode('utf-8')
        
        # Si c'est du JSON :
        import json
        try:
            data = json.loads(body_str)
            reponse = f"Recu : {data}"
        except json.JSONDecodeError:
            reponse = f"Body brut : {body_str}"
    else:
        reponse = "Pas de body (methode GET)"
    
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [reponse.encode('utf-8')]
```

### Parser la query string

```python
from urllib.parse import parse_qs, parse_qsl

def avec_query(environ, start_response):
    """Extraire les paramètres de query string."""
    
    query_string = environ.get('QUERY_STRING', '')
    # ex: "name=Alice&age=30&tag=python&tag=django"
    
    # parse_qs : retourne des listes (gère les valeurs multiples)
    params = parse_qs(query_string)
    # {'name': ['Alice'], 'age': ['30'], 'tag': ['python', 'django']}
    
    # parse_qsl : retourne une liste de tuples (ordre préservé)
    params_list = parse_qsl(query_string)
    # [('name', 'Alice'), ('age', '30'), ('tag', 'python'), ('tag', 'django')]
    
    # Accéder à une valeur (première occurrence) :
    name = params.get('name', ['anonyme'])[0]
    age  = params.get('age',  ['inconnu'])[0]
    
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8")])
    return [f"Bonjour {name}, age {age}".encode('utf-8')]
```

---

## 4. La fonction start_response

`start_response` est une fonction **fournie par le serveur WSGI** et passée à votre application. Vous l'appelez pour envoyer le statut HTTP et les en-têtes de réponse.

### Signature

```python
start_response(status, response_headers, exc_info=None)
```

- `status` : une chaîne `"CODE Raison"` — ex: `"200 OK"`, `"404 Not Found"`, `"302 Found"`
- `response_headers` : une liste de tuples `(nom, valeur)` — ex: `[("Content-Type", "text/html")]`
- `exc_info` : utilisé uniquement pour propager des exceptions (cas avancé)

### Règles importantes

```python
def regles_start_response(environ, start_response):
    """Démonstration des règles de start_response."""
    
    # REGLE 1 : Appeler start_response AVANT de retourner le body
    start_response("200 OK", [
        ("Content-Type", "text/plain"),
        ("Content-Length", "13"),      # longueur en bytes du body
        ("X-Custom-Header", "valeur"), # en-têtes personnalisées : OK
    ])
    
    # REGLE 2 : Les noms d'en-têtes sont insensibles à la casse
    # "content-type", "Content-Type", "CONTENT-TYPE" : tous valides
    
    # REGLE 3 : Ne PAS inclure ces en-têtes (gérés par le serveur) :
    # - "Status" (c'est le premier argument, pas un en-tête)
    # - "Transfer-Encoding" (géré par le serveur)
    
    # REGLE 4 : Content-Length doit correspondre exactement à la taille du body
    body = b"Hello, World!"  # 13 bytes
    return [body]
```

### Codes de statut courants

```python
# Voici un dictionnaire de référence pour vos applications WSGI
STATUS_CODES = {
    200: "200 OK",
    201: "201 Created",
    204: "204 No Content",
    301: "301 Moved Permanently",
    302: "302 Found",
    304: "304 Not Modified",
    400: "400 Bad Request",
    401: "401 Unauthorized",
    403: "403 Forbidden",
    404: "404 Not Found",
    405: "405 Method Not Allowed",
    409: "409 Conflict",
    422: "422 Unprocessable Entity",
    500: "500 Internal Server Error",
    503: "503 Service Unavailable",
}

def reponse_json(environ, start_response, data: dict, status: int = 200):
    """Fonction utilitaire : envoyer une réponse JSON."""
    import json
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    start_response(
        STATUS_CODES.get(status, f"{status} Unknown"),
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
        ]
    )
    return [body]
```

---

## 5. Écrire une application WSGI minimale

### Version zéro : Hello World

```python
# hello_wsgi.py

def application(environ, start_response):
    """L'application WSGI la plus simple possible."""
    status = "200 OK"
    headers = [("Content-Type", "text/plain; charset=utf-8")]
    start_response(status, headers)
    return [b"Bonjour depuis WSGI !"]
```

### Version avec routing manuel

```python
# router_simple.py
import json
from urllib.parse import parse_qs

# Fausse base de données
USERS = [
    {"id": 1, "name": "Alice", "role": "admin"},
    {"id": 2, "name": "Bob",   "role": "user"},
    {"id": 3, "name": "Carol", "role": "user"},
]


def application(environ, start_response):
    """Application WSGI avec routing basique."""
    
    path   = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')
    
    # Route : GET /
    if path == '/' and method == 'GET':
        return page_accueil(environ, start_response)
    
    # Route : GET /users
    elif path == '/users' and method == 'GET':
        return liste_users(environ, start_response)
    
    # Route : GET /users/1 (parsing d'ID)
    elif path.startswith('/users/') and method == 'GET':
        user_id_str = path[len('/users/'):]
        try:
            user_id = int(user_id_str)
            return detail_user(environ, start_response, user_id)
        except ValueError:
            return erreur_400(environ, start_response, "ID invalide")
    
    # Route inconnue : 404
    else:
        return erreur_404(environ, start_response)


def page_accueil(environ, start_response):
    body = b"<h1>Bienvenue sur mon API WSGI</h1>"
    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    return [body]


def liste_users(environ, start_response):
    body = json.dumps(USERS, ensure_ascii=False).encode('utf-8')
    start_response("200 OK", [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


def detail_user(environ, start_response, user_id):
    user = next((u for u in USERS if u['id'] == user_id), None)
    if user is None:
        return erreur_404(environ, start_response)
    body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    start_response("200 OK", [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


def erreur_404(environ, start_response):
    body = json.dumps({"error": "Not Found"}).encode('utf-8')
    start_response("404 Not Found", [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


def erreur_400(environ, start_response, message):
    body = json.dumps({"error": message}).encode('utf-8')
    start_response("400 Bad Request", [
        ("Content-Type", "application/json"),
        ("Content-Length", str(len(body))),
    ])
    return [body]
```

### Gestion des erreurs avec exc_info

```python
import sys

def application_robuste(environ, start_response):
    """Application qui gère les exceptions proprement."""
    try:
        path = environ['PATH_INFO']
        if path == '/crash':
            raise ValueError("Erreur intentionnelle pour la demo")
        
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"Tout va bien !"]
    
    except Exception:
        # exc_info=sys.exc_info() permet au serveur de logger l'erreur
        start_response(
            "500 Internal Server Error",
            [("Content-Type", "text/plain")],
            sys.exc_info()   # <--- ici : on passe l'exception au serveur
        )
        return [b"Une erreur interne s'est produite."]
```

---

## 6. Lancer avec wsgiref

`wsgiref` est la bibliothèque standard Python pour WSGI. Elle inclut un serveur de développement simple.

### Serveur basique

```python
# run_dev.py
from wsgiref.simple_server import make_server
from mon_app import application  # votre callable WSGI

if __name__ == '__main__':
    HOST = 'localhost'
    PORT = 8000
    
    # make_server(host, port, app) -> objet serveur WSGI
    with make_server(HOST, PORT, application) as httpd:
        print(f"Serveur de developpement sur http://{HOST}:{PORT}/")
        print("Ctrl+C pour arreter")
        try:
            httpd.serve_forever()   # boucle infinie
        except KeyboardInterrupt:
            print("\nServeur arrete.")
```

### Faire une requête unique (pour les tests)

```python
from wsgiref.simple_server import make_server

def application(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Test OK"]

# Serveur qui répond à UNE seule requête puis s'arrête
with make_server('localhost', 8001, application) as httpd:
    httpd.handle_request()  # une seule requête
```

### Utiliser wsgiref.validate pour débugger

```python
from wsgiref.validate import validator
from wsgiref.simple_server import make_server

def mon_app(environ, start_response):
    # Intentionnellement buggé : oubli du Content-Type
    start_response("200 OK", [])
    return [b"Oops, pas de Content-Type"]

# validator() entoure votre app et vérifie la conformité WSGI
# Elle lèvera des AssertionError si vous violez la spec
app_validee = validator(mon_app)

with make_server('localhost', 8002, app_validee) as httpd:
    httpd.handle_request()
```

### Simuler une requête sans réseau (pour les tests unitaires)

```python
from io import BytesIO
from wsgiref.util import setup_testing_defaults

def simuler_requete(app, method='GET', path='/', query='', body=b'', headers=None):
    """
    Simule une requête WSGI sans serveur réseau.
    Retourne (status, headers, body).
    """
    environ = {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': query,
        'CONTENT_LENGTH': str(len(body)),
        'CONTENT_TYPE': 'application/json' if body else '',
        'wsgi.input': BytesIO(body),
        'wsgi.errors': BytesIO(),
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '8000',
        'SERVER_PROTOCOL': 'HTTP/1.1',
    }
    
    # Ajouter les en-têtes HTTP_ custom
    if headers:
        for key, value in headers.items():
            key_wsgi = 'HTTP_' + key.upper().replace('-', '_')
            environ[key_wsgi] = value
    
    # Capturer ce que start_response reçoit
    captured_status = []
    captured_headers = []
    
    def start_response(status, response_headers, exc_info=None):
        captured_status.append(status)
        captured_headers.extend(response_headers)
    
    # Appeler l'application
    body_parts = app(environ, start_response)
    body_response = b"".join(body_parts)
    
    return captured_status[0], dict(captured_headers), body_response


# Exemple d'utilisation :
if __name__ == '__main__':
    from mon_app import application
    
    status, headers, body = simuler_requete(application, 'GET', '/users')
    print(f"Status: {status}")
    print(f"Headers: {headers}")
    print(f"Body: {body.decode()}")
```

---

## 7. WSGI vs ASGI

### Le problème de WSGI : synchrone et bloquant

WSGI est **synchrone** par design. Quand votre application WSGI appelle `time.sleep(5)` ou fait une requête SQL lente, elle bloque le thread entier. Gunicorn gère ça en démarrant plusieurs workers (processus), mais ce n'est pas efficace pour les connexions longues (WebSockets, Server-Sent Events).

```
WSGI (synchrone) :
                    Worker 1 : requête A [====== SQL 500ms ======] réponse A
                    Worker 2 : requête B [== traitement ==] réponse B
                    Worker 3 : IDLE (en attente)
                    
→ Pour 100 connexions simultanées : 100 workers → beaucoup de RAM
```

### ASGI : le successeur asynchrone

**ASGI (Asynchronous Server Gateway Interface)** est la réponse moderne à ce problème. Défini par Django Channels, maintenant géré par Encode (les auteurs de FastAPI/Starlette).

```python
# Application WSGI (synchrone)
def wsgi_app(environ, start_response):
    import time
    time.sleep(1)  # bloque le thread
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Fini"]


# Application ASGI (asynchrone)
async def asgi_app(scope, receive, send):
    import asyncio
    await asyncio.sleep(1)  # libère le thread pendant l'attente !
    
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [(b'content-type', b'text/plain')],
    })
    await send({
        'type': 'http.response.body',
        'body': b"Fini",
    })
```

### Tableau comparatif

| Aspect              | WSGI                        | ASGI                            |
|---------------------|-----------------------------|---------------------------------|
| Style               | Synchrone                   | Asynchrone (async/await)        |
| PEP/Spec            | PEP 3333                    | ASGI spec (Encode)              |
| Serveurs            | Gunicorn, uWSGI, wsgiref    | Uvicorn, Daphne, Hypercorn      |
| Frameworks          | Django, Flask, Pyramid      | FastAPI, Starlette, Django 3.1+ |
| WebSockets          | Non (hack possible)         | Natif                           |
| Long polling        | Difficile                   | Facile                          |
| Performances I/O    | Limitées                    | Excellentes                     |
| Courbe d'apprentissage | Faible                   | Moyenne (async/await requis)    |

### Pourquoi apprendre WSGI en 2026 ?

- Django tourne toujours en WSGI par défaut (et le fera longtemps)
- Comprendre WSGI vous donne la base pour comprendre ASGI
- Gunicorn + Nginx : le combo le plus déployé en production Python
- La plupart des jobs Django en production utilisent encore WSGI

---

## 8. Résumé et points clés

### Ce que vous devez retenir

```
┌─────────────────────────────────────────────────────────┐
│                    WSGI EN RÉSUMÉ                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. WSGI = contrat universel Python ↔ serveur web        │
│                                                          │
│  2. Une app WSGI = callable(environ, start_response)     │
│     qui retourne un itérable de bytes                    │
│                                                          │
│  3. environ = dict avec TOUTES les infos de la requête   │
│     - REQUEST_METHOD, PATH_INFO, QUERY_STRING            │
│     - HTTP_* pour les en-têtes                           │
│     - wsgi.input pour le body                            │
│                                                          │
│  4. start_response(status, headers) s'appelle AVANT      │
│     de retourner le body                                 │
│                                                          │
│  5. wsgiref.simple_server = serveur de DEV uniquement    │
│     En prod : Gunicorn, uWSGI                            │
│                                                          │
│  6. ASGI = la version async de WSGI (Django 3.1+)        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Le flux complet d'une requête GET /users

```
1. Navigateur envoie :
   GET /users?page=1 HTTP/1.1
   Host: example.com
   Accept: application/json

2. Nginx reçoit la connexion TCP, parse l'HTTP

3. Nginx transmet à Gunicorn (via socket Unix ou TCP)

4. Gunicorn construit environ :
   {
     'REQUEST_METHOD': 'GET',
     'PATH_INFO': '/users',
     'QUERY_STRING': 'page=1',
     'HTTP_HOST': 'example.com',
     'HTTP_ACCEPT': 'application/json',
     'wsgi.input': <BytesIO>,
     ...
   }

5. Gunicorn appelle : response = your_app(environ, start_response)

6. Votre app appelle start_response("200 OK", [...headers...])

7. Votre app retourne [b'[{"id":1,...}]']

8. Gunicorn transmet la réponse à Nginx

9. Nginx transmet au navigateur
```

### Ressources pour aller plus loin

- [PEP 3333](https://peps.python.org/pep-3333/) — la spec officielle (lisible en 30 min)
- [wsgiref documentation](https://docs.python.org/3/library/wsgiref.html) — stdlib Python
- [Gunicorn](https://gunicorn.org/) — le serveur WSGI de production le plus utilisé
- [Whitenoise](https://whitenoise.readthedocs.io/) — servir les fichiers statiques via WSGI
- [ASGI spec](https://asgi.readthedocs.io/) — pour comprendre la suite

---

*Jour 12 — 8 juillet 2026 — Programme Backend Python/Django*
