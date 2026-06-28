"""
Exercice Jour 33 — API CRUD complète (révision DRF)

Une API pour gérer des tâches (Todo list) avec tout ce qu'on a appris.
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
from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.test import APIClient


# ─── MODEL ───────────────────────────────────────────────────────────────────

class Tache(models.Model):
    BASSE = "basse"
    MOYENNE = "moyenne"
    HAUTE = "haute"
    PRIORITE_CHOICES = [(BASSE, "Basse"), (MOYENNE, "Moyenne"), (HAUTE, "Haute")]

    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    complete = models.BooleanField(default=False)
    priorite = models.CharField(max_length=10, choices=PRIORITE_CHOICES, default=MOYENNE)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_echeance = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "__main__"
        ordering = ["-date_creation"]

    def __str__(self):
        return self.titre


# ─── EXERCICE : Implémenter l'API complète ───────────────────────────────────
#
# Implémente les éléments suivants :

class TachePagination(PageNumberPagination):
    """5 tâches par page, max 50."""
    # TODO


class TacheSerializer(serializers.ModelSerializer):
    """
    Sérialise tous les champs.
    Validation custom : titre doit avoir au moins 3 caractères.
    """
    class Meta:
        model = Tache
        fields = "__all__"

    def validate_titre(self, value):
        # TODO : lève ValidationError si len(value) < 3
        return value


class TacheViewSet(viewsets.ModelViewSet):
    """
    ViewSet complet pour les tâches.

    - Pagination : TachePagination
    - Recherche : dans titre et description (?search=)
    - Tri : par date_creation, priorite, date_echeance (?ordering=)
    - Filtre manuel dans get_queryset :
        ?complete=true/false
        ?priorite=haute/moyenne/basse
    - Action "terminer" (detail=True, POST) : passe complete=True, retourne la tâche
    - Action "en_attente" (detail=False, GET) : retourne les tâches non complètes
    - Action "statistiques" (detail=False, GET) : retourne
        {"total": N, "completes": N, "en_attente": N, "par_priorite": {...}}
    """

    queryset = Tache.objects.all()
    serializer_class = TacheSerializer
    # TODO : pagination_class, filter_backends, search_fields, ordering_fields

    def get_queryset(self):
        qs = super().get_queryset()
        # TODO : filtre ?complete= et ?priorite=
        return qs

    @action(detail=True, methods=["post"])
    def terminer(self, request, pk=None):
        # TODO
        pass

    @action(detail=False, methods=["get"])
    def en_attente(self, request):
        # TODO
        pass

    @action(detail=False, methods=["get"])
    def statistiques(self, request):
        # TODO : utilise aggregate() pour calculer les stats
        pass


# ─── URLS ────────────────────────────────────────────────────────────────────

router = DefaultRouter()
router.register("taches", TacheViewSet, basename="tache")
urlpatterns = router.urls


# ─── TESTS ───────────────────────────────────────────────────────────────────

def setup():
    from django.db import connection
    with connection.schema_editor() as se:
        try: se.create_model(Tache)
        except: pass

    taches = [
        Tache(titre=f"Tâche {i}", description=f"Description {i}",
              complete=(i % 3 == 0), priorite=["basse","moyenne","haute"][i % 3])
        for i in range(15)
    ]
    Tache.objects.bulk_create(taches)


def tester():
    setup()
    client = APIClient()
    erreurs = 0

    def ok(n, extra=""): print(f"  OK    {n}{' (' + extra + ')' if extra else ''}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    # CRUD basique
    try:
        resp = client.get("/taches/")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        ok("GET list", f"{data['count']} tâches")
    except Exception as e: echec("list", e)

    try:
        resp = client.post("/taches/", {"titre": "Nouvelle tâche", "priorite": "haute"}, format="json")
        assert resp.status_code == 201
        ok("POST create")
    except Exception as e: echec("create", e)

    try:
        resp = client.post("/taches/", {"titre": "AB"}, format="json")
        assert resp.status_code == 400  # titre trop court
        ok("POST validation titre court → 400")
    except Exception as e: echec("validation", e)

    # Filtre
    try:
        resp = client.get("/taches/?complete=false")
        data = resp.json()
        assert all(not t["complete"] for t in data["results"])
        ok("Filtre ?complete=false")
    except Exception as e: echec("filtre complete", e)

    # Recherche
    try:
        resp = client.get("/taches/?search=Tâche 1")
        data = resp.json()
        assert data["count"] > 0
        ok("Recherche ?search=")
    except Exception as e: echec("search", e)

    # Action terminer
    try:
        tache = Tache.objects.filter(complete=False).first()
        resp = client.post(f"/taches/{tache.pk}/terminer/")
        assert resp.status_code == 200
        assert Tache.objects.get(pk=tache.pk).complete
        ok("Action terminer")
    except Exception as e: echec("terminer", e)

    # Action statistiques
    try:
        resp = client.get("/taches/statistiques/")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data and "completes" in data
        ok("Action statistiques", str(data))
    except Exception as e: echec("statistiques", e)

    print()
    if erreurs == 0: print("Module DRF terminé ! Prêt pour le projet Blog API.")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
