"""
Exercice Jour 31 — ViewSets et Routers DRF

Lance : python3 exercice.py
"""

import django, json
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
            "__main__",
        ],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        ROOT_URLCONF="__main__",
        REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": [], "DEFAULT_PERMISSION_CLASSES": []},
    )
    django.setup()

from django.db import models
from django.contrib.auth.models import User
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.test import APIClient, APITestCase


class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    statut = models.CharField(max_length=20, default="brouillon")
    vues = models.IntegerField(default=0)
    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="articles")
    date_creation = models.DateTimeField(auto_now_add=True)
    class Meta: app_label = "__main__"


# ─── EXERCICE 1 : Serializers ────────────────────────────────────────────────

class ArticleListSerializer(serializers.ModelSerializer):
    """Version compacte pour la liste."""
    # TODO : inclure id, titre, statut, vues, date_creation
    class Meta:
        model = Article
        fields = []  # TODO


class ArticleDetailSerializer(serializers.ModelSerializer):
    """Version complète pour le détail."""
    # TODO : tous les champs
    class Meta:
        model = Article
        fields = []  # TODO


# ─── EXERCICE 2 : ViewSet complet ────────────────────────────────────────────

class ArticleViewSet(viewsets.ModelViewSet):
    """
    ViewSet CRUD pour les articles.

    - get_queryset() : filtre par ?statut= si présent, toujours select_related("auteur")
    - get_serializer_class() : ArticleListSerializer pour "list", ArticleDetailSerializer sinon
    - perform_create() : associe request.user comme auteur si authentifié
    - Action "publier" (detail=True, POST) : passe statut à "publie", retourne {"statut": "publié"}
    - Action "populaires" (detail=False, GET) : retourne les 5 articles avec le plus de vues
    """

    # TODO : queryset de base
    # TODO : serializer_class par défaut

    def get_queryset(self):
        # TODO
        pass

    def get_serializer_class(self):
        # TODO
        pass

    def perform_create(self, serializer):
        # TODO
        pass

    @action(detail=True, methods=["post"])
    def publier(self, request, pk=None):
        # TODO
        pass

    @action(detail=False, methods=["get"])
    def populaires(self, request):
        # TODO
        pass


# ─── URLS via Router ─────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="article")
urlpatterns = router.urls


# ─── TESTS ───────────────────────────────────────────────────────────────────

def creer_tables():
    from django.db import connection
    with connection.schema_editor() as se:
        for m in [Article]:
            try: se.create_model(m)
            except: pass


def tester():
    creer_tables()
    client = APIClient()
    erreurs = 0

    def ok(n): print(f"  OK    {n}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    # Créer des articles de test
    for i in range(5):
        Article.objects.create(
            titre=f"Article {i}",
            contenu=f"Contenu {i}",
            statut="publie" if i < 3 else "brouillon",
            vues=i * 100,
        )

    # Test list
    try:
        resp = client.get("/articles/")
        assert resp.status_code == 200, f"Status: {resp.status_code}"
        data = resp.json()
        assert isinstance(data, (list, dict))
        ok("GET /articles/ (list)")
    except Exception as e: echec("list", e)

    # Test create
    try:
        resp = client.post("/articles/", {"titre": "Nouveau", "contenu": "..."}, format="json")
        assert resp.status_code == 201, f"Status: {resp.status_code}, body: {resp.content}"
        ok("POST /articles/ (create)")
    except Exception as e: echec("create", e)

    # Test retrieve
    try:
        pk = Article.objects.first().pk
        resp = client.get(f"/articles/{pk}/")
        assert resp.status_code == 200
        ok("GET /articles/{pk}/ (retrieve)")
    except Exception as e: echec("retrieve", e)

    # Test update
    try:
        pk = Article.objects.first().pk
        resp = client.patch(f"/articles/{pk}/", {"titre": "Modifié"}, format="json")
        assert resp.status_code == 200
        ok("PATCH /articles/{pk}/ (partial_update)")
    except Exception as e: echec("update", e)

    # Test delete
    try:
        article = Article.objects.create(titre="À supprimer", contenu="...")
        resp = client.delete(f"/articles/{article.pk}/")
        assert resp.status_code == 204
        ok("DELETE /articles/{pk}/ (destroy)")
    except Exception as e: echec("delete", e)

    # Test action publier
    try:
        pk = Article.objects.filter(statut="brouillon").first().pk
        resp = client.post(f"/articles/{pk}/publier/")
        assert resp.status_code == 200
        assert Article.objects.get(pk=pk).statut == "publie"
        ok("POST /articles/{pk}/publier/ (action)")
    except Exception as e: echec("action publier", e)

    # Test filtre ?statut=
    try:
        resp = client.get("/articles/?statut=publie")
        assert resp.status_code == 200
        ok("GET /articles/?statut=publie (filtre)")
    except Exception as e: echec("filtre statut", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
