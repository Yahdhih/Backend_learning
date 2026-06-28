"""
Exercice Jour 26 — Le problème N+1

Démonstration et correction du N+1 avec Django ORM.
Lance : python3 exercice.py
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", "__main__"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        DEBUG=True,  # Active le logging des requêtes
    )
    django.setup()

from django.db import models, connection, reset_queries


class Auteur(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    class Meta: app_label = "__main__"
    def __str__(self): return self.nom


class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    class Meta: app_label = "__main__"


class Article(models.Model):
    titre = models.CharField(max_length=200)
    auteur = models.ForeignKey(Auteur, on_delete=models.CASCADE, related_name="articles")
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True, related_name="articles")
    tags = models.ManyToManyField("Tag", blank=True)
    vues = models.IntegerField(default=0)
    class Meta: app_label = "__main__"


class Tag(models.Model):
    nom = models.CharField(max_length=50)
    class Meta: app_label = "__main__"


def compter_requetes(fn):
    """Decorator qui compte les requêtes SQL d'une fonction."""
    def wrapper(*args, **kwargs):
        reset_queries()
        result = fn(*args, **kwargs)
        nb = len(connection.queries)
        return result, nb
    return wrapper


def creer_donnees():
    from django.db import connection as conn
    with conn.schema_editor() as se:
        for m in [Auteur, Categorie, Tag, Article, Article.tags.through]:
            try: se.create_model(m)
            except: pass

    auteurs = [Auteur.objects.create(nom=f"Auteur {i}", email=f"auteur{i}@test.com") for i in range(5)]
    cats = [Categorie.objects.create(nom=f"Cat {i}") for i in range(3)]
    tags = [Tag.objects.create(nom=f"tag{i}") for i in range(4)]

    articles = []
    for i in range(10):
        a = Article.objects.create(
            titre=f"Article {i}",
            auteur=auteurs[i % 5],
            categorie=cats[i % 3],
            vues=i * 10,
        )
        a.tags.set(tags[:2] if i % 2 == 0 else tags[2:])
        articles.append(a)


# ─── EXERCICE 1 : Créer le problème N+1 ─────────────────────────────────────

def lister_articles_naif():
    """
    Liste tous les articles avec nom de l'auteur et de la catégorie.
    VERSION NAÏVE : génère N+1 requêtes.
    Ne modifie pas cette fonction — elle sert de référence.
    """
    articles = Article.objects.all()
    resultat = []
    for article in articles:
        resultat.append({
            "titre": article.titre,
            "auteur": article.auteur.nom,       # 1 requête par article !
            "categorie": article.categorie.nom if article.categorie else None,  # idem
        })
    return resultat


# ─── EXERCICE 2 : Corriger avec select_related ───────────────────────────────

def lister_articles_optimise():
    """
    Même résultat que lister_articles_naif() mais en UNE SEULE requête SQL.
    Utilise select_related() pour les ForeignKey.

    Doit retourner exactement le même format de données.
    """
    # TODO : Article.objects.select_related("auteur", "categorie").all()
    # puis boucle identique
    pass


# ─── EXERCICE 3 : ManyToMany avec prefetch_related ──────────────────────────

def lister_articles_avec_tags_naif():
    """VERSION NAÏVE avec N+1 sur les tags."""
    resultat = []
    for article in Article.objects.all():
        resultat.append({
            "titre": article.titre,
            "tags": [tag.nom for tag in article.tags.all()],  # N+1 !
        })
    return resultat


def lister_articles_avec_tags_optimise():
    """
    Même résultat mais optimisé.
    Utilise prefetch_related("tags") pour les ManyToMany.
    """
    # TODO
    pass


# ─── EXERCICE 4 : Combinaison select_related + prefetch_related ──────────────

def lister_articles_complet_optimise():
    """
    Retourne pour chaque article :
    - titre
    - auteur (nom)
    - categorie (nom)
    - tags (liste de noms)

    En le moins de requêtes possible (idéalement 2 : 1 SELECT + 1 pour les tags).
    """
    # TODO : select_related("auteur", "categorie") + prefetch_related("tags")
    pass


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    creer_donnees()
    erreurs = 0

    def ok(n, nb_req): print(f"  OK    {n} ({nb_req} requêtes SQL)")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    # Version naïve
    res_naif, nb_naif = compter_requetes(lister_articles_naif)()
    print(f"\n  Version naïve : {nb_naif} requêtes SQL pour 10 articles")
    assert nb_naif > 5, "La version naïve devrait faire beaucoup de requêtes"

    # Version optimisée select_related
    try:
        res_opt, nb_opt = compter_requetes(lister_articles_optimise)()
        assert res_opt == res_naif, "Les données doivent être identiques"
        assert nb_opt <= 2, f"select_related doit faire ≤2 requêtes, fait {nb_opt}"
        ok("select_related", nb_opt)
    except Exception as e: echec("select_related", e)

    # Version naïve tags
    _, nb_naif_tags = compter_requetes(lister_articles_avec_tags_naif)()
    print(f"  Tags naïf : {nb_naif_tags} requêtes")

    # Version optimisée prefetch
    try:
        res_pref, nb_pref = compter_requetes(lister_articles_avec_tags_optimise)()
        assert nb_pref <= 3, f"prefetch_related doit faire ≤3 requêtes, fait {nb_pref}"
        ok("prefetch_related", nb_pref)
    except Exception as e: echec("prefetch_related", e)

    # Version complète
    try:
        _, nb_complet = compter_requetes(lister_articles_complet_optimise)()
        assert nb_complet <= 3, f"Version complète doit faire ≤3 requêtes, fait {nb_complet}"
        ok("complet (select + prefetch)", nb_complet)
    except Exception as e: echec("complet", e)

    print(f"\n  Réduction : {nb_naif} requêtes → {nb_opt if 'nb_opt' in dir() else '?'} requêtes")
    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
