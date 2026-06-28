"""
Jour 13 — Exercice : Middlewares WSGI
9 juillet 2026

Objectifs :
  - Implémenter LoggingMiddleware, AuthMiddleware, TimingMiddleware
  - Comprendre comment les middlewares s'enchaînent
  - Tester la chaîne complète avec simuler_requete()

Instructions :
  Cherchez les blocs marqués TODO et implémentez-les.
  Les blocs [FOURNI] sont déjà écrits — lisez-les pour comprendre le contexte.
  Lancez ce fichier : python exercice.py
  Tous les tests doivent passer.
"""

import json
import time
import sys
from io import BytesIO


# =============================================================================
# UTILITAIRES [FOURNI]
# =============================================================================

def simuler_requete(app, method="GET", path="/", query="", body=b"", headers=None):
    """
    [FOURNI] Simule une requête WSGI sans serveur réseau.

    Retourne (status_str, headers_dict, body_bytes, environ_utilise).
    On retourne aussi l'environ pour inspecter ce que les middlewares
    ont pu y écrire (ex: AUTH_USER).
    """
    if isinstance(body, str):
        body = body.encode("utf-8")

    environ = {
        "REQUEST_METHOD":  method.upper(),
        "PATH_INFO":       path,
        "QUERY_STRING":    query,
        "CONTENT_TYPE":    "application/json" if body else "",
        "CONTENT_LENGTH":  str(len(body)),
        "SERVER_NAME":     "localhost",
        "SERVER_PORT":     "8000",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "HTTP_HOST":       "localhost:8000",
        "REMOTE_ADDR":     "127.0.0.1",
        "wsgi.version":    (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input":      BytesIO(body),
        "wsgi.errors":     BytesIO(),
        "wsgi.multithread":  False,
        "wsgi.multiprocess": False,
        "wsgi.run_once":     False,
    }

    if headers:
        for key, value in headers.items():
            wsgi_key = "HTTP_" + key.upper().replace("-", "_")
            environ[wsgi_key] = value

    captured = {"status": None, "headers": {}}

    def start_response(status, response_headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = dict(response_headers)

    body_parts = app(environ, start_response)
    body_response = b"".join(body_parts)

    return captured["status"], captured["headers"], body_response, environ


def reponse_json(start_response, data, status="200 OK"):
    """[FOURNI] Envoyer une réponse JSON depuis un handler."""
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    start_response(status, [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


# =============================================================================
# APPLICATION DE BASE [FOURNI]
# =============================================================================

# Base de données fictive de ressources protégées
RESSOURCES = {
    "/api/secret":   {"message": "Ceci est une ressource protegee", "niveau": "confidentiel"},
    "/api/profil":   {"message": "Votre profil", "data": {"theme": "sombre", "langue": "fr"}},
    "/api/produits": {"produits": ["Laptop", "Souris", "Clavier"], "total": 3},
}


def application_principale(environ, start_response):
    """
    [FOURNI] Application WSGI de base, sans aucun middleware.

    Routes :
      GET /           → page d'accueil publique
      GET /health     → status de santé (publique)
      GET /api/*      → ressources protégées
      *               → 404
    """
    path   = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")

    if path == "/" and method == "GET":
        data = {
            "app": "Demo Middlewares WSGI",
            "status": "ok",
            "utilisateur": environ.get("AUTH_USER", "anonyme"),
        }
        return reponse_json(start_response, data)

    if path == "/health" and method == "GET":
        return reponse_json(start_response, {"status": "healthy", "timestamp": time.time()})

    if path.startswith("/api/"):
        ressource = RESSOURCES.get(path)
        if ressource:
            # On enrichit la réponse avec les infos d'auth injectées par le middleware
            data = dict(ressource)
            data["auth_user"] = environ.get("AUTH_USER", "anonyme")
            data["auth_role"] = environ.get("AUTH_ROLE", "?")
            return reponse_json(start_response, data)
        body = json.dumps({"erreur": f"Ressource {path} introuvable"}).encode()
        start_response("404 Not Found", [("Content-Type", "application/json")])
        return [body]

    body = json.dumps({"erreur": f"Route '{method} {path}' inconnue"}).encode()
    start_response("404 Not Found", [("Content-Type", "application/json")])
    return [body]


# =============================================================================
# EXERCICE 1 : LoggingMiddleware
# =============================================================================

class LoggingMiddleware:
    """
    Middleware qui logue chaque requête HTTP sur stderr.

    Format attendu :
      [2026-07-09 10:30:00] GET    /api/produits          200 OK               42.1ms

    Comportement attendu :
      - Logue TOUTES les requêtes (même celles rejetées par AuthMiddleware)
      - Mesure la durée totale (y compris le temps des autres middlewares)
      - Capture le status code retourné
    """

    def __init__(self, app, sortie=None):
        """
        app    : application WSGI suivante dans la chaîne
        sortie : fichier de sortie pour les logs (défaut: sys.stderr)
        """
        self.app    = app
        self.sortie = sortie or sys.stderr

    def __call__(self, environ, start_response):
        # TODO 1.1 : noter l'heure de début (utiliser time.perf_counter() pour la durée)
        debut = None  # TODO: remplacer None par time.perf_counter()

        # TODO 1.2 : extraire method et path depuis environ
        method = None  # TODO
        path   = None  # TODO

        # TODO 1.3 : créer une liste pour capturer le status de la réponse
        statut_capture = []

        def start_response_log(status, response_headers, exc_info=None):
            # TODO 1.4 : stocker le status dans statut_capture
            pass  # TODO: ajouter status dans statut_capture

            # Ne pas oublier d'appeler le vrai start_response !
            return start_response(status, response_headers, exc_info)

        # TODO 1.5 : appeler self.app avec environ et start_response_log
        resultat = None  # TODO: appeler self.app(...)

        # TODO 1.6 : calculer la durée en millisecondes
        duree_ms = 0  # TODO

        # TODO 1.7 : récupérer le status capturé (ou "???" si non capturé)
        status = "???"  # TODO: utiliser statut_capture

        # TODO 1.8 : formater et afficher le log
        # Format : [YYYY-MM-DD HH:MM:SS] METHOD   PATH                   STATUS               XXXms
        # Utilisez time.strftime('%Y-%m-%d %H:%M:%S') pour le timestamp
        # Utilisez print(..., file=self.sortie) pour écrire
        pass  # TODO: afficher le log

        # TODO 1.9 : retourner le résultat
        return None  # TODO: retourner resultat


# =============================================================================
# EXERCICE 2 : AuthMiddleware
# =============================================================================

# Tokens valides pour les tests (en production : base de données ou JWT)
TOKENS_VALIDES = {
    "token-alice-admin":  {"user": "alice",  "role": "admin"},
    "token-bob-user":     {"user": "bob",    "role": "user"},
    "token-carol-reader": {"user": "carol",  "role": "reader"},
}


class AuthMiddleware:
    """
    Middleware d'authentification par token Bearer.

    Comportement attendu :
      1. Si la route est dans routes_publiques → laisser passer sans vérifier
      2. Extraire l'en-tête HTTP_AUTHORIZATION depuis environ
      3. Vérifier qu'il commence par "Bearer "
      4. Vérifier que le token est dans self.tokens_valides
      5. Si valide : injecter AUTH_USER et AUTH_ROLE dans environ, puis appeler self.app
      6. Si invalide : retourner une réponse 401 (sans appeler self.app)
    """

    def __init__(self, app, tokens_valides, routes_publiques=None):
        """
        app              : application WSGI suivante
        tokens_valides   : dict {token: {user: ..., role: ...}}
        routes_publiques : liste de paths sans authentification requise
        """
        self.app              = app
        self.tokens_valides   = tokens_valides
        # TODO 2.1 : stocker routes_publiques comme un set
        # Si None est passé, utiliser {"/"} et "/health"} comme défaut
        self.routes_publiques = None  # TODO

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "/")

        # TODO 2.2 : si path est dans self.routes_publiques, appeler self.app et retourner
        pass  # TODO

        # TODO 2.3 : extraire l'en-tête d'autorisation depuis environ
        # Clé dans environ : "HTTP_AUTHORIZATION"
        auth_header = None  # TODO

        # TODO 2.4 : vérifier que auth_header commence par "Bearer "
        # Si non : retourner self._reponse_401(start_response, "message d'erreur")
        pass  # TODO

        # TODO 2.5 : extraire le token (tout ce qui suit "Bearer ")
        token = None  # TODO

        # TODO 2.6 : vérifier que le token est dans self.tokens_valides
        # Si non : retourner self._reponse_401(start_response, "Token invalide")
        user_info = None  # TODO

        # TODO 2.7 : injecter les infos utilisateur dans environ
        # environ["AUTH_USER"] = ...
        # environ["AUTH_ROLE"] = ...
        pass  # TODO

        # TODO 2.8 : appeler self.app et retourner le résultat
        return None  # TODO

    def _reponse_401(self, start_response, message):
        """[FOURNI] Retourne une réponse 401 Unauthorized."""
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


# =============================================================================
# EXERCICE 3 : TimingMiddleware
# =============================================================================

class TimingMiddleware:
    """
    Middleware qui ajoute un en-tête X-Response-Time à chaque réponse.

    L'en-tête doit avoir la forme : "42.35ms"

    Comportement attendu :
      - Mesurer le temps entre le début du traitement et l'envoi des en-têtes
      - Ajouter X-Response-Time dans les en-têtes de réponse
      - Si seuil_alerte_ms est défini et la durée dépasse ce seuil :
        afficher un avertissement sur stderr

    Contrainte technique importante :
      Pour ajouter un en-tête à la RÉPONSE, vous devez intercepter start_response
      et modifier response_headers avant de les transmettre.
    """

    def __init__(self, app, seuil_alerte_ms=None):
        """
        app              : application WSGI suivante
        seuil_alerte_ms  : si défini et dépassé, afficher un warning
        """
        self.app             = app
        self.seuil_alerte_ms = seuil_alerte_ms

    def __call__(self, environ, start_response):
        # TODO 3.1 : noter l'heure de début avec time.perf_counter()
        debut = None  # TODO

        def start_response_timing(status, response_headers, exc_info=None):
            # TODO 3.2 : calculer la durée en millisecondes
            duree_ms = 0  # TODO

            # TODO 3.3 : créer la liste des nouveaux en-têtes
            # Copier response_headers et ajouter ("X-Response-Time", "XXXms")
            nouveaux_headers = None  # TODO

            # TODO 3.4 : si seuil_alerte_ms est défini et dépassé, afficher un warning
            # Format : "[TIMING] SLOW: GET /path XXXms > seuil YYYms"
            pass  # TODO

            # TODO 3.5 : appeler le vrai start_response avec les nouveaux en-têtes
            return None  # TODO

        # TODO 3.6 : appeler self.app avec start_response_timing
        return None  # TODO


# =============================================================================
# EXERCICE 4 : Empiler les middlewares
# =============================================================================

def construire_application():
    """
    [FOURNI — mais vous devez compléter les TODO ci-dessus pour que ça marche]

    Empile les trois middlewares dans le bon ordre :
      LoggingMiddleware → TimingMiddleware → AuthMiddleware → application_principale

    L'ordre signifie que les requêtes passent dans cet ordre.
    """
    app = application_principale

    # Couche 1 (la plus proche de l'app) : Auth
    app = AuthMiddleware(
        app,
        tokens_valides=TOKENS_VALIDES,
        routes_publiques=["/", "/health"],
    )

    # Couche 2 : Timing (mesure après l'auth)
    app = TimingMiddleware(app, seuil_alerte_ms=100)

    # Couche 3 (la plus externe) : Logging (voit toutes les requêtes)
    app = LoggingMiddleware(app)

    return app


# =============================================================================
# TESTS [FOURNI]
# =============================================================================

def tester():
    """
    Suite de tests complète pour la chaîne de middlewares.

    Si tous vos TODO sont correctement implémentés, tous les assert passent.
    """
    print("=" * 65)
    print("  TESTS MIDDLEWARE WSGI — JOUR 13")
    print("=" * 65)

    app = construire_application()

    # ------------------------------------------------------------------
    print("\n--- TEST 1 : Routes publiques (sans token) ---")

    status, headers, body, env = simuler_requete(app, "GET", "/")
    print(f"  GET /  → {status}")
    assert status == "200 OK", f"[ECHEC] Attendu '200 OK', got '{status}'"
    print("  [OK] Route publique '/' accessible sans token")

    status, headers, body, env = simuler_requete(app, "GET", "/health")
    print(f"  GET /health  → {status}")
    assert status == "200 OK", f"[ECHEC] Attendu '200 OK', got '{status}'"
    print("  [OK] Route publique '/health' accessible sans token")

    # ------------------------------------------------------------------
    print("\n--- TEST 2 : Routes protégées sans token → 401 ---")

    status, headers, body, env = simuler_requete(app, "GET", "/api/produits")
    print(f"  GET /api/produits (sans token)  → {status}")
    assert status == "401 Unauthorized", \
        f"[ECHEC] Attendu '401 Unauthorized', got '{status}'"
    data = json.loads(body)
    assert "erreur" in data, "[ECHEC] La réponse 401 devrait contenir 'erreur'"
    print("  [OK] Route protégée refusée sans token")

    # Vérifier l'en-tête WWW-Authenticate
    assert "WWW-Authenticate" in headers, \
        "[ECHEC] En-tête WWW-Authenticate manquant dans la réponse 401"
    print(f"  [OK] En-tête WWW-Authenticate présent : {headers['WWW-Authenticate']}")

    # ------------------------------------------------------------------
    print("\n--- TEST 3 : Token invalide → 401 ---")

    status, headers, body, env = simuler_requete(
        app, "GET", "/api/produits",
        headers={"Authorization": "Bearer token-bidon-inexistant"}
    )
    print(f"  GET /api/produits (token invalide)  → {status}")
    assert status == "401 Unauthorized", \
        f"[ECHEC] Attendu '401 Unauthorized', got '{status}'"
    print("  [OK] Token invalide correctement rejeté")

    # Mauvais format (pas de "Bearer ")
    status, headers, body, env = simuler_requete(
        app, "GET", "/api/produits",
        headers={"Authorization": "token-alice-admin"}  # sans "Bearer "
    )
    print(f"  GET /api/produits (pas de 'Bearer ')  → {status}")
    assert status == "401 Unauthorized", \
        f"[ECHEC] Format sans 'Bearer ' devrait retourner 401, got '{status}'"
    print("  [OK] Format sans 'Bearer ' correctement rejeté")

    # ------------------------------------------------------------------
    print("\n--- TEST 4 : Token valide → 200 avec infos utilisateur ---")

    status, headers, body, env = simuler_requete(
        app, "GET", "/api/produits",
        headers={"Authorization": "Bearer token-alice-admin"}
    )
    print(f"  GET /api/produits (token alice)  → {status}")
    assert status == "200 OK", f"[ECHEC] Token valide devrait retourner 200, got '{status}'"

    data = json.loads(body)
    assert data.get("auth_user") == "alice", \
        f"[ECHEC] auth_user devrait être 'alice', got '{data.get('auth_user')}'"
    assert data.get("auth_role") == "admin", \
        f"[ECHEC] auth_role devrait être 'admin', got '{data.get('auth_role')}'"
    print(f"  [OK] alice/admin connectée : auth_user={data['auth_user']}, auth_role={data['auth_role']}")

    # Tester avec un autre utilisateur
    status, headers, body, env = simuler_requete(
        app, "GET", "/api/profil",
        headers={"Authorization": "Bearer token-bob-user"}
    )
    assert status == "200 OK"
    data = json.loads(body)
    assert data.get("auth_user") == "bob"
    assert data.get("auth_role") == "user"
    print(f"  [OK] bob/user connecté : auth_user={data['auth_user']}, auth_role={data['auth_role']}")

    # ------------------------------------------------------------------
    print("\n--- TEST 5 : En-tête X-Response-Time présent ---")

    status, headers, body, env = simuler_requete(
        app, "GET", "/",
    )
    print(f"  En-têtes reçus : {list(headers.keys())}")
    assert "X-Response-Time" in headers, \
        "[ECHEC] L'en-tête X-Response-Time devrait être présent dans la réponse"

    timing_val = headers["X-Response-Time"]
    print(f"  [OK] X-Response-Time = {timing_val}")
    assert "ms" in timing_val, \
        f"[ECHEC] X-Response-Time devrait contenir 'ms', got '{timing_val}'"

    # Vérifier que c'est un nombre valide
    timing_num = float(timing_val.replace("ms", ""))
    assert timing_num >= 0, f"[ECHEC] Timing devrait être >= 0, got {timing_num}"
    print(f"  [OK] Timing valide : {timing_num:.2f}ms")

    # ------------------------------------------------------------------
    print("\n--- TEST 6 : Route inexistante → 404 ---")

    status, headers, body, env = simuler_requete(
        app, "GET", "/route-inconnue",
        headers={"Authorization": "Bearer token-alice-admin"}
    )
    print(f"  GET /route-inconnue  → {status}")
    assert status == "404 Not Found", \
        f"[ECHEC] Route inexistante devrait retourner 404, got '{status}'"
    print("  [OK] 404 retourné pour route inconnue")

    # ------------------------------------------------------------------
    print("\n--- TEST 7 : Vérifier que le Logging ne casse pas les réponses ---")

    # Le LoggingMiddleware ne devrait pas modifier le body ni le status
    for token, info in TOKENS_VALIDES.items():
        status, headers, body, env = simuler_requete(
            app, "GET", "/api/produits",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert status == "200 OK", \
            f"[ECHEC] LoggingMiddleware casse la réponse pour {info['user']}"
    print("  [OK] LoggingMiddleware ne modifie pas les réponses")

    # ------------------------------------------------------------------
    print("\n--- TEST 8 : Chaîne complète avec plusieurs middlewares ---")

    # Une requête passe par : Logging → Timing → Auth → App
    # On vérifie que TOUT fonctionne ensemble
    status, headers, body, env = simuler_requete(
        app, "GET", "/api/secret",
        headers={"Authorization": "Bearer token-carol-reader"}
    )
    assert status == "200 OK"
    assert "X-Response-Time" in headers  # Timing a fait son travail
    data = json.loads(body)
    assert data["auth_user"] == "carol"  # Auth a injecté les infos
    assert "message" in data             # L'app a répondu
    print(f"  [OK] Chaîne complète : status={status}, user={data['auth_user']}, timing={headers['X-Response-Time']}")

    # ------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  TOUS LES TESTS PASSES ! Middlewares correctement implementes.")
    print("=" * 65)
    print()
    print("Verifiez aussi que les logs s'affichaient sur stderr pendant les tests.")
    print("Vous devriez voir quelque chose comme :")
    print("  [2026-07-09 10:30:00] GET    /                      200 OK               0.1ms")


# =============================================================================
# BONUS : Middleware de rate limiting
# =============================================================================

class RateLimitMiddleware:
    """
    [BONUS — À implémenter si vous avez terminé les exercices principaux]

    Middleware qui limite le nombre de requêtes par IP.

    Comportement :
      - Chaque adresse IP peut faire max `limite` requêtes par `fenetre_secondes`
      - Si la limite est dépassée → 429 Too Many Requests
      - L'en-tête X-RateLimit-Remaining indique les requêtes restantes

    Conseil : utilisez un dict {ip: [timestamps]} pour stocker l'historique.
    Nettoyez les timestamps trop anciens à chaque requête.
    """

    def __init__(self, app, limite=10, fenetre_secondes=60):
        self.app               = app
        self.limite            = limite
        self.fenetre_secondes  = fenetre_secondes
        self.historique        = {}  # {ip: [timestamps]}

    def __call__(self, environ, start_response):
        # BONUS TODO : implémenter le rate limiting
        # 1. Extraire l'IP depuis environ["REMOTE_ADDR"]
        # 2. Nettoyer les timestamps anciens (> fenetre_secondes)
        # 3. Compter les requêtes récentes
        # 4. Si >= limite → retourner 429
        # 5. Sinon : ajouter le timestamp courant et appeler self.app
        # 6. Ajouter X-RateLimit-Remaining dans les en-têtes de réponse
        raise NotImplementedError("À implémenter (bonus)")


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

if __name__ == "__main__":
    print("\nLancement des tests de middlewares...\n")
    print("(Les logs des requêtes s'affichent sur stderr — regardez le terminal)\n")
    tester()
