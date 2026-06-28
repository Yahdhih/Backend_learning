# Jour 19 — Django : Migrations et Admin
📅 15 juillet 2026 · Module : Django

---

## Les migrations : comment Django synchronise le code et la base

Une migration est un fichier Python qui décrit **comment faire évoluer le schéma de la base de données**.

```
Ton code Python (models.py)
         ↕  makemigrations compare
Fichiers de migration (0001_initial.py, 0002_add_field.py...)
         ↕  migrate applique
Base de données (tables SQL)
```

---

## Les commandes essentielles

```bash
# Générer les migrations depuis les models
python manage.py makemigrations

# Voir le SQL qui sera exécuté (sans l'appliquer)
python manage.py sqlmigrate blog 0001

# Appliquer les migrations en attente
python manage.py migrate

# Voir l'état des migrations (quelles sont appliquées)
python manage.py showmigrations

# Revenir à une migration précédente (rollback)
python manage.py migrate blog 0001

# Revenir à zéro (supprime toutes les tables de l'app)
python manage.py migrate blog zero
```

---

## Structure d'un fichier de migration

```python
# blog/migrations/0002_article_vues.py
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0001_initial"),   # dépend de la migration précédente
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="vues",
            field=models.IntegerField(default=0),
        ),
    ]
```

---

## Opérations de migration courantes

```python
# Créer un model complet
migrations.CreateModel(name="Article", fields=[...])

# Ajouter un champ
migrations.AddField(model_name="article", name="vues", field=models.IntegerField(default=0))

# Modifier un champ
migrations.AlterField(model_name="article", name="titre", field=models.CharField(max_length=500))

# Supprimer un champ
migrations.RemoveField(model_name="article", name="ancien_champ")

# Renommer un champ
migrations.RenameField(model_name="article", old_name="body", new_name="contenu")

# Ajouter/supprimer un index
migrations.AddIndex(model_name="article", index=models.Index(fields=["titre"]))

# Exécuter du Python (migration de données)
migrations.RunPython(ma_fonction, reverse_code=migrations.RunPython.noop)

# Exécuter du SQL brut
migrations.RunSQL("UPDATE blog_article SET vues = 0 WHERE vues IS NULL")
```

---

## Migration de données avec RunPython

Quand tu dois **transformer des données existantes** (pas juste le schéma) :

```python
def remplir_slugs(apps, schema_editor):
    """Génère des slugs pour les articles qui n'en ont pas."""
    Article = apps.get_model("blog", "Article")  # version historique du model
    from django.utils.text import slugify

    for article in Article.objects.filter(slug=""):
        article.slug = slugify(article.titre)
        article.save()

def annuler_slugs(apps, schema_editor):
    """Rollback : vider les slugs."""
    Article = apps.get_model("blog", "Article")
    Article.objects.all().update(slug="")


class Migration(migrations.Migration):
    dependencies = [("blog", "0003_add_slug_field")]

    operations = [
        migrations.RunPython(remplir_slugs, reverse_code=annuler_slugs),
    ]
```

**Important :** Dans `RunPython`, toujours utiliser `apps.get_model()` et jamais importer le model directement. Le model peut avoir changé depuis.

---

## L'admin Django

L'admin est une interface web auto-générée pour gérer les données. C'est l'un des points forts de Django.

```python
# blog/admin.py
from django.contrib import admin
from .models import Article, Categorie, Commentaire

# Enregistrement simple
admin.site.register(Categorie)

# Enregistrement avec configuration
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    # Colonnes dans la liste
    list_display = ["titre", "auteur", "statut", "date_creation", "vues"]

    # Filtres latéraux
    list_filter = ["statut", "categorie", "date_creation"]

    # Barre de recherche
    search_fields = ["titre", "contenu", "auteur__username"]

    # Champs en lecture seule
    readonly_fields = ["date_creation", "date_modification", "vues"]

    # Organisation des champs dans le formulaire
    fieldsets = [
        ("Contenu", {
            "fields": ["titre", "slug", "contenu", "resume"]
        }),
        ("Publication", {
            "fields": ["statut", "categorie", "tags"],
        }),
        ("Statistiques", {
            "fields": ["vues", "date_creation", "date_modification"],
            "classes": ["collapse"],  # section repliable
        }),
    ]

    # Prépopuler le slug depuis le titre
    prepopulated_fields = {"slug": ["titre"]}

    # Actions batch (s'appliquent à plusieurs objets sélectionnés)
    actions = ["publier_articles", "archiver_articles"]

    @admin.action(description="Publier les articles sélectionnés")
    def publier_articles(self, request, queryset):
        queryset.update(statut="publie")

    @admin.action(description="Archiver les articles sélectionnés")
    def archiver_articles(self, request, queryset):
        queryset.update(statut="archive")

    # Optimisation : éviter N+1 dans l'admin
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("auteur", "categorie")
```

---

## Admin inline : éditer des objets liés sur la même page

```python
class CommentaireInline(admin.TabularInline):
    model = Commentaire
    extra = 1                          # 1 formulaire vide par défaut
    readonly_fields = ["date"]
    fields = ["auteur", "contenu", "approuve", "date"]

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    inlines = [CommentaireInline]
    ...
```

---

## Créer un superuser

```bash
python manage.py createsuperuser
# → demande username, email, password
```

Puis aller sur `http://localhost:8000/admin/`
