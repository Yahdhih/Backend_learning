"""
Exercice Jour 66 — Projet Capstone : API Blog sécurisée

C'est le dernier exercice du cursus. Il met en pratique tout ce que tu as appris.
Lance : python3 exercice.py

Ce fichier contient le squelette complet. Implémente chaque TODO.
Une fois tous les tests verts, tu as terminé le cursus !
"""

import django, uuid, hmac as hmac_mod, hashlib, base64, json, time
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                        "rest_framework", "__main__"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        ROOT_URLCONF="__main__",
        SECRET_KEY="capstone-secret-key-use-env-in-prod",
        USE_TZ=True, TIME_ZONE="UTC",
        PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    )
    django.setup()

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.core.cache import cache
import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory


# ═══════════════════════════════════════════════════════════════════
# MODULE 1 : MODÈLES
# ═══════════════════════════════════════════════════════════════════

class Niveau:
    INVITE = 0
    UTILISATEUR = 1
    MODERATEUR = 2
    REDACTEUR = 3
    ADMIN = 4

class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profil")
    niveau = models.IntegerField(default=Niveau.UTILISATEUR)
    class Meta: app_label = "__main__"

class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name="articles")
    statut = models.CharField(max_length=20, default="brouillon")  # brouillon, publie
    vues = models.IntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    class Meta: app_label = "__main__"

class Commentaire(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="commentaires")
    auteur = models.ForeignKey(User, on_delete=models.CASCADE)
    contenu = models.TextField()
    approuve = models.BooleanField(default=False)
    class Meta: app_label = "__main__"

class RefreshToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.TextField(unique=True)
    expire_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    famille = models.UUIDField(default=uuid.uuid4)
    class Meta: app_label = "__main__"

    def is_valide(self):
        return not self.revoked and self.expire_at > timezone.now()


# ═══════════════════════════════════════════════════════════════════
# MODULE 2 : JWT
# ═══════════════════════════════════════════════════════════════════

SECRET = settings.SECRET_KEY.encode()

def _b64e(data): return base64.urlsafe_b64encode(data).rstrip(b"=").decode()
def _b64d(s): return base64.urlsafe_b64decode(s + "=" * (4 - len(s) % 4))

def creer_jwt(payload, expire_dans=900):
    p = {**payload, "iat": int(time.time()), "exp": int(time.time()) + expire_dans}
    h = _b64e(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    b = _b64e(json.dumps(p).encode())
    s = _b64e(hmac_mod.new(SECRET, f"{h}.{b}".encode(), hashlib.sha256).digest())
    return f"{h}.{b}.{s}"

def verifier_jwt(token):
    h, b, s = token.split(".")
    attendu = _b64e(hmac_mod.new(SECRET, f"{h}.{b}".encode(), hashlib.sha256).digest())
    if not hmac_mod.compare_digest(s, attendu): raise ValueError("Signature invalide")
    p = json.loads(_b64d(b))
    if p["exp"] < time.time(): raise ValueError("Expiré")
    return p


# ═══════════════════════════════════════════════════════════════════
# MODULE 3 : AUTHENTIFICATION
# ═══════════════════════════════════════════════════════════════════

def emettre_tokens(user):
    """
    TODO : creer_jwt access (15min) + refresh (7j), sauvegarder RefreshToken
    Retourner {"access_token": ..., "refresh_token": ...}
    """
    pass

def renouveler(refresh_str):
    """
    TODO : Token rotation avec détection de vol (Token Family)
    Retourner {"access_token": ..., "refresh_token": ...} ou ValueError
    """
    pass

class JWTAuth(BaseAuthentication):
    """TODO : lire Authorization: Bearer <token>, verifier_jwt, retourner (user, token)"""
    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "): return None
        try:
            payload = verifier_jwt(header[7:])
            user = User.objects.get(pk=payload["user_id"])
            return (user, header[7:])
        except Exception as e:
            raise AuthenticationFailed(str(e))


# ═══════════════════════════════════════════════════════════════════
# MODULE 4 : PERMISSIONS
# ═══════════════════════════════════════════════════════════════════

class RequiertNiveau(BasePermission):
    """TODO : vérifier request.user.profil.niveau >= niveau_minimum"""
    def __init__(self, niveau_minimum):
        self.niveau_minimum = niveau_minimum
    def has_permission(self, request, view):
        if not request.user.is_authenticated: return False
        try: return request.user.profil.niveau >= self.niveau_minimum
        except: return False

class EstAuteurOuModerateurOuAdmin(BasePermission):
    """TODO : lecture publique, modification seulement pour auteur/modérateur/admin"""
    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"): return True
        if request.user.is_staff: return True
        try:
            if request.user.profil.niveau >= Niveau.MODERATEUR: return True
        except: pass
        return getattr(obj, "auteur", None) == request.user


# ═══════════════════════════════════════════════════════════════════
# MODULE 5 : SERIALIZERS
# ═══════════════════════════════════════════════════════════════════

class ArticleSerializer(serializers.ModelSerializer):
    auteur_username = serializers.CharField(source="auteur.username", read_only=True)
    nb_commentaires = serializers.SerializerMethodField()

    def get_nb_commentaires(self, obj):
        return obj.commentaires.filter(approuve=True).count()

    class Meta:
        model = Article
        fields = ["id", "titre", "contenu", "statut", "vues", "auteur_username",
                  "nb_commentaires", "date_creation"]
        read_only_fields = ["statut", "vues", "auteur_username", "date_creation"]


class CommentaireSerializer(serializers.ModelSerializer):
    auteur_username = serializers.CharField(source="auteur.username", read_only=True)
    class Meta:
        model = Commentaire
        fields = ["id", "contenu", "auteur_username", "approuve"]
        read_only_fields = ["auteur_username", "approuve"]


# ═══════════════════════════════════════════════════════════════════
# MODULE 6 : VUES
# ═══════════════════════════════════════════════════════════════════

urlpatterns = []

class LoginView(APIView):
    """TODO : authentifier + emettre_tokens ou 401"""
    permission_classes = []
    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        try:
            user = User.objects.get(username=username)
            if not user.check_password(password): raise Exception()
        except:
            return Response({"error": "Identifiants incorrects"}, status=401)
        tokens = emettre_tokens(user)
        if tokens is None:
            return Response({"error": "Auth non implémentée"}, status=500)
        return Response(tokens)

class RefreshView(APIView):
    """TODO : renouveler ou 401"""
    permission_classes = []
    def post(self, request):
        try:
            tokens = renouveler(request.data.get("refresh_token", ""))
            return Response(tokens)
        except ValueError as e:
            return Response({"error": str(e)}, status=401)

class ArticleListView(APIView):
    authentication_classes = [JWTAuth]
    permission_classes = []

    def get(self, request):
        """
        TODO : liste des articles publiés
        - Si authentifié et Rédacteur+ : voir aussi les brouillons de l'auteur
        - Cache Redis 60 secondes sur la clé "articles_publies"
        - Utiliser select_related("auteur") pour éviter N+1
        """
        cache_key = "articles_publies"
        cached = cache.get(cache_key)
        if cached:
            return Response({"data": cached, "from_cache": True})

        articles = Article.objects.filter(statut="publie").select_related("auteur").order_by("-date_creation")
        data = ArticleSerializer(articles, many=True).data
        cache.set(cache_key, list(data), 60)
        return Response({"data": data, "from_cache": False})

    def post(self, request):
        """
        TODO : créer un article (authentifié seulement)
        - Assigner l'auteur = request.user
        - Invalider le cache "articles_publies" si statut = publie
        """
        if not request.user.is_authenticated:
            return Response({"error": "Non authentifié"}, status=401)
        serializer = ArticleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        article = serializer.save(auteur=request.user)
        if article.statut == "publie":
            cache.delete("articles_publies")
        return Response(ArticleSerializer(article).data, status=201)

class ArticleDetailView(APIView):
    authentication_classes = [JWTAuth]
    permission_classes = []

    def get_object(self, pk):
        try:
            return Article.objects.select_related("auteur").get(pk=pk)
        except Article.DoesNotExist:
            return None

    def get(self, request, pk):
        article = self.get_object(pk)
        if not article: return Response({"error": "Non trouvé"}, status=404)
        if article.statut != "publie" and article.auteur != request.user and not request.user.is_staff:
            return Response({"error": "Non trouvé"}, status=404)
        return Response(ArticleSerializer(article).data)

    def patch(self, request, pk):
        """TODO : modifier l'article (auteur ou modérateur+)"""
        article = self.get_object(pk)
        if not article: return Response({"error": "Non trouvé"}, status=404)
        perm = EstAuteurOuModerateurOuAdmin()
        if not perm.has_object_permission(request, self, article):
            return Response({"error": "Interdit"}, status=403)
        serializer = ArticleSerializer(article, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        article = serializer.save()
        cache.delete("articles_publies")
        return Response(ArticleSerializer(article).data)

    def delete(self, request, pk):
        """TODO : supprimer (auteur ou modérateur+)"""
        article = self.get_object(pk)
        if not article: return Response({"error": "Non trouvé"}, status=404)
        perm = EstAuteurOuModerateurOuAdmin()
        if not perm.has_object_permission(request, self, article):
            return Response({"error": "Interdit"}, status=403)
        article.delete()
        cache.delete("articles_publies")
        return Response(status=204)


# ═══════════════════════════════════════════════════════════════════
# MODULE 7 : TESTS FINAUX
# ═══════════════════════════════════════════════════════════════════

def tester():
    from django.db import connection
    with connection.schema_editor() as se:
        for m in [User, Profil, Article, Commentaire, RefreshToken]:
            try: se.create_model(m)
            except: pass

    # Setup
    alice = User.objects.create_user("alice66", password="p123")
    bob = User.objects.create_user("bob66", password="p456")
    mod = User.objects.create_user("mod66", password="p789")

    Profil.objects.create(user=alice, niveau=Niveau.REDACTEUR)
    Profil.objects.create(user=bob, niveau=Niveau.UTILISATEUR)
    Profil.objects.create(user=mod, niveau=Niveau.MODERATEUR)

    factory = APIRequestFactory()
    erreurs = 0

    def ok(n): print(f"  OK    {n}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    print("══════════════════════════════════")
    print("  PROJET CAPSTONE — TESTS FINAUX")
    print("══════════════════════════════════\n")

    # ── Auth ──
    print("--- Auth ---")
    req = factory.post("/login/", {"username": "alice66", "password": "p123"}, format="json")
    resp = LoginView.as_view()(req)
    try:
        assert resp.status_code == 200 and "access_token" in resp.data
        tokens_alice = resp.data
        ok("Login Alice → 200 + tokens")
    except: echec("login alice", f"status={resp.status_code}"); tokens_alice = None

    try:
        req = factory.post("/login/", {"username": "alice66", "password": "mauvais"}, format="json")
        resp = LoginView.as_view()(req)
        assert resp.status_code == 401
        ok("Login mauvais mdp → 401")
    except Exception as e: echec("login mauvais mdp", e)

    # ── Articles ──
    print("\n--- Articles ---")
    if tokens_alice:
        # Créer un article
        req = factory.post("/articles/", {"titre": "Test", "contenu": "Contenu test"},
                           format="json",
                           HTTP_AUTHORIZATION=f"Bearer {tokens_alice['access_token']}")
        resp = ArticleListView.as_view()(req)
        try:
            assert resp.status_code == 201
            article_id = resp.data["id"]
            ok("POST /articles/ → 201")
        except: echec("créer article", f"status={resp.status_code}"); article_id = None

        # Lister les articles publics (vide car le seul est brouillon)
        req = factory.get("/articles/")
        resp = ArticleListView.as_view()(req)
        try:
            assert resp.status_code == 200
            ok("GET /articles/ → 200")
        except Exception as e: echec("lister articles", e)

        if article_id:
            # Modifier l'article (Alice = auteur)
            req = factory.patch(f"/articles/{article_id}/", {"statut": "publie"},
                                format="json",
                                HTTP_AUTHORIZATION=f"Bearer {tokens_alice['access_token']}")
            resp = ArticleDetailView.as_view()(req, pk=article_id)
            try:
                assert resp.status_code == 200
                ok("PATCH article par auteur → 200")
            except Exception as e: echec("modifier article auteur", e)

            # Bob essaie de modifier l'article d'Alice
            req = factory.post("/login/", {"username": "bob66", "password": "p456"}, format="json")
            tokens_bob = LoginView.as_view()(req).data if hasattr(LoginView.as_view()(req), 'data') else {}

            try:
                req_login_bob = factory.post("/login/", {"username": "bob66", "password": "p456"}, format="json")
                resp_bob = LoginView.as_view()(req_login_bob)
                if resp_bob.status_code == 200:
                    req_patch = factory.patch(f"/articles/{article_id}/", {"titre": "Hack"},
                                              format="json",
                                              HTTP_AUTHORIZATION=f"Bearer {resp_bob.data['access_token']}")
                    resp_patch = ArticleDetailView.as_view()(req_patch, pk=article_id)
                    assert resp_patch.status_code == 403
                    ok("PATCH article par Bob → 403")
            except Exception as e: echec("modifier article autre user", e)

    # ── Cache ──
    print("\n--- Cache ---")
    try:
        cache.clear()
        req = factory.get("/articles/")
        resp1 = ArticleListView.as_view()(req)
        req2 = factory.get("/articles/")
        resp2 = ArticleListView.as_view()(req2)
        assert resp2.data.get("from_cache") == True
        ok("Cache : deuxième requête depuis le cache")
    except Exception as e: echec("cache", e)

    # ── Token Rotation ──
    print("\n--- Token Rotation ---")
    if tokens_alice and tokens_alice.get("refresh_token"):
        try:
            req = factory.post("/refresh/",
                               {"refresh_token": tokens_alice["refresh_token"]},
                               format="json")
            resp = RefreshView.as_view()(req)
            assert resp.status_code == 200
            ok("Rotation token → 200 + nouveau access")

            # Réutiliser l'ancien refresh → doit échouer (vol détecté)
            req2 = factory.post("/refresh/",
                                {"refresh_token": tokens_alice["refresh_token"]},
                                format="json")
            resp2 = RefreshView.as_view()(req2)
            assert resp2.status_code == 401
            ok("Ancien refresh réutilisé → 401")
        except Exception as e: echec("token rotation", e)

    print()
    if erreurs == 0:
        print("══════════════════════════════════")
        print("  CURSUS TERMINÉ ! Tous les tests passent.")
        print("  66 jours de Python Backend maîtrisés.")
        print("══════════════════════════════════")
    else:
        print(f"{erreurs} test(s) échoué(s). Continue à implémenter les TODO.")
        print("Hint : commence par emettre_tokens() et renouveler().")


if __name__ == "__main__":
    tester()
