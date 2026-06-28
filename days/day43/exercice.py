"""
Exercice Jour 43 — Django auth system + DRF

Lance : python3 exercice.py
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[
            "django.contrib.contenttypes", "django.contrib.auth",
            "rest_framework", "rest_framework.authtoken", "__main__",
        ],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        ROOT_URLCONF="__main__",
        REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
                        "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"]},
    )
    django.setup()

from django.contrib.auth.models import User
from django.db import models
from rest_framework import serializers, viewsets, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.test import APIClient
from django.urls import path


class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name="articles")
    statut = models.CharField(max_length=20, default="brouillon")
    class Meta: app_label = "__main__"


# ─── EXERCICE 1 : Permission custom ──────────────────────────────────────────

class IsAuthorOrReadOnly(BasePermission):
    """
    - GET, HEAD, OPTIONS : autorisé pour tous
    - POST : authentifié seulement
    - PUT, PATCH, DELETE : auteur de l'objet seulement
    """

    def has_permission(self, request, view):
        # TODO
        pass

    def has_object_permission(self, request, view, obj):
        # TODO : obj.auteur == request.user pour les méthodes non-safe
        pass


# ─── EXERCICE 2 : Vue de login ───────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    POST /auth/login/
    Body : {"username": "...", "password": "..."}
    Retourne : {"token": "...", "user_id": ..., "username": "..."}
    Ou 401 si identifiants invalides.
    """
    # TODO :
    # 1. Extraire username et password de request.data
    # 2. authenticate(username=..., password=...)
    # 3. Si valide : Token.objects.get_or_create(user=user) → retourner le token
    # 4. Si invalide : 401 + {"error": "Identifiants invalides"}
    pass


@api_view(["POST"])
def logout_view(request):
    """
    POST /auth/logout/
    Supprime le token de l'utilisateur connecté.
    Retourne 204.
    """
    # TODO : request.user.auth_token.delete()
    pass


# ─── EXERCICE 3 : ViewSet avec auth ──────────────────────────────────────────

class ArticleSerializer(serializers.ModelSerializer):
    auteur_username = serializers.ReadOnlyField(source="auteur.username")
    class Meta:
        model = Article
        fields = ["id", "titre", "contenu", "statut", "auteur_username"]


class ArticleViewSet(viewsets.ModelViewSet):
    """
    - list/retrieve : public (AllowAny)
    - create : authentifié
    - update/destroy : auteur seulement (IsAuthorOrReadOnly)
    - perform_create : associe request.user comme auteur
    - get_queryset : publiés + brouillons de l'utilisateur connecté
    """
    serializer_class = ArticleSerializer

    def get_permissions(self):
        # TODO
        pass

    def get_queryset(self):
        # TODO
        pass

    def perform_create(self, serializer):
        # TODO
        pass


# ─── URLS ────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="article")

urlpatterns = [
    path("auth/login/", login_view),
    path("auth/logout/", logout_view),
] + router.urls


# ─── TESTS ───────────────────────────────────────────────────────────────────

def setup():
    from django.db import connection
    from django.contrib.auth.models import Permission
    with connection.schema_editor() as se:
        for m in [Article]:
            try: se.create_model(m)
            except: pass
    # Créer les tables authtoken
    try:
        from django.core.management import call_command
        call_command("migrate", "--run-syncdb", verbosity=0)
    except: pass


def tester():
    setup()
    client = APIClient()
    erreurs = 0

    def ok(n): print(f"  OK    {n}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    # Créer des users
    alice = User.objects.create_user("alice", password="alice123")
    bob = User.objects.create_user("bob", password="bob123")

    # Test login
    try:
        resp = client.post("/auth/login/", {"username": "alice", "password": "alice123"}, format="json")
        assert resp.status_code == 200, f"Login échoué: {resp.status_code} {resp.content}"
        assert "token" in resp.json()
        alice_token = resp.json()["token"]
        ok("Login réussi")
    except Exception as e: echec("login", e); return

    # Test login invalide
    try:
        resp = client.post("/auth/login/", {"username": "alice", "password": "mauvais"}, format="json")
        assert resp.status_code == 401
        ok("Login invalide → 401")
    except Exception as e: echec("login invalide", e)

    # Test liste articles sans auth (public)
    try:
        resp = client.get("/articles/")
        assert resp.status_code == 200
        ok("GET articles sans auth (public)")
    except Exception as e: echec("liste sans auth", e)

    # Test créer article avec auth
    try:
        client.credentials(HTTP_AUTHORIZATION=f"Token {alice_token}")
        resp = client.post("/articles/", {"titre": "Article d'Alice", "contenu": "..."}, format="json")
        assert resp.status_code == 201, f"Create échoué: {resp.content}"
        article_id = resp.json()["id"]
        ok("Créer article (authentifié)")
    except Exception as e: echec("create auth", e)

    # Test créer article sans auth → 401
    try:
        client.credentials()  # clear
        resp = client.post("/articles/", {"titre": "Test"}, format="json")
        assert resp.status_code == 401, f"Attendu 401, obtenu {resp.status_code}"
        ok("Create sans auth → 401")
    except Exception as e: echec("create sans auth", e)

    # Test modifier l'article de quelqu'un d'autre → 403
    try:
        bob_token = Token.objects.get_or_create(user=bob)[0].key
        client.credentials(HTTP_AUTHORIZATION=f"Token {bob_token}")
        resp = client.patch(f"/articles/{article_id}/", {"titre": "Modifié par Bob"}, format="json")
        assert resp.status_code == 403, f"Attendu 403, obtenu {resp.status_code}"
        ok("Modifier article d'autrui → 403")
    except Exception as e: echec("permission objet", e)

    # Test logout
    try:
        client.credentials(HTTP_AUTHORIZATION=f"Token {alice_token}")
        resp = client.post("/auth/logout/")
        assert resp.status_code == 204
        # Vérifier que le token ne fonctionne plus
        resp2 = client.post("/articles/", {"titre": "Après logout"}, format="json")
        assert resp2.status_code == 401
        ok("Logout + token invalidé")
    except Exception as e: echec("logout", e)

    print()
    if erreurs == 0: print("Tous les tests passent ! Module Auth terminé.")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
