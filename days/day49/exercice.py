"""
Exercice Jour 49 — RBAC : Rôles et permissions

Lance : python3 exercice.py
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                        "rest_framework", "__main__"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        ROOT_URLCONF="__main__",
        SECRET_KEY="rbac-test-key",
    )
    django.setup()

from django.contrib.auth.models import User, Group, Permission
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.test import APIRequestFactory


# ─── Modèles ─────────────────────────────────────────────────────────────────

class Niveau:
    INVITE = 0
    UTILISATEUR = 1
    MODERATEUR = 2
    REDACTEUR = 3
    ADMIN = 4
    NOMS = {0: "Invité", 1: "Utilisateur", 2: "Modérateur", 3: "Rédacteur", 4: "Admin"}


class Profil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profil")
    niveau = models.IntegerField(default=Niveau.UTILISATEUR)

    def peut(self, niveau_requis: int) -> bool:
        """Retourne True si ce profil a au moins le niveau requis."""
        # TODO
        pass

    def __str__(self):
        return f"{self.user.username} ({Niveau.NOMS.get(self.niveau, '?')})"

    class Meta: app_label = "__main__"


class Article(models.Model):
    titre = models.CharField(max_length=200)
    auteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name="articles")
    statut = models.CharField(max_length=20, default="brouillon")

    class Meta:
        app_label = "__main__"
        permissions = [
            ("publish_article", "Peut publier des articles"),
            ("moderate_article", "Peut modérer les commentaires"),
        ]

    def __str__(self):
        return self.titre


# ─── EXERCICE 1 : Permissions Django custom ──────────────────────────────────

def creer_groupes():
    """
    Crée les groupes Redacteurs et Moderateurs avec leurs permissions.

    TODO :
    - Groupe "Redacteurs" : peut add_article, change_article, view_article, publish_article
    - Groupe "Moderateurs" : peut view_article, moderate_article
    """
    # TODO : Group.objects.get_or_create + group.permissions.add(...)
    pass


# ─── EXERCICE 2 : Permissions DRF ────────────────────────────────────────────

class RequiertNiveau(BasePermission):
    """
    Permission qui vérifie que l'utilisateur a au moins `niveau_minimum`.
    Nécessite que l'utilisateur ait un Profil.
    """

    def __init__(self, niveau_minimum: int):
        self.niveau_minimum = niveau_minimum

    def has_permission(self, request, view):
        """
        TODO :
        1. Vérifier que l'utilisateur est authentifié
        2. Accéder à request.user.profil
        3. Appeler .peut(self.niveau_minimum)
        """
        # TODO
        pass


class EstAuteurOuAdmin(BasePermission):
    """
    - Lecture : tout le monde
    - Écriture : l'auteur de l'article OU un admin (is_staff)
    """

    def has_object_permission(self, request, view, obj):
        # TODO
        pass


class EstDanGroupe(BasePermission):
    """Vérifie que l'utilisateur est dans le groupe spécifié."""

    def __init__(self, nom_groupe: str):
        self.nom_groupe = nom_groupe

    def has_permission(self, request, view):
        # TODO : request.user.groups.filter(name=self.nom_groupe).exists()
        pass


# ─── EXERCICE 3 : Vues protégées ─────────────────────────────────────────────

urlpatterns = []

class ArticlePublierView(APIView):
    """Publier un article — seulement les Rédacteurs ou Admins."""
    # TODO : authentication_classes, permission_classes

    def post(self, request, pk):
        try:
            article = Article.objects.get(pk=pk)
        except Article.DoesNotExist:
            return Response({"error": "Non trouvé"}, status=404)

        # Vérification objet : l'auteur ou un admin peut publier
        if not EstAuteurOuAdmin().has_object_permission(request, None, article):
            return Response({"error": "Interdit"}, status=403)

        article.statut = "publie"
        article.save()
        return Response({"message": "Article publié", "statut": article.statut})


class ArticleModerationView(APIView):
    """Modération — seulement les Modérateurs ou Admins."""
    # TODO

    def delete(self, request, pk):
        """Supprimer un article (modération)."""
        try:
            article = Article.objects.get(pk=pk)
        except Article.DoesNotExist:
            return Response({"error": "Non trouvé"}, status=404)
        article.delete()
        return Response({"message": "Supprimé"})


class AdminView(APIView):
    """Stats admin — niveau ADMIN seulement."""
    # TODO permission_classes = [IsAuthenticated, RequiertNiveau(Niveau.ADMIN)]

    def get(self, request):
        return Response({
            "total_users": User.objects.count(),
            "total_articles": Article.objects.count(),
        })


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    from django.db import connection
    with connection.schema_editor() as se:
        for m in [User, Group, Profil, Article]:
            try: se.create_model(m)
            except: pass

    # Créer les utilisateurs
    alice = User.objects.create_user("alice", password="p")
    bob = User.objects.create_user("bob", password="p")
    admin = User.objects.create_user("admin", password="p", is_staff=True)

    # Créer les profils
    Profil.objects.create(user=alice, niveau=Niveau.REDACTEUR)
    Profil.objects.create(user=bob, niveau=Niveau.UTILISATEUR)
    Profil.objects.create(user=admin, niveau=Niveau.ADMIN)

    erreurs = 0
    def ok(n): print(f"  OK    {n}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    print("=== Niveaux d'accès ===")
    try:
        assert alice.profil.peut(Niveau.REDACTEUR) == True
        assert alice.profil.peut(Niveau.ADMIN) == False
        assert admin.profil.peut(Niveau.ADMIN) == True
        ok("Hiérarchie de niveaux")
    except Exception as e: echec("niveaux", e)

    print("\n=== Permissions Django ===")
    try:
        creer_groupes()
        g = Group.objects.filter(name="Redacteurs").first()
        if g:
            alice.groups.add(g)
            # Recharger depuis DB
            alice.refresh_from_db()
            # Note: permissions en cache — utiliser has_perm sur user rechargé
            ok("Groupes créés et assignés")
        else:
            echec("groupes", "Groupe Redacteurs non créé")
    except Exception as e: echec("groupes", e)

    print("\n=== Permissions objet ===")
    try:
        article_alice = Article.objects.create(titre="Article d'Alice", auteur=alice)
        perm = EstAuteurOuAdmin()

        class FakeRequest:
            def __init__(self, user, method="GET"):
                self.user = user
                self.method = method

        # Alice peut modifier son propre article
        assert perm.has_object_permission(FakeRequest(alice, "PUT"), None, article_alice) == True
        ok("Auteur peut modifier son article")

        # Bob ne peut pas modifier l'article d'Alice
        assert perm.has_object_permission(FakeRequest(bob, "PUT"), None, article_alice) == False
        ok("Autre user ne peut pas modifier")

        # Admin peut tout modifier
        assert perm.has_object_permission(FakeRequest(admin, "PUT"), None, article_alice) == True
        ok("Admin peut modifier n'importe quoi")

        # Lecture publique
        assert perm.has_object_permission(FakeRequest(bob, "GET"), None, article_alice) == True
        ok("Lecture publique autorisée")
    except Exception as e: echec("permissions objet", e)

    print("\n=== RequiertNiveau ===")
    try:
        perm_admin = RequiertNiveau(Niveau.ADMIN)
        perm_redacteur = RequiertNiveau(Niveau.REDACTEUR)

        class FakeRequest2:
            def __init__(self, u):
                self.user = u
                self.auth = None

        assert perm_admin.has_permission(FakeRequest2(admin), None) == True
        ok("Admin accède au niveau ADMIN")

        assert perm_admin.has_permission(FakeRequest2(alice), None) == False
        ok("Rédacteur refusé au niveau ADMIN")

        assert perm_redacteur.has_permission(FakeRequest2(alice), None) == True
        ok("Rédacteur accède au niveau REDACTEUR")

        assert perm_redacteur.has_permission(FakeRequest2(bob), None) == False
        ok("Utilisateur basique refusé au niveau REDACTEUR")
    except Exception as e: echec("RequiertNiveau", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
