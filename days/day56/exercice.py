"""
Exercice Jour 56 — Optimisation SQL avec Django ORM

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


class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    class Meta: app_label = "__main__"


class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    statut = models.CharField(max_length=20, default="publie")
    vues = models.IntegerField(default=0)
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE, related_name="articles", null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "__main__"
        # TODO Exercice 3 : ajoute les indexes ici
        # indexes = [
        #     models.Index(fields=["statut"]),
        #     models.Index(fields=["-vues"]),
        #     models.Index(fields=["statut", "categorie"]),
        # ]


def mesurer(label, fn):
    reset_queries()
    debut = time.perf_counter()
    result = fn()
    duree = (time.perf_counter() - debut) * 1000
    nb = len(connection.queries)
    return result, duree, nb


def creer_donnees(n=3000):
    from django.db import connection as c
    with c.schema_editor() as se:
        for m in [Categorie, Article]:
            try: se.create_model(m)
            except: pass

    cats = [Categorie.objects.create(nom=f"Cat {i}") for i in range(10)]

    import random
    articles = [
        Article(
            titre=f"Article {i} Python" if i % 5 == 0 else f"Article {i}",
            contenu="x" * 500,    # simuler un gros contenu
            statut="publie" if i % 3 != 0 else "brouillon",
            vues=random.randint(0, 5000),
            categorie=random.choice(cats),
        )
        for i in range(n)
    ]
    Article.objects.bulk_create(articles, batch_size=500)
    print(f"  {Article.objects.count()} articles créés")


# ─── EXERCICE 1 : count() vs len() ──────────────────────────────────────────

def compter_mauvais():
    """Mauvaise façon — charge tous les objets."""
    return len(Article.objects.filter(statut="publie"))

def compter_bon():
    """Bonne façon — COUNT(*) SQL."""
    # TODO
    pass


# ─── EXERCICE 2 : only() vs SELECT * ────────────────────────────────────────

def lister_titres_mauvais():
    """Charge tous les champs y compris contenu (gros)."""
    return [a.titre for a in Article.objects.filter(statut="publie")]

def lister_titres_bon():
    """Charge seulement titre et id."""
    # TODO : .only("titre") ou .values("titre")
    pass


# ─── EXERCICE 3 : exists() vs count() > 0 ───────────────────────────────────

def verifier_mauvais(categorie_id):
    return Article.objects.filter(categorie_id=categorie_id).count() > 0

def verifier_bon(categorie_id):
    """Utilise exists() — plus rapide."""
    # TODO
    pass


# ─── EXERCICE 4 : iterator() pour grands volumes ────────────────────────────

def calculer_total_vues_mauvais():
    """Charge tous les articles en mémoire."""
    total = 0
    for article in Article.objects.all():
        total += article.vues
    return total

def calculer_total_vues_bon():
    """Avec iterator() — ne charge jamais tout en mémoire."""
    total = 0
    # TODO : Article.objects.iterator(chunk_size=200)
    pass

def calculer_total_vues_optimal():
    """Encore mieux : un seul SUM() SQL."""
    from django.db.models import Sum
    # TODO : aggregate(Sum("vues"))
    pass


# ─── EXERCICE 5 : EXPLAIN ────────────────────────────────────────────────────

def voir_explain():
    """Affiche le plan EXPLAIN pour plusieurs requêtes."""
    print("\n  Plans EXPLAIN :")
    requetes = [
        ("Sans index (statut)", "SELECT * FROM __main___article WHERE statut = 'publie'"),
        ("Tri par vues", "SELECT * FROM __main___article ORDER BY vues DESC LIMIT 10"),
        ("COUNT(*)", "SELECT COUNT(*) FROM __main___article WHERE statut = 'publie'"),
    ]
    with connection.cursor() as c:
        for label, sql in requetes:
            c.execute(f"EXPLAIN QUERY PLAN {sql}")
            plan = c.fetchall()
            print(f"  {label}: {plan}")


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    print("Création des données...")
    creer_donnees(1500)

    print("\n--- Benchmark ---")

    _, t1, _ = mesurer("count mauvais (len)", compter_mauvais)
    if compter_bon():
        _, t2, _ = mesurer("count bon (COUNT)", compter_bon)
        print(f"  count: len={t1:.1f}ms vs COUNT={t2:.1f}ms {'✓ amélioration' if t2 < t1 else ''}")
    else:
        print(f"  count mauvais: {t1:.1f}ms (TODO: implémenter compter_bon)")

    _, t3, _ = mesurer("SELECT * (mauvais)", lister_titres_mauvais)
    if lister_titres_bon():
        _, t4, _ = mesurer("only() (bon)", lister_titres_bon)
        print(f"  select: SELECT*={t3:.1f}ms vs only={t4:.1f}ms")
    else:
        print(f"  SELECT* : {t3:.1f}ms (TODO: implémenter lister_titres_bon)")

    cat_id = Categorie.objects.first().pk
    _, t5, _ = mesurer("count>0 (mauvais)", lambda: verifier_mauvais(cat_id))
    if verifier_bon(cat_id) is not None:
        _, t6, _ = mesurer("exists() (bon)", lambda: verifier_bon(cat_id))
        print(f"  exists: count>{t5:.1f}ms vs exists={t6:.1f}ms")

    _, t7, _ = mesurer("total vues boucle", calculer_total_vues_mauvais)
    if calculer_total_vues_bon():
        _, t8, _ = mesurer("iterator()", calculer_total_vues_bon)
        print(f"  iterator: boucle={t7:.1f}ms vs iterator={t8:.1f}ms")
    if calculer_total_vues_optimal():
        _, t9, _ = mesurer("SUM SQL", calculer_total_vues_optimal)
        print(f"  SUM SQL={t9:.1f}ms (le plus rapide)")

    voir_explain()
    print("\nConseils : ajoute les indexes dans Meta et relance pour voir l'amélioration.")


if __name__ == "__main__":
    tester()
