"""
Exercice Jour 52 — Tests complets du système d'authentification

Lance : python3 exercice.py
"""

import django, hmac as hmac_module, hashlib, base64, json, time, uuid
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                        "rest_framework", "__main__"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        ROOT_URLCONF="__main__",
        SECRET_KEY="test-auth-secret",
        USE_TZ=True,
        TIME_ZONE="UTC",
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],  # rapide
    )
    django.setup()

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory, APIClient


# ─── Système JWT (copié du jour 48 — version fonctionnelle) ─────────────────

SECRET = settings.SECRET_KEY.encode()

def _b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_decode(s):
    return base64.urlsafe_b64decode(s + "=" * (4 - len(s) % 4))

def creer_jwt(payload, expire_dans=900):
    p = {**payload, "iat": int(time.time()), "exp": int(time.time()) + expire_dans}
    h = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    b = _b64url_encode(json.dumps(p).encode())
    s = _b64url_encode(hmac_module.new(SECRET, f"{h}.{b}".encode(), hashlib.sha256).digest())
    return f"{h}.{b}.{s}"

def verifier_jwt(token):
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Format invalide")
    h, b, s = parts
    s_attendu = _b64url_encode(hmac_module.new(SECRET, f"{h}.{b}".encode(), hashlib.sha256).digest())
    if not hmac_module.compare_digest(s, s_attendu):
        raise ValueError("Signature invalide")
    payload = json.loads(_b64url_decode(b))
    if payload["exp"] < time.time():
        raise ValueError("Expiré")
    return payload


# ─── Modèle RefreshToken ─────────────────────────────────────────────────────

class RefreshToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.TextField(unique=True)
    expire_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    famille = models.UUIDField(default=uuid.uuid4)
    class Meta: app_label = "__main__"

def emettre_tokens(user):
    access = creer_jwt({"user_id": user.pk, "username": user.username}, 900)
    refresh = creer_jwt({"user_id": user.pk}, 7*24*3600)
    f = uuid.uuid4()
    RefreshToken.objects.create(
        user=user, token=refresh,
        expire_at=timezone.now() + datetime.timedelta(days=7),
        famille=f,
    )
    return {"access_token": access, "refresh_token": refresh}

def renouveler_access(refresh_str):
    try:
        rt = RefreshToken.objects.get(token=refresh_str)
    except RefreshToken.DoesNotExist:
        raise ValueError("Inconnu")
    if rt.revoked:
        RefreshToken.objects.filter(famille=rt.famille).update(revoked=True)
        raise ValueError("Révoqué — vol détecté")
    if not rt.is_valide():
        raise ValueError("Expiré")
    rt.revoked = True; rt.save()
    payload = verifier_jwt(refresh_str)
    user = User.objects.get(pk=payload["user_id"])
    tokens = emettre_tokens(user)
    # Mettre à jour la famille
    RefreshToken.objects.filter(token=tokens["refresh_token"]).update(famille=rt.famille)
    return tokens

def is_valide(self):
    return not self.revoked and self.expire_at > timezone.now()
RefreshToken.is_valide = is_valide


# ─── Vues ────────────────────────────────────────────────────────────────────

class JWTAuth(BaseAuthentication):
    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        token = header[7:]
        try:
            payload = verifier_jwt(token)
        except ValueError as e:
            raise AuthenticationFailed(str(e))
        try:
            user = User.objects.get(pk=payload["user_id"])
        except User.DoesNotExist:
            raise AuthenticationFailed("Utilisateur introuvable")
        return (user, token)

urlpatterns = []

class LoginView(APIView):
    permission_classes = []
    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "Identifiants incorrects"}, status=401)
        if not user.check_password(password):
            return Response({"error": "Identifiants incorrects"}, status=401)
        return Response(emettre_tokens(user))

class RefreshView(APIView):
    permission_classes = []
    def post(self, request):
        refresh = request.data.get("refresh_token", "")
        try:
            tokens = renouveler_access(refresh)
            return Response(tokens)
        except ValueError as e:
            return Response({"error": str(e)}, status=401)

class MoiView(APIView):
    authentication_classes = [JWTAuth]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({"id": request.user.pk, "username": request.user.username})

class LogoutView(APIView):
    authentication_classes = [JWTAuth]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        refresh = request.data.get("refresh_token", "")
        RefreshToken.objects.filter(token=refresh).update(revoked=True)
        return Response({"message": "Déconnecté"})


# ─── EXERCICE : Écrire des tests complets ────────────────────────────────────

def tester():
    """
    Ces tests vérifient le système d'auth complet.
    Certains sont précrits (marqués OK), d'autres sont à compléter (TODO).
    """
    from django.db import connection
    with connection.schema_editor() as se:
        for m in [User, RefreshToken]:
            try: se.create_model(m)
            except: pass

    erreurs = 0
    def ok(n): print(f"  OK    {n}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    factory = APIRequestFactory()
    alice = User.objects.create_user("alice52", password="motdepasse123")
    bob = User.objects.create_user("bob52", password="motdepasse456")

    # ── Tests de login ───────────────────────────────────────────────────────
    print("=== Tests Login ===")

    req = factory.post("/auth/login/", {"username": "alice52", "password": "motdepasse123"},
                       format="json")
    resp = LoginView.as_view()(req)
    try:
        assert resp.status_code == 200
        assert "access_token" in resp.data
        assert "refresh_token" in resp.data
        ok("Login valide → 200 + tokens")
        access = resp.data["access_token"]
        refresh = resp.data["refresh_token"]
    except Exception as e: echec("login valide", e); access = refresh = None

    try:
        req = factory.post("/auth/login/", {"username": "alice52", "password": "mauvais"},
                           format="json")
        resp = LoginView.as_view()(req)
        assert resp.status_code == 401
        assert "access_token" not in resp.data
        ok("Login mauvais mdp → 401 sans token")
    except Exception as e: echec("login mauvais mdp", e)

    try:
        req = factory.post("/auth/login/", {"username": "inexistant", "password": "p"},
                           format="json")
        resp = LoginView.as_view()(req)
        assert resp.status_code == 401
        ok("Login user inconnu → 401")
    except Exception as e: echec("login user inconnu", e)

    # ── Tests de ressource protégée ──────────────────────────────────────────
    print("\n=== Tests Ressource Protégée ===")

    if access:
        try:
            req = factory.get("/auth/moi/", HTTP_AUTHORIZATION=f"Bearer {access}")
            resp = MoiView.as_view()(req)
            assert resp.status_code == 200
            assert resp.data["username"] == "alice52"
            ok("GET /moi/ avec token valide → 200")
        except Exception as e: echec("moi avec token", e)

    try:
        req = factory.get("/auth/moi/")
        resp = MoiView.as_view()(req)
        assert resp.status_code == 401
        ok("GET /moi/ sans token → 401")
    except Exception as e: echec("moi sans token", e)

    try:
        req = factory.get("/auth/moi/", HTTP_AUTHORIZATION="Bearer token.faux.signature")
        resp = MoiView.as_view()(req)
        assert resp.status_code == 401
        ok("GET /moi/ token invalide → 401")
    except Exception as e: echec("moi token invalide", e)

    # ── Tests token expiré ───────────────────────────────────────────────────
    print("\n=== Tests Token Expiré ===")
    try:
        token_expire = creer_jwt({"user_id": alice.pk}, expire_dans=-1)
        req = factory.get("/auth/moi/", HTTP_AUTHORIZATION=f"Bearer {token_expire}")
        resp = MoiView.as_view()(req)
        assert resp.status_code == 401
        ok("Token expiré → 401")
    except Exception as e: echec("token expiré", e)

    # ── Tests rotation ───────────────────────────────────────────────────────
    print("\n=== Tests Rotation ===")
    if refresh:
        try:
            req = factory.post("/auth/refresh/", {"refresh_token": refresh}, format="json")
            resp = RefreshView.as_view()(req)
            assert resp.status_code == 200
            assert "access_token" in resp.data
            ok("Refresh → nouvel access")
            nouveau_refresh = resp.data["refresh_token"]

            # L'ancien refresh doit être révoqué
            ancien = RefreshToken.objects.get(token=refresh)
            assert ancien.revoked
            ok("Ancien refresh révoqué après rotation")

            # Utiliser l'ancien refresh → doit échouer
            req2 = factory.post("/auth/refresh/", {"refresh_token": refresh}, format="json")
            resp2 = RefreshView.as_view()(req2)
            assert resp2.status_code == 401
            ok("Ancien refresh réutilisé → 401 (vol détecté)")
        except Exception as e: echec("rotation", e)

    # ── Tests logout ─────────────────────────────────────────────────────────
    print("\n=== Tests Logout ===")
    if access:
        try:
            tokens_bob = emettre_tokens(bob)
            req = factory.post("/auth/logout/",
                               {"refresh_token": tokens_bob["refresh_token"]},
                               format="json",
                               HTTP_AUTHORIZATION=f"Bearer {tokens_bob['access_token']}")
            resp = LogoutView.as_view()(req)
            assert resp.status_code == 200
            ok("Logout → 200")

            rt = RefreshToken.objects.get(token=tokens_bob["refresh_token"])
            assert rt.revoked
            ok("Refresh révoqué après logout")
        except Exception as e: echec("logout", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
