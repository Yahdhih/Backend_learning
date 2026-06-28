"""
Exercice Jour 32 — Pagination et Filtering DRF

Lance : python3 exercice.py
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=[
            "django.contrib.contenttypes", "django.contrib.auth",
            "rest_framework", "__main__",
        ],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        ROOT_URLCONF="__main__",
        REST_FRAMEWORK={"DEFAULT_AUTHENTICATION_CLASSES": [], "DEFAULT_PERMISSION_CLASSES": []},
    )
    django.setup()

from django.db import models
from django.contrib.auth.models import User
from rest_framework import serializers, viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.routers import DefaultRouter
from rest_framework.test import APIClient


class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField(default="")
    statut = models.CharField(max_length=20, default="publie")
    vues = models.IntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    class Meta: app_label = "__main__"; ordering = ["-date_creation"]


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ["id", "titre", "statut", "vues", "date_creation"]


# ─── EXERCICE 1 : Pagination ─────────────────────────────────────────────────

class ArticlePagination(PageNumberPagination):
    """
    Configure la pagination :
    - 5 articles par page par défaut
    - Le client peut changer avec ?page_size= (max 50)
    """
    # TODO
    page_size = None       # TODO
    page_size_query_param = None  # TODO
    max_page_size = None   # TODO


# ─── EXERCICE 2 : ViewSet avec pagination et filtres ────────────────────────

class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet en lecture seule avec :
    - Pagination (ArticlePagination)
    - Recherche dans titre et contenu (?search=)
    - Tri par date_creation, vues, titre (?ordering=)
    - Filtre par statut (?statut=)  ← implémente manuellement dans get_queryset

    TODO : configure tout ci-dessous
    """
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    pagination_class = None    # TODO : ArticlePagination
    filter_backends = []       # TODO : [SearchFilter, OrderingFilter]
    search_fields = []         # TODO
    ordering_fields = []       # TODO
    ordering = []              # TODO : tri par défaut

    def get_queryset(self):
        qs = super().get_queryset()
        statut = self.request.query_params.get("statut")
        # TODO : filtre par statut si présent
        return qs


# ─── URL Router ──────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="article")
urlpatterns = router.urls


# ─── TESTS ───────────────────────────────────────────────────────────────────

def creer_tables_et_donnees():
    from django.db import connection
    with connection.schema_editor() as se:
        try: se.create_model(Article)
        except: pass

    # 20 articles de test
    for i in range(20):
        Article.objects.create(
            titre=f"Article Python {i}" if i % 3 == 0 else f"Article Django {i}",
            contenu=f"Contenu de l'article {i}",
            statut="publie" if i % 2 == 0 else "brouillon",
            vues=i * 50,
        )


def tester():
    creer_tables_et_donnees()
    client = APIClient()
    erreurs = 0

    def ok(n, extra=""): print(f"  OK    {n}{' — ' + extra if extra else ''}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    # Test pagination page 1
    try:
        resp = client.get("/articles/")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data, "La réponse doit avoir 'results' (pagination activée)"
        assert "count" in data
        assert "next" in data
        assert len(data["results"]) == 5, f"Doit avoir 5 résultats, a {len(data['results'])}"
        ok("Pagination page 1", f"count={data['count']}")
    except Exception as e: echec("pagination", e)

    # Test page 2
    try:
        resp = client.get("/articles/?page=2")
        data = resp.json()
        assert data["previous"] is not None
        ok("Pagination page 2")
    except Exception as e: echec("page 2", e)

    # Test page_size custom
    try:
        resp = client.get("/articles/?page_size=3")
        data = resp.json()
        assert len(data["results"]) == 3
        ok("page_size=3")
    except Exception as e: echec("page_size", e)

    # Test recherche
    try:
        resp = client.get("/articles/?search=Python")
        data = resp.json()
        assert data["count"] > 0
        assert all("Python" in a["titre"] for a in data["results"])
        ok("Recherche ?search=Python", f"{data['count']} résultats")
    except Exception as e: echec("search", e)

    # Test tri
    try:
        resp = client.get("/articles/?ordering=-vues&page_size=20")
        data = resp.json()
        vues = [a["vues"] for a in data["results"]]
        assert vues == sorted(vues, reverse=True), "Doit être trié par vues décroissant"
        ok("Tri ?ordering=-vues")
    except Exception as e: echec("ordering", e)

    # Test filtre statut
    try:
        resp = client.get("/articles/?statut=publie&page_size=20")
        data = resp.json()
        assert all(a["statut"] == "publie" for a in data["results"])
        ok("Filtre ?statut=publie", f"{data['count']} résultats")
    except Exception as e: echec("filtre statut", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
