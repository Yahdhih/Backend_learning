"""
Exercice Jour 24 — Django ORM avancé : annotate, aggregate, Q, F

Lance : python3 exercice.py
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", "__main__"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )
    django.setup()

from django.db import models
from django.db.models import Count, Sum, Avg, Q, F, Max, Min


class Auteur(models.Model):
    nom = models.CharField(max_length=100)
    class Meta: app_label = "__main__"

class Article(models.Model):
    titre = models.CharField(max_length=200)
    auteur = models.ForeignKey(Auteur, on_delete=models.CASCADE, related_name="articles")
    vues = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    publie = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    class Meta: app_label = "__main__"

class Commentaire(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="commentaires")
    texte = models.TextField()
    class Meta: app_label = "__main__"


def creer_donnees():
    from django.db import connection
    with connection.schema_editor() as se:
        for m in [Auteur, Article, Commentaire]:
            try: se.create_model(m)
            except: pass

    alice = Auteur.objects.create(nom="Alice")
    bob = Auteur.objects.create(nom="Bob")

    a1 = Article.objects.create(titre="Python avancé", auteur=alice, vues=500, likes=50)
    a2 = Article.objects.create(titre="Django REST", auteur=alice, vues=300, likes=30)
    a3 = Article.objects.create(titre="JavaScript", auteur=bob, vues=100, likes=10)
    a4 = Article.objects.create(titre="Brouillon", auteur=bob, vues=0, likes=0, publie=False)

    Commentaire.objects.create(article=a1, texte="Super !")
    Commentaire.objects.create(article=a1, texte="Merci")
    Commentaire.objects.create(article=a1, texte="Excellent")
    Commentaire.objects.create(article=a2, texte="Très utile")


# ─── EXERCICE 1 : annotate — ajouter des calculs par objet ──────────────────

def auteurs_avec_stats():
    """
    Retourne tous les auteurs avec :
    - nb_articles : nombre total d'articles
    - nb_articles_publies : nombre d'articles publiés
    - total_vues : somme des vues de tous leurs articles

    Utilise annotate() avec Count() et Sum().

    Résultat attendu (ordre alphabétique par nom) :
    [
        {"nom": "Alice", "nb_articles": 2, "nb_articles_publies": 2, "total_vues": 800},
        {"nom": "Bob", "nb_articles": 2, "nb_articles_publies": 1, "total_vues": 100},
    ]
    """
    # TODO : annotate + values + order_by
    pass


def articles_avec_nb_commentaires():
    """
    Retourne les articles publiés avec leur nombre de commentaires.
    Trié par nombre de commentaires décroissant.

    Résultat attendu :
    [
        {"titre": "Python avancé", "nb_commentaires": 3},
        {"titre": "Django REST", "nb_commentaires": 1},
        {"titre": "JavaScript", "nb_commentaires": 0},
    ]
    """
    # TODO : annotate + Count + filter(publie=True) + order_by
    pass


# ─── EXERCICE 2 : aggregate — calculer des stats globales ───────────────────

def stats_globales():
    """
    Retourne un dict avec les statistiques globales sur les articles publiés :
    - total : nombre d'articles publiés
    - vues_totales : somme de toutes les vues
    - vues_moyennes : moyenne des vues (arrondie à 2 décimales)
    - article_le_plus_vu : nombre de vues max
    - article_le_moins_vu : nombre de vues min

    Résultat attendu :
    {"total": 3, "vues_totales": 900, "vues_moyennes": 300.0, ...}
    """
    # TODO : filter(publie=True).aggregate(...)
    pass


# ─── EXERCICE 3 : Q objects — conditions complexes ──────────────────────────

def articles_populaires_ou_recents(min_vues=200, min_likes=25):
    """
    Retourne les articles qui ont SOIT plus de min_vues vues
    SOIT plus de min_likes likes.
    (Publiés seulement.)

    Utilise Q(vues__gt=...) | Q(likes__gt=...)
    """
    # TODO
    pass


def articles_ni_vus_ni_aimes():
    """
    Retourne les articles avec 0 vues ET 0 likes.
    Utilise Q objects avec &.
    """
    # TODO
    pass


# ─── EXERCICE 4 : F expressions — références à d'autres champs ──────────────

def articles_plus_likes_que_vues_divise_10():
    """
    Retourne les articles où likes > vues / 10
    (articles avec un bon ratio likes/vues).

    Utilise F("vues") / 10 dans le filtre.
    """
    # TODO : filter(likes__gt=F("vues") / 10)
    pass


def doubler_vues_articles_populaires(min_vues=100):
    """
    Pour les articles avec plus de min_vues vues,
    double le compteur de vues en une seule requête SQL.

    Utilise update(vues=F("vues") * 2)
    Retourne le nombre d'articles modifiés.
    """
    # TODO : filter(...).update(vues=F("vues") * 2)
    pass


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    creer_donnees()
    erreurs = 0

    def ok(n): print(f"  OK    {n}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    try:
        stats = auteurs_avec_stats()
        assert stats is not None, "Retourne quelque chose"
        stats_list = list(stats)
        assert len(stats_list) == 2
        alice = next(s for s in stats_list if s["nom"] == "Alice")
        assert alice["nb_articles"] == 2
        assert alice["total_vues"] == 800
        ok("auteurs_avec_stats")
    except Exception as e: echec("auteurs_avec_stats", e)

    try:
        arts = list(articles_avec_nb_commentaires())
        assert arts[0]["titre"] == "Python avancé"
        assert arts[0]["nb_commentaires"] == 3
        ok("articles_avec_nb_commentaires")
    except Exception as e: echec("articles_avec_nb_commentaires", e)

    try:
        stats = stats_globales()
        assert stats["total"] == 3
        assert stats["vues_totales"] == 900
        ok("stats_globales")
    except Exception as e: echec("stats_globales", e)

    try:
        arts = list(articles_populaires_ou_recents())
        titres = [a.titre for a in arts]
        assert "Python avancé" in titres  # 500 vues
        assert "Django REST" in titres    # 300 vues
        assert "JavaScript" not in titres # 100 vues, 10 likes — en dessous des seuils
        ok("articles_populaires_ou_recents")
    except Exception as e: echec("articles_populaires_ou_recents", e)

    try:
        nb = doubler_vues_articles_populaires(min_vues=100)
        assert nb >= 2  # au moins Python avancé et Django REST
        ok(f"doubler_vues ({nb} articles modifiés)")
    except Exception as e: echec("doubler_vues", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
