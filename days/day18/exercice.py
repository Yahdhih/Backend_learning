"""
Exercice Jour 18 — Django Models

Définit des models Django et teste les relations.
Lance : python3 exercice.py
"""

import os
import django
from django.conf import settings

# Setup Django minimal
if not settings.configured:
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "__main__",
        ],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
    )
    django.setup()

from django.db import models
from django.contrib.auth.models import User


# ─── EXERCICE 1 : Définir les models ────────────────────────────────────────
#
# Crée les 4 models suivants selon les spécifications.
# Ne change pas les noms des classes ni des champs.

class Categorie(models.Model):
    """
    Catégorie d'article.
    Champs : nom (CharField, 100, unique), slug (SlugField, unique)
    Meta : ordonné par nom, verbose_name correct
    """
    # TODO
    pass

    class Meta:
        app_label = "__main__"


class Tag(models.Model):
    """
    Tag pour les articles.
    Champs : nom (CharField, 50, unique)
    Méthode __str__ qui retourne le nom
    """
    # TODO
    pass

    class Meta:
        app_label = "__main__"


class Article(models.Model):
    """
    Article de blog.
    Champs :
    - titre : CharField, 200
    - slug : SlugField, unique
    - contenu : TextField
    - resume : TextField, blank=True
    - statut : CharField avec choices BROUILLON/PUBLIE/ARCHIVE, default=BROUILLON
    - date_creation : DateTimeField, auto_now_add
    - date_modification : DateTimeField, auto_now
    - vues : IntegerField, default=0
    - categorie : ForeignKey vers Categorie, SET_NULL, null=True, blank=True
    - tags : ManyToManyField vers Tag, blank=True

    Propriétés :
    - est_publie : True si statut == "publie"
    - extrait : 200 premiers chars du contenu

    Méthodes :
    - publier() : passe le statut à "publie" et sauvegarde
    - archiver() : passe le statut à "archive" et sauvegarde

    __str__ : retourne le titre
    Meta : ordonné par -date_creation
    """
    BROUILLON = "brouillon"
    PUBLIE = "publie"
    ARCHIVE = "archive"
    STATUT_CHOICES = [
        (BROUILLON, "Brouillon"),
        (PUBLIE, "Publié"),
        (ARCHIVE, "Archivé"),
    ]

    # TODO : définis tous les champs

    class Meta:
        app_label = "__main__"
        ordering = ["-date_creation"]


class Commentaire(models.Model):
    """
    Commentaire sur un article.
    Champs :
    - article : ForeignKey vers Article, CASCADE, related_name="commentaires"
    - auteur : CharField, 100
    - email : EmailField
    - contenu : TextField
    - date : DateTimeField, auto_now_add
    - approuve : BooleanField, default=False

    __str__ : "Commentaire de {auteur} sur {article.titre}"
    Meta : ordonné par date
    """
    # TODO

    class Meta:
        app_label = "__main__"
        ordering = ["date"]


# ─── EXERCICE 2 : Manager personnalisé ──────────────────────────────────────
#
# Ajoute un manager ArticleManager à la classe Article ci-dessus.
# Le manager doit avoir ces méthodes :
# - publies() : retourne seulement les articles publiés
# - brouillons() : retourne seulement les brouillons
# - populaires(min_vues=10) : articles avec plus de min_vues vues

# TODO : crée la classe ArticleManager(models.Manager) et ajoute
# objects = ArticleManager() dans la classe Article


# ─── TESTS ───────────────────────────────────────────────────────────────────

def creer_tables():
    from django.db import connection
    with connection.schema_editor() as schema_editor:
        for model in [Categorie, Tag, Article, Commentaire]:
            try:
                schema_editor.create_model(model)
            except Exception:
                pass  # table existe déjà


def tester():
    creer_tables()
    erreurs = 0

    def ok(nom):
        print(f"  OK    {nom}")

    def echec(nom, msg):
        nonlocal erreurs
        erreurs += 1
        print(f"  ECHEC {nom}: {msg}")

    # Test Categorie
    try:
        cat = Categorie.objects.create(nom="Python", slug="python")
        assert cat.pk is not None
        assert str(cat) == "Python" or hasattr(cat, "__str__")
        ok("Categorie créée")
    except Exception as e:
        echec("Categorie", str(e))

    # Test Tag
    try:
        tag = Tag.objects.create(nom="django")
        assert str(tag) == "django"
        ok("Tag créé")
    except Exception as e:
        echec("Tag", str(e))

    # Test Article
    try:
        cat = Categorie.objects.first()
        article = Article.objects.create(
            titre="Mon premier article",
            slug="mon-premier-article",
            contenu="Contenu de l'article " * 20,
            categorie=cat,
        )
        assert article.statut == Article.BROUILLON
        assert not article.est_publie
        assert len(article.extrait) <= 200

        article.publier()
        article.refresh_from_db()
        assert article.statut == Article.PUBLIE
        assert article.est_publie
        ok("Article créé et publié")
    except Exception as e:
        echec("Article", str(e))

    # Test ManyToMany
    try:
        article = Article.objects.first()
        tag1 = Tag.objects.create(nom="python")
        tag2 = Tag.objects.create(nom="web")
        article.tags.add(tag1, tag2)
        assert article.tags.count() == 2
        ok("ManyToMany tags")
    except Exception as e:
        echec("ManyToMany", str(e))

    # Test Commentaire
    try:
        article = Article.objects.first()
        comm = Commentaire.objects.create(
            article=article,
            auteur="Alice",
            email="alice@test.com",
            contenu="Super article !",
        )
        assert not comm.approuve
        assert article.commentaires.count() == 1
        ok("Commentaire + related_name")
    except Exception as e:
        echec("Commentaire", str(e))

    # Test Manager
    try:
        Article.objects.create(
            titre="Brouillon",
            slug="brouillon-1",
            contenu="...",
            statut=Article.BROUILLON,
        )
        publies = Article.objects.publies()
        brouillons = Article.objects.brouillons()
        assert publies.count() >= 1
        assert brouillons.count() >= 1
        ok("Manager custom")
    except AttributeError:
        echec("Manager", "ArticleManager non implémenté")
    except Exception as e:
        echec("Manager", str(e))

    print()
    if erreurs == 0:
        print("Tous les tests passent !")
    else:
        print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
