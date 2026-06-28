"""
Exercice Jour 48 — Système d'authentification JWT complet (projet)

Lance : python3 exercice.py
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", "rest_framework", "__main__"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        ROOT_URLCONF="__main__",
        SECRET_KEY="jwt-project-secret-key-256bits-minimum",
    )
    django.setup()

import hmac, hashlib, base64, json, time
from django.contrib.auth.models import User
from django.test import RequestFactory
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


# ─── EXERCICE 1 : Bibliothèque JWT maison ────────────────────────────────────

SECRET = settings.SECRET_KEY.encode()

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def creer_token(payload: dict, expire_dans: int = 3600) -> str:
    """
    Crée un JWT signé avec HMAC-SHA256.
    Ajoute automatiquement 'iat' (issued at) et 'exp' (expiration).

    TODO :
    1. Construire header = {"alg": "HS256", "typ": "JWT"}
    2. Ajouter iat et exp au payload
    3. Encoder header et payload en base64url
    4. Calculer signature HMAC-SHA256 sur "header.payload"
    5. Retourner "header.payload.signature"
    """
    # TODO
    pass


def verifier_token(token: str) -> dict:
    """
    Vérifie un JWT et retourne le payload si valide.
    Lève ValueError si invalide ou expiré.

    TODO :
    1. Découper le token en 3 parties
    2. Recalculer la signature attendue
    3. Comparer avec hmac.compare_digest (timing-safe)
    4. Vérifier l'expiration (payload["exp"] > time.time())
    5. Retourner le payload décodé
    """
    # TODO
    pass


def creer_paire_tokens(user_id: int, username: str) -> dict:
    """
    Crée access token (15min) + refresh token (7 jours).
    """
    # TODO
    pass


# ─── EXERCICE 2 : Stockage des refresh tokens ────────────────────────────────

REFRESH_TOKENS_VALIDES = set()  # en prod : Redis ou DB


def emettre_tokens(user: User) -> dict:
    """
    Émet une paire de tokens pour l'utilisateur.
    Stocke le refresh token pour pouvoir le révoquer.

    TODO : creer_paire_tokens + stocker le refresh dans REFRESH_TOKENS_VALIDES
    """
    # TODO
    pass


def renouveler_access_token(refresh_token: str) -> str:
    """
    Échange un refresh token contre un nouvel access token.
    Rotation : émet un nouveau refresh token et révoque l'ancien.

    TODO :
    1. Vérifier que le refresh est dans REFRESH_TOKENS_VALIDES
    2. Vérifier la signature JWT
    3. Retirer l'ancien refresh de REFRESH_TOKENS_VALIDES
    4. Émettre une nouvelle paire et retourner l'access token
    """
    # TODO
    pass


def revoquer_token(refresh_token: str):
    """Révoque un refresh token (logout)."""
    REFRESH_TOKENS_VALIDES.discard(refresh_token)


# ─── EXERCICE 3 : Classe d'authentification DRF ──────────────────────────────

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JWTAuthentication(BaseAuthentication):
    """
    Classe d'authentification DRF.
    Lit le header Authorization: Bearer <token>
    """

    def authenticate(self, request):
        """
        Retourne (user, token) si authentifié, None si pas de token,
        lève AuthenticationFailed si token invalide.

        TODO :
        1. Récupérer le header Authorization
        2. Vérifier que c'est "Bearer <token>"
        3. Appeler verifier_token()
        4. Trouver l'utilisateur par user_id dans le payload
        5. Retourner (user, token)
        """
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        # TODO
        pass


# ─── EXERCICE 4 : Vues d'authentification ────────────────────────────────────

urlpatterns = []

class LoginView(APIView):
    """POST /auth/login/ — retourne access + refresh tokens"""
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        # TODO : authentifier + appeler emettre_tokens
        pass


class LogoutView(APIView):
    """POST /auth/logout/ — révoque le refresh token"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh_token")
        # TODO : revoquer_token
        pass


class RefreshView(APIView):
    """POST /auth/refresh/ — échange refresh → nouvel access token"""
    permission_classes = []

    def post(self, request):
        refresh = request.data.get("refresh_token")
        # TODO : renouveler_access_token
        pass


class MoiView(APIView):
    """GET /auth/moi/ — infos de l'utilisateur connecté"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.pk,
            "username": request.user.username,
            "email": request.user.email,
        })


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    from django.db import connection
    with connection.schema_editor() as se:
        for m in [User]:
            try: se.create_model(m)
            except: pass

    # Créer un utilisateur test
    user = User.objects.create_user(username="alice", password="alice123", email="alice@test.com")

    erreurs = 0
    def ok(n, extra=""): print(f"  OK    {n}{' (' + extra + ')' if extra else ''}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    print("=== JWT Création & Vérification ===")
    try:
        token = creer_token({"user_id": 1, "username": "alice"}, expire_dans=3600)
        assert token is not None
        parties = token.split(".")
        assert len(parties) == 3, "JWT doit avoir 3 parties"
        ok("Création JWT", token[:30] + "...")
    except Exception as e: echec("création JWT", e)

    try:
        token = creer_token({"user_id": 1}, expire_dans=3600)
        payload = verifier_token(token)
        assert payload["user_id"] == 1
        ok("Vérification JWT valide")
    except Exception as e: echec("vérification JWT", e)

    try:
        token = creer_token({"user_id": 1}, expire_dans=-1)  # déjà expiré
        try:
            verifier_token(token)
            echec("token expiré", "Aurait dû lever ValueError")
        except ValueError:
            ok("Token expiré refusé")
    except Exception as e: echec("token expiré", e)

    try:
        token = creer_token({"user_id": 1}, expire_dans=3600)
        header, payload_b64, sig = token.split(".")
        token_falsifie = f"{header}.{payload_b64}.fakesignature"
        try:
            verifier_token(token_falsifie)
            echec("token falsifié", "Aurait dû lever ValueError")
        except ValueError:
            ok("Token falsifié refusé")
    except Exception as e: echec("token falsifié", e)

    print("\n=== Paire de tokens ===")
    try:
        tokens = emettre_tokens(user)
        if tokens:
            assert "access_token" in tokens
            assert "refresh_token" in tokens
            assert tokens["refresh_token"] in REFRESH_TOKENS_VALIDES
            ok("Émission access + refresh")

            # Renouvellement
            nouveau_access = renouveler_access_token(tokens["refresh_token"])
            if nouveau_access:
                payload = verifier_token(nouveau_access)
                assert payload["user_id"] == user.pk
                ok("Renouvellement access token")

            # Révocation
            tokens2 = emettre_tokens(user)
            if tokens2:
                revoquer_token(tokens2["refresh_token"])
                assert tokens2["refresh_token"] not in REFRESH_TOKENS_VALIDES
                ok("Révocation (logout)")
    except Exception as e: echec("paire tokens", e)

    print("\n=== Authentification DRF ===")
    try:
        factory = RequestFactory()
        tokens = emettre_tokens(user)
        if tokens:
            # Requête avec token valide
            req = factory.get("/moi/", HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")
            view = MoiView.as_view()
            resp = view(req)
            if resp.status_code == 200:
                ok("GET /moi/ avec token valide → 200")
            else:
                echec("GET /moi/", f"status {resp.status_code}")

            # Requête sans token
            req2 = factory.get("/moi/")
            resp2 = view(req2)
            if resp2.status_code == 401:
                ok("GET /moi/ sans token → 401")
            else:
                echec("GET /moi/ sans token", f"status {resp2.status_code}")
    except Exception as e: echec("auth DRF", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s). Continue à implémenter les TODO.")


if __name__ == "__main__":
    tester()
