# Exercice Jour 19 — Migrations et Admin Django

## Mise en place

```bash
# Crée un projet Django de test
mkdir blog_project && cd blog_project
pip install django
django-admin startproject config .
python manage.py startapp blog
```

Ajoute `"blog"` dans `INSTALLED_APPS` dans `config/settings.py`.

---

## Partie 1 — Premiers models et migration initiale

Dans `blog/models.py`, définis :

```python
from django.db import models

class Categorie(models.Model):
    nom = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.nom

class Article(models.Model):
    BROUILLON = "brouillon"
    PUBLIE = "publie"
    STATUT_CHOICES = [(BROUILLON, "Brouillon"), (PUBLIE, "Publié")]

    titre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    contenu = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default=BROUILLON)
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre
```

```bash
# Génère la migration
python manage.py makemigrations blog

# Regarde le SQL généré
python manage.py sqlmigrate blog 0001

# Applique
python manage.py migrate
```

**Observation :** Combien de tables ont été créées ? Lesquelles ?

---

## Partie 2 — Ajouter un champ (migration évolutive)

Ajoute un champ `vues = models.IntegerField(default=0)` à `Article`.

```bash
python manage.py makemigrations blog --name="add_vues_to_article"
python manage.py sqlmigrate blog 0002
python manage.py migrate
```

**Observation :** Que fait Django avec le `default=0` pour les lignes existantes ?

---

## Partie 3 — Migration de données

Ajoute un champ `resume = models.TextField(blank=True)` à `Article`.

Ensuite crée une migration qui **remplit automatiquement** le résumé avec les 100 premiers caractères du contenu :

```bash
python manage.py makemigrations blog --empty --name="fill_resume"
```

Modifie le fichier généré pour ajouter :

```python
def remplir_resume(apps, schema_editor):
    Article = apps.get_model("blog", "Article")
    for article in Article.objects.all():
        article.resume = article.contenu[:100]
        article.save()

operations = [
    migrations.RunPython(remplir_resume, reverse_code=migrations.RunPython.noop),
]
```

---

## Partie 4 — Configurer l'Admin

Dans `blog/admin.py` :

```python
from django.contrib import admin
from .models import Article, Categorie

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ["nom", "slug"]
    prepopulated_fields = {"slug": ["nom"]}

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["titre", "statut", "categorie", "date_creation", "vues"]
    list_filter = ["statut", "categorie"]
    search_fields = ["titre", "contenu"]
    prepopulated_fields = {"slug": ["titre"]}
    readonly_fields = ["vues", "date_creation"]

    actions = ["publier_selection"]

    @admin.action(description="Publier les articles sélectionnés")
    def publier_selection(self, request, queryset):
        queryset.update(statut="publie")
```

```bash
python manage.py createsuperuser
python manage.py runserver
```

Va sur `http://localhost:8000/admin/` et :
1. Crée 2 catégories
2. Crée 3 articles (1 publié, 2 brouillons)
3. Teste l'action "Publier" sur les brouillons
4. Teste la recherche

---

## Questions dans `notes.md`

1. Pourquoi Django garde-t-il l'historique des migrations dans la table `django_migrations` ?
2. Que se passe-t-il si tu modifies un fichier de migration déjà appliqué ?
3. Quelle est la différence entre `makemigrations` et `migrate` ?
