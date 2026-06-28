"""
Exercice Jour 27 — Optimisation ORM et indexes

Mesure les performances et ajoute des indexes.
Lance : python3 exercice.py
"""

import time, django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", "__main__"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        DEBUG=True,
    )
    django.setup()

from django.db import models, connection, reset_queries


class Article(models.Model):
    titre = models.CharField(max_length=200)
    statut = models.CharField(max_length=20, default="publie")
    auteur_email = models.EmailField()
    vues = models.IntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "__main__"
        # TODO Exercice 3 : ajoute les indexes ici


def creer_donnees(n=5000):
    from django.db import connection as conn
    with conn.schema_editor() as se:
        try: se.create_model(Article)
        except: pass

    import random
    statuts = ["publie", "brouillon", "archive"]
    emails = [f"auteur{i}@test.com" for i in range(20)]

    articles = [
        Article(
            titre=f"Article numéro {i}",
            statut=random.choice(statuts),
            auteur_email=random.choice(emails),
            vues=random.randint(0, 10000),
        )
        for i in range(n)
    ]
    Article.objects.bulk_create(articles, batch_size=500)
    print(f"  {Article.objects.count()} articles créés")


def mesurer(label, fn):
    """Mesure le temps et le nombre de requêtes d'une fonction."""
    reset_queries()
    debut = time.perf_counter()
    result = fn()
    duree = (time.perf_counter() - debut) * 1000
    nb_req = len(connection.queries)
    print(f"  {label}: {duree:.1f}ms, {nb_req} requête(s)")
    return result


# ─── EXERCICE 1 : Requêtes de base à optimiser ──────────────────────────────

def compter_publies():
    """Compte les articles publiés. Simple mais peut bénéficier d'un index."""
    # TODO : Article.objects.filter(statut="publie").count()
    pass


def trouver_par_email(email):
    """Trouve tous les articles d'un auteur par email."""
    # TODO : Article.objects.filter(auteur_email=email)
    pass


def articles_populaires(min_vues=1000):
    """Articles avec plus de min_vues vues, triés par vues décroissant."""
    # TODO
    pass


# ─── EXERCICE 2 : only() — charger moins de colonnes ────────────────────────

def titres_seulement():
    """
    Retourne seulement les titres des articles publiés.
    Utilise only("titre") pour ne pas charger tous les champs.
    Compare avec la version sans only().
    """
    # TODO : Article.objects.filter(statut="publie").only("titre")
    pass


# ─── EXERCICE 3 : Ajouter des indexes ───────────────────────────────────────
#
# Dans la classe Meta d'Article ci-dessus, ajoute :
#   indexes = [
#       models.Index(fields=["statut"]),
#       models.Index(fields=["auteur_email"]),
#       models.Index(fields=["-vues"]),
#       models.Index(fields=["statut", "auteur_email"]),  # index composite
#   ]
#
# Note : avec SQLite en mémoire, les indexes sont moins visibles.
# En production avec PostgreSQL, la différence est dramatique.


# ─── EXERCICE 4 : iterator() pour les grands QuerySets ──────────────────────

def traiter_tous_les_articles():
    """
    Traite tous les articles un par un sans les charger tous en mémoire.
    Utilise iterator() pour ne pas tout charger d'un coup.
    Retourne le total des vues.
    """
    # Sans iterator() : charge 5000 articles en mémoire
    # Avec iterator() : traite article par article

    # TODO : Article.objects.iterator(chunk_size=500)
    # Additionne toutes les vues et retourne le total
    pass


# ─── EXERCICE 5 : EXPLAIN — voir le plan de requête ─────────────────────────

def voir_plan_requete():
    """
    Affiche le plan d'exécution EXPLAIN d'une requête SQLite.
    """
    with connection.cursor() as cursor:
        # TODO : cursor.execute("EXPLAIN QUERY PLAN SELECT ...")
        # Affiche les lignes du plan
        cursor.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM __main___article WHERE statut = ?",
            ["publie"]
        )
        rows = cursor.fetchall()
        print("\n  Plan EXPLAIN QUERY PLAN :")
        for row in rows:
            print(f"    {row}")


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    print("Création des données...")
    creer_donnees(2000)

    print("\n--- Benchmark des requêtes ---")
    mesurer("compter_publies", compter_publies)
    mesurer("trouver_par_email", lambda: list(trouver_par_email("auteur1@test.com")))
    mesurer("articles_populaires", lambda: list(articles_populaires()))
    mesurer("titres_seulement", lambda: list(titres_seulement()) if titres_seulement() else None)

    print("\n--- iterator() ---")
    if traiter_tous_les_articles:
        debut = time.perf_counter()
        total = traiter_tous_les_articles()
        duree = (time.perf_counter() - debut) * 1000
        if total:
            print(f"  Total vues : {total} ({duree:.1f}ms)")

    voir_plan_requete()
    print("\nFin de l'exercice. Observe les temps et le plan EXPLAIN.")


if __name__ == "__main__":
    tester()
