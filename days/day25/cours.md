# Jour 25 — Migrations Django en profondeur (21 juillet 2026)

---

## Introduction

Les migrations Django sont le système de versionnement du schéma de base de données. Chaque changement de modèle (ajout d'un champ, création d'une table, modification d'un index) est capturé dans un fichier de migration Python. Ces fichiers forment une chaîne : chaque migration connaît ses dépendances et peut être appliquée ou annulée dans l'ordre.

---

## 1. Structure d'un fichier de migration

Voici un fichier de migration typique, annoté pour en comprendre chaque partie :

```python
# blog/migrations/0002_post_add_slug.py

from django.db import migrations, models


class Migration(migrations.Migration):

    # Liste des migrations qui doivent être appliquées avant celle-ci
    # Format : ('nom_de_lapp', 'nom_de_la_migration')
    dependencies = [
        ('blog', '0001_initial'),
    ]

    # Liste des opérations à exécuter dans l'ordre
    operations = [
        migrations.AddField(
            model_name='post',
            name='slug',
            field=models.SlugField(max_length=200, unique=True, default=''),
            # default requis car colonne NOT NULL sur table existante
            preserve_default=False,  # le défaut est temporaire, pas dans le modèle
        ),
    ]
```

---

## 2. Les opérations principales

### CreateModel et DeleteModel

```python
migrations.CreateModel(
    name='Tag',
    fields=[
        ('id', models.AutoField(auto_created=True, primary_key=True)),
        ('name', models.CharField(max_length=50, unique=True)),
        ('slug', models.SlugField(unique=True)),
    ],
)

migrations.DeleteModel(
    name='OldModel',
)
```

### AddField et RemoveField

```python
# Ajouter un champ nullable (pas de default obligatoire)
migrations.AddField(
    model_name='post',
    name='subtitle',
    field=models.CharField(max_length=200, blank=True, default=''),
)

# Ajouter un champ NOT NULL sur une table existante
# → il faut fournir un default (temporaire si preserve_default=False)
migrations.AddField(
    model_name='post',
    name='views',
    field=models.PositiveIntegerField(default=0),
)

# Supprimer un champ
migrations.RemoveField(
    model_name='post',
    name='old_field',
)
```

### AlterField — modifier un champ existant

```python
# Changer la taille max d'un CharField
migrations.AlterField(
    model_name='post',
    name='title',
    field=models.CharField(max_length=300),  # était 200
)
```

### RenameField et RenameModel

```python
migrations.RenameField(
    model_name='post',
    old_name='content',
    new_name='body',
)

migrations.RenameModel(
    old_name='Article',
    new_name='Post',
)
```

### AddIndex et RemoveIndex

```python
migrations.AddIndex(
    model_name='post',
    index=models.Index(fields=['created_at'], name='blog_post_created_at_idx'),
)

migrations.RemoveIndex(
    model_name='post',
    name='blog_post_created_at_idx',
)
```

---

## 3. Migrations de données avec RunPython

`RunPython` exécute du code Python arbitraire pendant la migration. C'est l'outil pour les **migrations de données** : transformer des données existantes, remplir un nouveau champ, etc.

### Structure d'une migration de données

```python
# blog/migrations/0004_populate_slug.py

from django.db import migrations
from django.utils.text import slugify


def remplir_slugs(apps, schema_editor):
    """
    Fonction forward : s'exécute lors de `migrate`.

    IMPORTANT : Toujours utiliser `apps.get_model()` pour récupérer
    le modèle — jamais importer le modèle directement. Cela garantit
    qu'on utilise la version historique du modèle (compatible avec
    l'état du schéma à ce moment précis de la chaîne de migrations).
    """
    Post = apps.get_model('blog', 'Post')

    for post in Post.objects.all():
        if not post.slug:
            post.slug = slugify(post.title)
            post.save(update_fields=['slug'])


def retirer_slugs(apps, schema_editor):
    """
    Fonction backward : s'exécute lors de `migrate blog 0003`
    pour revenir en arrière.
    """
    Post = apps.get_model('blog', 'Post')
    Post.objects.all().update(slug='')


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0003_post_add_slug_field'),
    ]

    operations = [
        migrations.RunPython(
            code=remplir_slugs,
            reverse_code=retirer_slugs,
        ),
    ]
```

### RunPython avec noop pour les migrations irréversibles

```python
# Si la migration ne peut pas être annulée
migrations.RunPython(
    code=ma_fonction,
    reverse_code=migrations.RunPython.noop,  # ne fait rien en cas de rollback
)
```

---

## 4. RunSQL — exécuter du SQL brut

```python
migrations.RunSQL(
    sql="""
        UPDATE blog_post
        SET status = 'published'
        WHERE is_published = TRUE AND status IS NULL;
    """,
    reverse_sql="""
        UPDATE blog_post
        SET status = NULL
        WHERE is_published = TRUE;
    """,
)
```

Utile pour des opérations que l'ORM ne supporte pas directement : triggers, vues SQL, extensions PostgreSQL, etc.

---

## 5. Commandes essentielles

### makemigrations — détecter les changements

```python
# Détecter et créer toutes les migrations nécessaires
python manage.py makemigrations

# Pour une application spécifique
python manage.py makemigrations blog

# Avec un nom explicite
python manage.py makemigrations blog --name add_slug_to_post

# Voir ce qui serait généré sans créer le fichier
python manage.py makemigrations --dry-run --verbosity 3
```

### migrate — appliquer les migrations

```python
# Appliquer toutes les migrations en attente
python manage.py migrate

# Appliquer jusqu'à une migration spécifique (rollback partiel)
python manage.py migrate blog 0002

# Revenir à l'état avant toutes les migrations d'une app
python manage.py migrate blog zero
```

### showmigrations — voir l'état

```python
# Liste toutes les migrations et leur état (X = appliquée)
python manage.py showmigrations

# Pour une app spécifique
python manage.py showmigrations blog
```

Exemple de sortie :
```
blog
 [X] 0001_initial
 [X] 0002_post_add_slug
 [ ] 0003_post_add_views   ← pas encore appliquée
```

### sqlmigrate — voir le SQL généré

```python
# Affiche le SQL qu'une migration va exécuter (sans l'exécuter)
python manage.py sqlmigrate blog 0002

# Exemple de sortie :
# BEGIN;
# --
# -- Add field slug to post
# --
# ALTER TABLE "blog_post" ADD COLUMN "slug" varchar(200) DEFAULT '' NOT NULL;
# ALTER TABLE "blog_post" ALTER COLUMN "slug" DROP DEFAULT;
# CREATE UNIQUE INDEX "blog_post_slug_key" ON "blog_post" ("slug");
# COMMIT;
```

Très utile pour :
- Vérifier ce que Django va faire avant de l'exécuter en production
- Comprendre comment Django traduit vos modèles en SQL
- Partager le SQL avec un DBA pour revue

---

## 6. Squashing — fusionner des migrations

Quand une application a accumulé des dizaines de migrations, on peut les "squasher" (fusionner) en une seule pour accélérer les déploiements et nettoyer l'historique.

```python
# Fusionner les migrations 0001 à 0020 en une seule
python manage.py squashmigrations blog 0001 0020

# Résultat : un nouveau fichier 0001_squashed_0020_*.py
```

Le fichier squashé contient la liste des migrations qu'il remplace :
```python
class Migration(migrations.Migration):
    replaces = [
        ('blog', '0001_initial'),
        ('blog', '0002_post_add_slug'),
        # ...
        ('blog', '0020_post_add_views'),
    ]
    # ...
```

Une fois que tous les environnements ont appliqué le squash, on peut supprimer les anciennes migrations et retirer `replaces`.

---

## 7. Fake migrations

```python
# Marquer une migration comme appliquée sans l'exécuter
# Utile si le schéma existe déjà (ex: base de données importée)
python manage.py migrate --fake blog 0002

# Fake la migration initiale (la table existe déjà)
python manage.py migrate --fake-initial
```

**Cas d'usage typique :** Vous ajoutez Django à une application existante dont le schéma est déjà en place. Vous créez les migrations, puis vous les "fake" pour que Django sache que ces changements sont déjà appliqués.

---

## 8. Migrations dans les tests

Django propose des outils pour tester les migrations :

```python
# Dans les tests : désactiver les migrations (plus rapide, mais teste moins)
# settings_test.py
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()
```

Pour tester les migrations elles-mêmes :

```python
from django.test import TestCase
from django.db.migrations.executor import MigrationExecutor
from django.db import connection


class TestMigration(TestCase):
    @property
    def app(self):
        return 'blog'

    def test_migration_0004(self):
        executor = MigrationExecutor(connection)
        app_before = [('blog', '0003_post_add_slug_field')]
        app_after = [('blog', '0004_populate_slug')]

        # Revenir avant la migration
        executor.migrate(app_before)

        # Créer des données de test
        old_state = executor.loader.project_state(app_before)
        Post = old_state.apps.get_model('blog', 'Post')
        Post.objects.create(title='Test Post', slug='')

        # Appliquer la migration
        executor.loader.build_graph()
        executor.migrate(app_after)

        # Vérifier le résultat
        new_state = executor.loader.project_state(app_after)
        Post = new_state.apps.get_model('blog', 'Post')
        post = Post.objects.get(title='Test Post')
        self.assertEqual(post.slug, 'test-post')
```

---

## 9. Problèmes courants et solutions

### Ajouter un champ NOT NULL sans valeur par défaut

```
django.db.utils.IntegrityError: NOT NULL constraint failed
```

**Solution :** Fournir un `default` dans le modèle (temporaire ou permanent) :
```python
# Dans le modèle
views = models.PositiveIntegerField(default=0)

# Ou lors de makemigrations, Django vous demande de choisir :
# 1) Provide a one-off default now
# 2) Quit and define a default in the model
```

### Conflits de migrations

Quand deux développeurs créent des migrations depuis la même base :
```
CommandError: Conflicting migrations detected
```

**Solution :**
```bash
python manage.py makemigrations --merge blog
# Django crée une migration de merge
```

### Dépendances circulaires

```
django.db.migrations.exceptions.CircularDependencyError
```

**Solution :** Déplacer la relation dans une migration séparée ou utiliser des `ForeignKey` avec `to` en string pour des relations inter-app.

---

## Résumé

| Opération                    | Commande / Outil                          |
|------------------------------|-------------------------------------------|
| Détecter les changements     | `makemigrations`                          |
| Appliquer les migrations     | `migrate`                                 |
| Voir le SQL généré           | `sqlmigrate <app> <num>`                  |
| Lister l'état                | `showmigrations`                          |
| Rollback                     | `migrate <app> <num>`                     |
| Fusionner des migrations     | `squashmigrations <app> <from> <to>`      |
| Marquer sans exécuter        | `migrate --fake <app> <num>`              |
| Données dans une migration   | `RunPython(forward, backward)`            |
| SQL brut dans une migration  | `RunSQL(sql, reverse_sql)`                |
