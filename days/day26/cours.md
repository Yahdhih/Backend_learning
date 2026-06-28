# Jour 26 — Le problème N+1 (22 juillet 2026)

---

## Introduction

Le problème N+1 est le bug de performance le plus courant dans les applications utilisant un ORM. Il est insidieux car le code fonctionne correctement — il est juste catastrophiquement lent à grande échelle. Ce cours explique ce qu'est le problème, comment le détecter, et comment le corriger avec `select_related()` et `prefetch_related()`.

---

## 1. Qu'est-ce que le problème N+1 ?

### Un exemple concret

Imaginez qu'on veut afficher 100 posts avec le nom de leur auteur :

```python
posts = Post.objects.all()[:100]

for post in posts:
    print(f"{post.title} — par {post.author.username}")
```

Ce code paraît innocent. Voici ce qui se passe réellement :

1. **Requête 1 :** `SELECT * FROM blog_post LIMIT 100`
2. **Requête 2 :** `SELECT * FROM auth_user WHERE id = 1` (auteur du post 1)
3. **Requête 3 :** `SELECT * FROM auth_user WHERE id = 2` (auteur du post 2)
4. ...
5. **Requête 101 :** `SELECT * FROM auth_user WHERE id = N` (auteur du post 100)

**Total : 101 requêtes** pour afficher 100 posts. Avec 1000 posts, c'est 1001 requêtes. Avec 10 000 posts, 10 001 requêtes.

C'est le problème **N+1** : 1 requête initiale + N requêtes pour chaque relation accédée.

### Pourquoi l'ORM fait ça ?

Django est **lazy** par défaut. Quand vous accédez à `post.author`, Django ne sait pas encore si vous allez utiliser l'auteur ou non. Il fait donc la requête uniquement quand vous y accédez — ce qui est le bon comportement pour un objet isolé, mais catastrophique dans une boucle.

---

## 2. Comment détecter le problème N+1

### Méthode 1 : django-debug-toolbar

En développement, installez `django-debug-toolbar`. Il affiche un panneau avec toutes les requêtes SQL exécutées pour chaque page — idéal pour visualiser rapidement les problèmes N+1.

```python
# Installation
pip install django-debug-toolbar

# settings.py
INSTALLED_APPS = [
    ...
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    ...
]
```

### Méthode 2 : django.db.connection.queries

Pour déboguer dans le code ou les tests :

```python
from django.db import connection, reset_queries
from django.conf import settings

# Activer le logging des requêtes (en DEBUG uniquement)
settings.DEBUG = True

reset_queries()  # Réinitialiser le compteur

# ... code à analyser ...

print(f"Nombre de requêtes : {len(connection.queries)}")
for q in connection.queries:
    print(f"  [{q['time']}s] {q['sql'][:120]}")
```

### Méthode 3 : assertNumQueries dans les tests

```python
from django.test import TestCase

class TestPerformance(TestCase):

    def test_liste_posts_sans_n_plus_1(self):
        # Créer 10 posts avec des auteurs différents
        # ...

        # Cette assertion ÉCHOUE si plus de 2 requêtes sont faites
        with self.assertNumQueries(2):
            posts = list(Post.objects.select_related('author').all())
            for post in posts:
                _ = post.author.username  # N'engendre PAS de requête supplémentaire
```

---

## 3. select_related() — pour les ForeignKey et OneToOne

`select_related()` résout le N+1 pour les relations **ForeignKey** et **OneToOne** en faisant un **JOIN SQL**.

```python
# SANS select_related : 1 + N requêtes
posts = Post.objects.all()

# AVEC select_related : 1 seule requête (JOIN)
posts = Post.objects.select_related('author')
```

SQL généré par `select_related('author')` :
```sql
SELECT blog_post.*, auth_user.*
FROM blog_post
INNER JOIN auth_user ON (blog_post.author_id = auth_user.id);
```

Django charge tous les auteurs dans la même requête et les met en cache. Quand on accède à `post.author`, aucune requête supplémentaire n'est faite.

### Traverser plusieurs niveaux

```python
# ForeignKey imbriquées : post → auteur → profil
posts = Post.objects.select_related('author', 'author__profile')

# Accès sans requête supplémentaire
for post in posts:
    print(post.author.profile.bio)  # 0 requête supplémentaire
```

### Limites de select_related()

`select_related()` ne fonctionne **pas** pour :
- Les relations ManyToMany
- Les relations inversées (reverse ForeignKey) — ex: accéder aux commentaires d'un post depuis le post

Pour ces cas, utilisez `prefetch_related()`.

---

## 4. prefetch_related() — pour les ManyToMany et relations inversées

`prefetch_related()` résout le N+1 pour les relations **ManyToMany** et les **reverse ForeignKey**. Au lieu d'un JOIN, il fait une **seconde requête avec IN** et assemble les résultats en Python.

```python
# Récupérer les posts avec leurs tags (ManyToMany)
posts = Post.objects.prefetch_related('tags')

for post in posts:
    tags = post.tags.all()  # Pas de requête : résultats en cache
    print([t.name for t in tags])
```

SQL généré : **deux requêtes**
```sql
-- Requête 1
SELECT * FROM blog_post;

-- Requête 2
SELECT blog_tag.*, blog_post_tags.post_id
FROM blog_tag
INNER JOIN blog_post_tags ON blog_tag.id = blog_post_tags.tag_id
WHERE blog_post_tags.post_id IN (1, 2, 3, ..., 100);
```

### Relations inversées (reverse ForeignKey)

```python
# Accéder aux commentaires de chaque post (reverse FK)
posts = Post.objects.prefetch_related('comment_set')

for post in posts:
    comments = post.comment_set.all()  # Pas de requête supplémentaire
    print(f"{post.title} : {len(comments)} commentaires")
```

### related_name plus lisible

```python
# Dans le modèle
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')

# Dans la vue
posts = Post.objects.prefetch_related('comments')
for post in posts:
    for comment in post.comments.all():  # Pas de requête
        print(comment.body)
```

---

## 5. Prefetch() — contrôle avancé du prefetch

Pour un prefetch avec des filtres ou un queryset personnalisé, utilisez la classe `Prefetch` :

```python
from django.db.models import Prefetch

# Prefetcher seulement les commentaires approuvés
posts = Post.objects.prefetch_related(
    Prefetch(
        'comments',
        queryset=Comment.objects.filter(is_approved=True).select_related('author'),
        to_attr='approved_comments'  # stocké dans post.approved_comments
    )
)

for post in posts:
    # post.approved_comments est une liste (pas un QuerySet)
    print(f"{post.title} : {len(post.approved_comments)} commentaires approuvés")
```

---

## 6. Quand utiliser lequel ?

| Situation                          | Solution              | SQL généré         |
|------------------------------------|----------------------|---------------------|
| ForeignKey simple                  | `select_related`     | JOIN                |
| OneToOneField                      | `select_related`     | JOIN                |
| ForeignKey imbriqué (A→B→C)        | `select_related('b', 'b__c')` | JOIN multiple |
| ManyToManyField                    | `prefetch_related`   | 2 requêtes + IN     |
| Reverse ForeignKey (`_set`)        | `prefetch_related`   | 2 requêtes + IN     |
| Prefetch avec filtre               | `Prefetch(queryset=...)` | 2 requêtes + IN |

### Règle simple

- **select_related** : "aller chercher" (ForeignKey, OneToOne) — un JOIN
- **prefetch_related** : "ramener" (ManyToMany, relations inverses) — une requête séparée

---

## 7. Attention : le prefetch peut être invalidé

```python
# Bon : on utilise le prefetch
posts = Post.objects.prefetch_related('comments')
for post in posts:
    comments = post.comments.all()  # utilise le cache

# Mauvais : le filtre supplémentaire invalide le prefetch !
posts = Post.objects.prefetch_related('comments')
for post in posts:
    # Nouveau QuerySet → nouvelle requête → N+1 !
    comments = post.comments.filter(is_approved=True)
```

La solution pour filtrer : utiliser `Prefetch()` avec un `queryset` personnalisé.

---

## 8. Benchmarks — l'impact réel

Avec 100 posts, 10 commentaires chacun, 5 tags chacun :

| Approche                            | Requêtes SQL | Temps (approximatif) |
|-------------------------------------|-------------|----------------------|
| Sans optimisation                   | 1 + 100 + 100 = 201 | ~500ms |
| `select_related('author')`          | 1           | ~5ms   |
| `prefetch_related('tags', 'comments')` | 3        | ~15ms  |
| Combiné                             | 3           | ~15ms  |

Les chiffres exacts varient selon la base de données et le matériel, mais l'ordre de grandeur est représentatif.

---

## Résumé

1. **N+1 = 1 requête initiale + N requêtes dans la boucle.** Le code fonctionne, mais lentement.
2. **Détecter** avec `connection.queries`, `django-debug-toolbar`, ou `assertNumQueries` dans les tests.
3. **select_related()** pour les ForeignKey et OneToOne → fait un JOIN SQL → 1 requête.
4. **prefetch_related()** pour les ManyToMany et relations inversées → fait 2 requêtes avec IN.
5. **Prefetch()** pour les prefetch avec filtres ou `to_attr` custom.
6. Attention aux filtres dans la boucle qui **invalident** le prefetch.
