# Day 39 — Exercice : Session Auth from Scratch avec Django
# Objectif : Implémenter un système d'authentification par session complet

"""
Architecture :
- Vue login   : valide les credentials, crée une session
- Vue logout  : détruit la session
- Middleware  : vérifie la session sur chaque requête
- Décorateur  : @session_required
- Tests       : avec le client Django

Ce fichier est auto-contenu ; lancez-le avec :
    python manage.py shell < exercice.py
ou exécutez la suite de tests directement :
    python exercice.py
"""

import hashlib
import hmac
import json
import time
import uuid
from functools import wraps
from unittest import TestCase, mock
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# 1. Stockage de sessions (simulé en mémoire pour l'exercice)
# ---------------------------------------------------------------------------

SESSION_STORE: dict[str, dict] = {}
SESSION_TTL = 3600  # secondes


def creer_session(user_id: int, username: str) -> str:
    """Crée une nouvelle session et retourne le session_id."""
    session_id = str(uuid.uuid4())
    SESSION_STORE[session_id] = {
        "user_id": user_id,
        "username": username,
        "created_at": time.time(),
        "expires_at": time.time() + SESSION_TTL,
    }
    return session_id


def recuperer_session(session_id: str) -> dict | None:
    """Récupère une session valide. Retourne None si invalide ou expirée."""
    session = SESSION_STORE.get(session_id)
    if not session:
        return None
    if time.time() > session["expires_at"]:
        # Nettoyer la session expirée
        del SESSION_STORE[session_id]
        return None
    return session


def detruire_session(session_id: str) -> None:
    """Supprime une session du store."""
    SESSION_STORE.pop(session_id, None)


# ---------------------------------------------------------------------------
# 2. Base de données utilisateurs simulée
# ---------------------------------------------------------------------------

USERS_DB = {
    "alice": {
        "id": 1,
        "username": "alice",
        # hash SHA-256 de "motdepasse123" — en prod on utilise bcrypt/argon2
        "password_hash": hashlib.sha256(b"motdepasse123").hexdigest(),
    },
    "bob": {
        "id": 2,
        "username": "bob",
        "password_hash": hashlib.sha256(b"secret456").hexdigest(),
    },
}


def verifier_credentials(username: str, password: str) -> dict | None:
    """Retourne l'utilisateur si les credentials sont corrects, sinon None."""
    user = USERS_DB.get(username)
    if not user:
        return None
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    # hmac.compare_digest évite les timing attacks
    if hmac.compare_digest(user["password_hash"], password_hash):
        return user
    return None


# ---------------------------------------------------------------------------
# 3. Simulateur de requête/réponse HTTP (sans Django réel pour l'exercice)
# ---------------------------------------------------------------------------

class FakeRequest:
    """Simule une requête HTTP Django simplifiée."""

    def __init__(self, method="GET", path="/", body=None, cookies=None):
        self.method = method
        self.path = path
        self.body = body or {}
        self.COOKIES = cookies or {}
        self.session_data: dict | None = None  # rempli par le middleware
        self.user = None  # rempli par le middleware

    def POST(self):
        return self.body


class FakeResponse:
    """Simule une réponse HTTP Django simplifiée."""

    def __init__(self, status_code: int, data: dict | str = None):
        self.status_code = status_code
        self.data = data or {}
        self.cookies: dict[str, str] = {}

    def set_cookie(self, name: str, value: str, httponly=True, samesite="Lax"):
        self.cookies[name] = {
            "value": value,
            "httponly": httponly,
            "samesite": samesite,
        }

    def delete_cookie(self, name: str):
        self.cookies[name] = {"value": "", "max_age": 0}

    def __repr__(self):
        return f"<Response {self.status_code}>"


# ---------------------------------------------------------------------------
# 4. Middleware de vérification de session
# ---------------------------------------------------------------------------

SESSION_COOKIE_NAME = "sessionid"


class SessionMiddleware:
    """
    Middleware qui lit le cookie de session et attache les données
    à la requête entrante.

    Dans Django réel : process_request est appelé avant la vue,
    process_response après.
    """

    def __init__(self, get_response=None):
        self.get_response = get_response

    def process_request(self, request: FakeRequest) -> None:
        """Attache la session à la requête."""
        session_id = request.COOKIES.get(SESSION_COOKIE_NAME)
        if session_id:
            session = recuperer_session(session_id)
            request.session_data = session
            if session:
                request.user = {
                    "id": session["user_id"],
                    "username": session["username"],
                    "is_authenticated": True,
                }
        else:
            request.session_data = None
            request.user = {"is_authenticated": False}

    def process_response(self, request: FakeRequest, response: FakeResponse) -> FakeResponse:
        """Ici on pourrait renouveler le cookie si la session est active."""
        return response

    def __call__(self, request: FakeRequest):
        """Interface Django standard."""
        self.process_request(request)
        response = self.get_response(request) if self.get_response else FakeResponse(200)
        return self.process_response(request, response)


# ---------------------------------------------------------------------------
# 5. Décorateur @session_required
# ---------------------------------------------------------------------------

def session_required(view_func):
    """
    Décorateur qui redirige vers /login/ si l'utilisateur n'est pas connecté.

    Usage :
        @session_required
        def ma_vue(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request: FakeRequest, *args, **kwargs):
        # S'assurer que le middleware a été exécuté
        if not hasattr(request, "user"):
            middleware = SessionMiddleware()
            middleware.process_request(request)

        user = getattr(request, "user", None)
        if not user or not user.get("is_authenticated"):
            return FakeResponse(302, {"redirect": "/login/"})

        return view_func(request, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# 6. Vues Django (simulées)
# ---------------------------------------------------------------------------

def vue_login(request: FakeRequest) -> FakeResponse:
    """
    POST /login/ — Authentifie l'utilisateur et crée une session.

    Body attendu : {"username": "...", "password": "..."}
    """
    if request.method != "POST":
        return FakeResponse(405, {"error": "Méthode non autorisée"})

    username = request.body.get("username", "").strip()
    password = request.body.get("password", "")

    if not username or not password:
        return FakeResponse(400, {"error": "username et password requis"})

    user = verifier_credentials(username, password)
    if not user:
        # Délai constant pour résister aux timing attacks
        time.sleep(0.01)
        return FakeResponse(401, {"error": "Credentials invalides"})

    # Créer la session
    session_id = creer_session(user["id"], user["username"])

    response = FakeResponse(200, {"message": f"Bienvenue {username} !"})
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        httponly=True,   # inaccessible au JavaScript
        samesite="Lax",  # protection CSRF de base
    )
    return response


def vue_logout(request: FakeRequest) -> FakeResponse:
    """
    POST /logout/ — Détruit la session courante.
    """
    if request.method != "POST":
        return FakeResponse(405, {"error": "Méthode non autorisée"})

    session_id = request.COOKIES.get(SESSION_COOKIE_NAME)
    if session_id:
        detruire_session(session_id)

    response = FakeResponse(200, {"message": "Déconnecté"})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@session_required
def vue_profil(request: FakeRequest) -> FakeResponse:
    """
    GET /profil/ — Retourne le profil de l'utilisateur connecté.
    Protégé par @session_required.
    """
    return FakeResponse(200, {
        "user_id": request.user["id"],
        "username": request.user["username"],
    })


@session_required
def vue_dashboard(request: FakeRequest) -> FakeResponse:
    """
    GET /dashboard/ — Page protégée.
    """
    return FakeResponse(200, {"message": "Bienvenue sur le tableau de bord !"})


# ---------------------------------------------------------------------------
# 7. Suite de tests
# ---------------------------------------------------------------------------

class TestSessionAuth(TestCase):
    """Tests du système d'authentification par session."""

    def setUp(self):
        """Nettoyer le store de sessions entre chaque test."""
        SESSION_STORE.clear()

    # --- Tests du store de sessions ---

    def test_creer_session_retourne_un_uuid(self):
        session_id = creer_session(1, "alice")
        self.assertIsInstance(session_id, str)
        self.assertEqual(len(session_id), 36)  # format UUID

    def test_recuperer_session_valide(self):
        session_id = creer_session(1, "alice")
        session = recuperer_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session["user_id"], 1)
        self.assertEqual(session["username"], "alice")

    def test_recuperer_session_inexistante(self):
        session = recuperer_session("session-qui-nexiste-pas")
        self.assertIsNone(session)

    def test_recuperer_session_expiree(self):
        session_id = creer_session(1, "alice")
        # Simuler l'expiration en modifiant le store
        SESSION_STORE[session_id]["expires_at"] = time.time() - 1
        session = recuperer_session(session_id)
        self.assertIsNone(session)
        # La session doit être nettoyée du store
        self.assertNotIn(session_id, SESSION_STORE)

    def test_detruire_session(self):
        session_id = creer_session(1, "alice")
        detruire_session(session_id)
        self.assertIsNone(recuperer_session(session_id))

    # --- Tests des credentials ---

    def test_credentials_valides_alice(self):
        user = verifier_credentials("alice", "motdepasse123")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "alice")

    def test_credentials_invalides_mauvais_mot_de_passe(self):
        user = verifier_credentials("alice", "mauvais_mdp")
        self.assertIsNone(user)

    def test_credentials_invalides_utilisateur_inconnu(self):
        user = verifier_credentials("inconnu", "mdp")
        self.assertIsNone(user)

    # --- Tests du middleware ---

    def test_middleware_attache_session_a_la_requete(self):
        session_id = creer_session(1, "alice")
        request = FakeRequest(cookies={SESSION_COOKIE_NAME: session_id})
        middleware = SessionMiddleware()
        middleware.process_request(request)

        self.assertIsNotNone(request.session_data)
        self.assertTrue(request.user["is_authenticated"])
        self.assertEqual(request.user["username"], "alice")

    def test_middleware_sans_cookie(self):
        request = FakeRequest()  # pas de cookies
        middleware = SessionMiddleware()
        middleware.process_request(request)

        self.assertIsNone(request.session_data)
        self.assertFalse(request.user["is_authenticated"])

    def test_middleware_cookie_invalide(self):
        request = FakeRequest(cookies={SESSION_COOKIE_NAME: "faux-session-id"})
        middleware = SessionMiddleware()
        middleware.process_request(request)

        self.assertIsNone(request.session_data)
        self.assertFalse(request.user["is_authenticated"])

    # --- Tests de la vue login ---

    def test_login_succes(self):
        request = FakeRequest(
            method="POST",
            body={"username": "alice", "password": "motdepasse123"},
        )
        response = vue_login(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(SESSION_COOKIE_NAME, response.cookies)
        # Vérifier que la session a bien été créée
        session_id = response.cookies[SESSION_COOKIE_NAME]["value"]
        session = recuperer_session(session_id)
        self.assertIsNotNone(session)
        self.assertEqual(session["username"], "alice")

    def test_login_credentials_invalides(self):
        request = FakeRequest(
            method="POST",
            body={"username": "alice", "password": "mauvais"},
        )
        response = vue_login(request)
        self.assertEqual(response.status_code, 401)

    def test_login_champs_manquants(self):
        request = FakeRequest(
            method="POST",
            body={"username": "alice"},  # pas de password
        )
        response = vue_login(request)
        self.assertEqual(response.status_code, 400)

    def test_login_methode_get_refusee(self):
        request = FakeRequest(method="GET")
        response = vue_login(request)
        self.assertEqual(response.status_code, 405)

    def test_cookie_httponly(self):
        """Le cookie doit être HttpOnly (inaccessible au JS)."""
        request = FakeRequest(
            method="POST",
            body={"username": "alice", "password": "motdepasse123"},
        )
        response = vue_login(request)
        cookie = response.cookies.get(SESSION_COOKIE_NAME, {})
        self.assertTrue(cookie.get("httponly", False))

    # --- Tests de la vue logout ---

    def test_logout_detruit_la_session(self):
        # D'abord créer une session
        session_id = creer_session(1, "alice")
        self.assertIsNotNone(recuperer_session(session_id))

        request = FakeRequest(
            method="POST",
            cookies={SESSION_COOKIE_NAME: session_id},
        )
        response = vue_logout(request)
        self.assertEqual(response.status_code, 200)
        # La session doit être détruite
        self.assertIsNone(recuperer_session(session_id))

    def test_logout_methode_get_refusee(self):
        request = FakeRequest(method="GET")
        response = vue_logout(request)
        self.assertEqual(response.status_code, 405)

    # --- Tests du décorateur @session_required ---

    def test_vue_protegee_sans_session_redirige(self):
        request = FakeRequest(method="GET")
        response = vue_profil(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.data.get("redirect"), "/login/")

    def test_vue_protegee_avec_session_valide(self):
        session_id = creer_session(1, "alice")
        request = FakeRequest(
            method="GET",
            cookies={SESSION_COOKIE_NAME: session_id},
        )
        # Simuler ce que ferait le middleware Django
        middleware = SessionMiddleware()
        middleware.process_request(request)

        response = vue_profil(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "alice")

    def test_vue_dashboard_protegee(self):
        session_id = creer_session(2, "bob")
        request = FakeRequest(
            method="GET",
            cookies={SESSION_COOKIE_NAME: session_id},
        )
        middleware = SessionMiddleware()
        middleware.process_request(request)

        response = vue_dashboard(request)
        self.assertEqual(response.status_code, 200)

    # --- Test du flux complet login → accès protégé → logout ---

    def test_flux_complet(self):
        """Scénario : login → accès protégé → logout → accès refusé."""
        middleware = SessionMiddleware()

        # 1. Login
        login_request = FakeRequest(
            method="POST",
            body={"username": "alice", "password": "motdepasse123"},
        )
        login_response = vue_login(login_request)
        self.assertEqual(login_response.status_code, 200)
        session_id = login_response.cookies[SESSION_COOKIE_NAME]["value"]

        # 2. Accéder à une page protégée avec la session
        profil_request = FakeRequest(
            method="GET",
            cookies={SESSION_COOKIE_NAME: session_id},
        )
        middleware.process_request(profil_request)
        profil_response = vue_profil(profil_request)
        self.assertEqual(profil_response.status_code, 200)
        self.assertEqual(profil_response.data["username"], "alice")

        # 3. Logout
        logout_request = FakeRequest(
            method="POST",
            cookies={SESSION_COOKIE_NAME: session_id},
        )
        logout_response = vue_logout(logout_request)
        self.assertEqual(logout_response.status_code, 200)

        # 4. Tenter d'accéder avec l'ancienne session → refusé
        stale_request = FakeRequest(
            method="GET",
            cookies={SESSION_COOKIE_NAME: session_id},
        )
        middleware.process_request(stale_request)
        stale_response = vue_profil(stale_request)
        self.assertEqual(stale_response.status_code, 302)


# ---------------------------------------------------------------------------
# 8. Note sur l'intégration Django réelle
# ---------------------------------------------------------------------------

INTEGRATION_DJANGO = """
Dans un projet Django réel, voici comment ces composants s'articulent :

settings.py :
    INSTALLED_APPS = [..., 'django.contrib.sessions', ...]
    MIDDLEWARE = [
        'django.contrib.sessions.middleware.SessionMiddleware',
        ...
    ]
    SESSION_COOKIE_AGE = 3600        # TTL en secondes
    SESSION_COOKIE_HTTPONLY = True   # Pas d'accès JS
    SESSION_COOKIE_SECURE = True     # HTTPS uniquement en prod
    SESSION_COOKIE_SAMESITE = 'Lax'  # Protection CSRF

views.py :
    from django.contrib.auth import authenticate, login, logout

    def login_view(request):
        user = authenticate(request, username=..., password=...)
        if user:
            login(request, user)  # crée la session automatiquement
            return redirect('dashboard')
        return render(request, 'login.html', {'error': 'Credentials invalides'})

    def logout_view(request):
        logout(request)  # détruit la session
        return redirect('login')

    @login_required  # équivalent à notre @session_required
    def dashboard(request):
        return render(request, 'dashboard.html')

    # request.session est un dict-like object :
    request.session['panier'] = [1, 2, 3]
    panier = request.session.get('panier', [])
    del request.session['panier']
"""


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import unittest

    print("=" * 60)
    print("Day 39 — Tests : Session Auth from Scratch")
    print("=" * 60)
    print()

    # Afficher la note d'intégration Django
    print("Note d'intégration Django réelle :")
    print(INTEGRATION_DJANGO)
    print()

    # Lancer les tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSessionAuth)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\nTous les tests passent. Le système de session fonctionne correctement.")
    else:
        print(f"\n{len(result.failures)} échec(s), {len(result.errors)} erreur(s).")
