# Exercice Jour 25 — Migrations Django en profondeur

## Mise en place

```bash
mkdir migration_lab && cd migration_lab
pip install django
django-admin startproject config .
python manage.py startapp blog
```

Ajoute `"blog"` dans `INSTALLED_APPS`.

---

## Étape 1 — Migration initiale

`blog/models.py` :
```python
from django.db import models

class Post(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    publie = models.BooleanField(default=False)

    def __str__(self):
        return self.titre
```

```bash
python manage.py makemigrations blog
python manage.py sqlmigrate blog 0001   # observe le SQL
python manage.py migrate
```

Crée quelques posts en shell :
```bash
python manage.py shell -c "
from blog.models import Post
Post.objects.create(titre='Premier article', contenu='Contenu du premier article')
Post.objects.create(titre='Deuxième article', contenu='Contenu du deuxième article', publie=True)
print(Post.objects.count(), 'posts créés')
"
```

---

## Étape 2 — Ajouter un champ NOT NULL

Ajoute `auteur = models.CharField(max_length=100)` à `Post`.

```bash
python manage.py makemigrations blog
```

Django te demande une valeur par défaut pour les lignes existantes. Entre `1` puis `"Anonyme"`.

```bash
python manage.py migrate
python manage.py sqlmigrate blog 0002
```

**Observation :** Quel SQL a été généré pour gérer les lignes existantes ?

---

## Étape 3 — Migration de données avec RunPython

Ajoute `slug = models.SlugField(unique=True, blank=True)` à `Post`.

```bash
python manage.py makemigrations blog --name="add_slug"
python manage.py makemigrations blog --empty --name="fill_slugs"
```

Modifie le fichier de migration vide `0004_fill_slugs.py` :

```python
from django.db import migrations
from django.utils.text import slugify

def remplir_slugs(apps, schema_editor):
    Post = apps.get_model("blog", "Post")
    for post in Post.objects.all():
        base_slug = slugify(post.titre)
        slug = base_slug
        compteur = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{compteur}"
            compteur += 1
        post.slug = slug
        post.save()

def vider_slugs(apps, schema_editor):
    Post = apps.get_model("blog", "Post")
    Post.objects.all().update(slug="")

class Migration(migrations.Migration):
    dependencies = [("blog", "0003_add_slug")]
    operations = [
        migrations.RunPython(remplir_slugs, reverse_code=vider_slugs),
    ]
```

```bash
python manage.py migrate
python manage.py shell -c "from blog.models import Post; print(list(Post.objects.values('titre', 'slug')))"
```

---

## Étape 4 — Voir les migrations appliquées

```bash
python manage.py showmigrations blog
```

---

## Étape 5 — Rollback

```bash
# Revenir à la migration 0002
python manage.py migrate blog 0002

# Vérifie que le champ slug n'existe plus
python manage.py shell -c "from blog.models import Post; p = Post.objects.first(); print(hasattr(p, 'slug'))"

# Réapplique
python manage.py migrate blog
```

---

## Étape 6 — Voir le SQL sans appliquer

```bash
python manage.py sqlmigrate blog 0001
python manage.py sqlmigrate blog 0003
```

---

## Questions dans `notes.md`

1. Pourquoi `apps.get_model()` et pas `from blog.models import Post` dans RunPython ?
2. Que se passe-t-il si deux développeurs créent une migration en même temps sur la même branche ?
3. Quelle est la différence entre une migration de schéma et une migration de données ?
4. Quand utiliserais-tu `RunSQL` plutôt que `RunPython` ?
