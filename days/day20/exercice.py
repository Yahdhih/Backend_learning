"""
Exercice Jour 20 — Mini API Django sans DRF (révision complète)

Une API JSON pour un blog : list, detail, create, delete.
Lance : python3 exercice.py
"""

import os, json, django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", "__main__"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        ROOT_URLCONF="__main__",
    )
    django.setup()

from django.db import models
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.urls import path
from django.test import RequestFactory, TestCase
import json as _json


# ─── MODELS ──────────────────────────────────────────────────────────────────

class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    statut = models.CharField(
        max_length=20,
        choices=[("brouillon", "Brouillon"), ("publie", "Publié")],
        default="brouillon",
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "__main__"
        ordering = ["-date_creation"]

    def to_dict(self):
        return {
            "id": self.pk,
            "titre": self.titre,
            "contenu": self.contenu,
            "statut": self.statut,
            "date_creation": self.date_creation.isoformat() if self.date_creation else None,
        }


# ─── EXERCICE 1 : Vue liste et création ──────────────────────────────────────

class ArticleListView(View):
    """
    GET /api/articles/  → liste tous les articles (JSON)
    POST /api/articles/ → crée un article depuis le body JSON

    Format du body POST :
    {"titre": "Mon article", "contenu": "Contenu...", "statut": "publie"}

    Réponses :
    - GET : 200 + liste d'articles
    - POST valide : 201 + article créé
    - POST sans titre : 400 + {"error": "Le titre est obligatoire"}
    - Méthode non autorisée : 405
    """

    def get(self, request):
        # TODO : récupère tous les articles et retourne en JSON
        pass

    def post(self, request):
        # TODO :
        # 1. Parse request.body en JSON
        # 2. Valide que "titre" est présent
        # 3. Crée l'article
        # 4. Retourne 201 avec l'article créé
        pass


# ─── EXERCICE 2 : Vue détail, modification, suppression ──────────────────────

class ArticleDetailView(View):
    """
    GET /api/articles/{id}/    → détail d'un article
    PUT /api/articles/{id}/    → remplace entièrement l'article
    DELETE /api/articles/{id}/ → supprime l'article

    Réponses :
    - Article inexistant : 404 + {"error": "Article introuvable"}
    - GET : 200 + article
    - PUT : 200 + article modifié
    - DELETE : 204 (No Content, pas de body)
    """

    def get_article(self, pk):
        # TODO : récupère l'article ou retourne None
        pass

    def get(self, request, pk):
        # TODO
        pass

    def put(self, request, pk):
        # TODO : parse JSON, met à jour les champs, sauvegarde
        pass

    def delete(self, request, pk):
        # TODO : supprime et retourne 204
        pass


# ─── EXERCICE 3 : Filtrage par statut ────────────────────────────────────────

class ArticlePubliesView(View):
    """
    GET /api/articles/publies/ → liste seulement les articles publiés
    Supporte aussi ?search=terme pour filtrer par titre
    """

    def get(self, request):
        # TODO :
        # 1. Récupère seulement les articles publiés
        # 2. Si request.GET.get("search"), filtre aussi par titre (icontains)
        # 3. Retourne en JSON
        pass


# ─── URL configuration ────────────────────────────────────────────────────────

urlpatterns = [
    path("api/articles/", ArticleListView.as_view()),
    path("api/articles/publies/", ArticlePubliesView.as_view()),
    path("api/articles/<int:pk>/", ArticleDetailView.as_view()),
]


# ─── TESTS ───────────────────────────────────────────────────────────────────

def creer_tables():
    from django.db import connection
    with connection.schema_editor() as se:
        try:
            se.create_model(Article)
        except Exception:
            pass


def tester():
    creer_tables()
    factory = RequestFactory()
    erreurs = 0

    def ok(nom): print(f"  OK    {nom}")
    def echec(nom, msg):
        nonlocal erreurs; erreurs += 1
        print(f"  ECHEC {nom}: {msg}")

    # Test GET liste vide
    try:
        req = factory.get("/api/articles/")
        resp = ArticleListView.as_view()(req)
        assert resp.status_code == 200
        data = _json.loads(resp.content)
        assert isinstance(data, list)
        ok("GET liste vide")
    except Exception as e:
        echec("GET liste", str(e))

    # Test POST création
    try:
        req = factory.post("/api/articles/",
            data=_json.dumps({"titre": "Test", "contenu": "Contenu"}),
            content_type="application/json")
        resp = ArticleListView.as_view()(req)
        assert resp.status_code == 201, f"Attendu 201, obtenu {resp.status_code}"
        data = _json.loads(resp.content)
        assert data["titre"] == "Test"
        ok("POST créer article")
    except Exception as e:
        echec("POST créer", str(e))

    # Test POST sans titre → 400
    try:
        req = factory.post("/api/articles/",
            data=_json.dumps({"contenu": "Sans titre"}),
            content_type="application/json")
        resp = ArticleListView.as_view()(req)
        assert resp.status_code == 400
        ok("POST sans titre → 400")
    except Exception as e:
        echec("POST validation", str(e))

    # Test GET détail
    try:
        article = Article.objects.first()
        req = factory.get(f"/api/articles/{article.pk}/")
        resp = ArticleDetailView.as_view()(req, pk=article.pk)
        assert resp.status_code == 200
        data = _json.loads(resp.content)
        assert data["id"] == article.pk
        ok("GET détail")
    except Exception as e:
        echec("GET détail", str(e))

    # Test GET 404
    try:
        req = factory.get("/api/articles/9999/")
        resp = ArticleDetailView.as_view()(req, pk=9999)
        assert resp.status_code == 404
        ok("GET 404")
    except Exception as e:
        echec("GET 404", str(e))

    # Test DELETE
    try:
        article = Article.objects.create(titre="À supprimer", contenu="...")
        pk = article.pk
        req = factory.delete(f"/api/articles/{pk}/")
        resp = ArticleDetailView.as_view()(req, pk=pk)
        assert resp.status_code == 204
        assert not Article.objects.filter(pk=pk).exists()
        ok("DELETE article")
    except Exception as e:
        echec("DELETE", str(e))

    # Test filtre publiés
    try:
        Article.objects.create(titre="Publié", contenu="...", statut="publie")
        req = factory.get("/api/articles/publies/")
        resp = ArticlePubliesView.as_view()(req)
        assert resp.status_code == 200
        data = _json.loads(resp.content)
        assert all(a["statut"] == "publie" for a in data)
        ok("GET filtre publiés")
    except Exception as e:
        echec("GET publiés", str(e))

    print()
    if erreurs == 0:
        print("Tous les tests passent ! Module Django terminé.")
    else:
        print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
