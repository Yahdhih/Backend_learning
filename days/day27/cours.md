# Jour 27 — Optimisation ORM et indexes (23 juillet 2026)

---

## Introduction

Après avoir réglé le problème N+1 (jour 26), ce cours s'attaque à l'optimisation fine des requêtes : indexes, `only()`, `defer()`, `iterator()`, et lecture des plans d'exécution. L'objectif est de passer d'une application qui "marche" à une application qui "marche vite, même avec des millions de lignes".

---

## 1. Les indexes en SQL

### Qu'est-ce qu'un index ?

Un index est une structure de données séparée qui maintient une copie ordonnée des valeurs d'une ou plusieurs colonnes. Sans index, chaque requête filtrée provoque un **parcours séquentiel (Sequential Scan)** : la base de données lit toutes les lignes de la table pour trouver celles qui correspondent.

Avec un index, la base de données utilise l'arbre B-tree pour trouver les lignes en **O(log n)** au lieu de O(n).

```
Table sans index (100 000 lignes) :
  WHERE email = 'alice@example.com'
  → Lire 100 000 lignes pour en trouver 1
  → ~100 000 comparaisons

Table avec index sur email :
  WHERE email = 'alice@example.com'
  → Naviguer dans l'arbre B-tree
  → ~17 comparaisons (log2(100 000))
```

### Types d'indexes

#### B-tree (le plus courant)

Le type par défaut dans Django et la plupart des bases de données. Supporté pour : `=`, `<`, `>`, `<=`, `>=`, `BETWEEN`, `LIKE 'prefix%'`, `IN`.

```python
# Dans un modèle Django
class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)  # UNIQUE crée automatiquement un index
    author = models.ForeignKey(User, db_index=True)  # db_index=True (défaut pour FK)
    created_at = models.DateTimeField(db_index=True)
    views = models.PositiveIntegerField(default=0)
```

#### Index UNIQUE

```python
# Colonne unique (contrainte + index)
email = models.EmailField(unique=True)

# Unicité composite dans Meta
class Meta:
    unique_together = [['author', 'slug']]
    # Ou avec UniqueConstraint (Django 2.2+) :
    constraints = [
        models.UniqueConstraint(fields=['author', 'slug'], name='unique_author_slug')
    ]
```

#### Index composite

```python
from django.db import models

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField()

    class Meta:
        indexes = [
            # Index composite : optimise les requêtes filtrées par author + status
            models.Index(fields=['author', 'status'], name='post_author_status_idx'),
            # Index pour ORDER BY created_at DESC
            models.Index(fields=['-created_at'], name='post_created_at_desc_idx'),
        ]
```

### Quand ajouter un index ?

**Ajoutez un index sur :**
- Les colonnes utilisées fréquemment dans `WHERE`
- Les colonnes utilisées dans `JOIN` (les ForeignKey en ont un automatiquement)
- Les colonnes utilisées dans `ORDER BY` sur de grandes tables
- Les colonnes avec une haute **cardinalité** (beaucoup de valeurs distinctes)

**Ne pas indexer :**
- Les petites tables (< quelques milliers de lignes — le scan est plus rapide)
- Les colonnes avec très peu de valeurs distinctes (`is_active` booléen — peu utile)
- Les colonnes rarement filtrées
- Les tables à fort taux d'écritures (chaque INSERT/UPDATE/DELETE doit mettre à jour tous les indexes)

### L'ordre des colonnes dans un index composite

```python
# Index sur (status, created_at)
models.Index(fields=['status', 'created_at'])
```

Cet index est **utilisé** pour :
- `WHERE status = 'published'`
- `WHERE status = 'published' AND created_at > '2026-01-01'`

Cet index **n'est pas utilisé** pour :
- `WHERE created_at > '2026-01-01'` (created_at n'est pas en premier)

Règle : un index composite `(A, B)` sert pour `A`, `A+B`, mais pas `B` seul.

---

## 2. EXPLAIN et EXPLAIN ANALYZE

### EXPLAIN dans SQLite

```python
import sqlite3

conn = sqlite3.connect(':memory:')
cur = conn.cursor()

# ... créer la table et insérer des données ...

# Voir le plan d'exécution
plan = cur.execute(
    "EXPLAIN QUERY PLAN SELECT * FROM blog_post WHERE author_id = 1"
).fetchall()
for row in plan:
    print(row)
```

Résultat **sans index** sur `author_id` :
```
(2, 0, 0, 'SCAN TABLE blog_post')
```
→ `SCAN TABLE` = lecture de toute la table.

Résultat **avec index** sur `author_id` :
```
(3, 0, 0, 'SEARCH TABLE blog_post USING INDEX blog_post_author_id (author_id=?)')
```
→ `SEARCH ... USING INDEX` = utilisation de l'index.

### EXPLAIN ANALYZE dans PostgreSQL

Pour PostgreSQL, `EXPLAIN ANALYZE` exécute réellement la requête et donne les temps réels :

```sql
EXPLAIN ANALYZE
SELECT p.title, u.username
FROM blog_post p
JOIN auth_user u ON p.author_id = u.id
WHERE p.status = 'published'
ORDER BY p.created_at DESC
LIMIT 20;
```

Exemple de sortie annotée :
```
Limit  (cost=65.00..65.05 rows=20 width=72) (actual time=0.312..0.318 rows=20 loops=1)
  ->  Sort  (cost=65.00..66.00 rows=400 width=72) (actual time=0.308..0.312 rows=20 loops=1)
        Sort Key: p.created_at DESC
        Sort Method: top-N heapsort  Memory: 27kB
        ->  Hash Join  (cost=15.00..50.00 rows=400 width=72) (actual time=0.086..0.251 rows=400 loops=1)
              Hash Cond: (p.author_id = u.id)
              ->  Seq Scan on blog_post p  (cost=0.00..28.00 rows=400 width=44) (actual time=0.012..0.089 rows=400 loops=1)
                    Filter: ((status)::text = 'published')
                    Rows Removed by Filter: 100
              ->  Hash  (cost=10.00..10.00 rows=400 width=36) (actual time=0.061..0.061 rows=50 loops=1)
                    ->  Seq Scan on auth_user u  (cost=...)
Planning Time: 0.456 ms
Execution Time: 0.412 ms
```

**Termes clés :**

| Terme                | Signification                                                |
|---------------------|--------------------------------------------------------------|
| `Seq Scan`          | Lecture séquentielle — chercher un index si sur grande table |
| `Index Scan`        | Utilisation d'un index (rapide pour peu de lignes)           |
| `Bitmap Index Scan` | Hybride pour de nombreuses lignes via index                  |
| `Hash Join`         | Join via table de hachage en mémoire (efficace)              |
| `Nested Loop`       | Join par boucle — efficace si la table interne est petite    |
| `cost=X..Y`         | Coût estimé : X pour le premier résultat, Y pour tout        |
| `actual time=A..B`  | Temps réel mesuré (seulement avec ANALYZE)                   |
| `rows=N`            | Nombre de lignes estimé / réel                               |
| `Rows Removed by Filter` | Combien de lignes ont été lues mais rejetées           |

**Signaux d'alarme dans un plan :**
- `Seq Scan` sur une table avec des millions de lignes
- Grand écart entre `rows=estimé` et `rows=réel` (statistiques périmées)
- `Sort` sur de grandes quantités de données (suggère un index sur la colonne de tri)

---

## 3. only() et defer() — limiter les colonnes chargées

Par défaut, `Post.objects.all()` fait `SELECT *` — toutes les colonnes sont chargées, même celles qu'on n'utilise pas.

### only() — ne charger que ces colonnes

```python
# Ne charger que id, title, slug — SELECT id, title, slug FROM blog_post
posts = Post.objects.only('id', 'title', 'slug')

for post in posts:
    print(post.title)  # OK — chargé
    print(post.slug)   # OK — chargé
    print(post.content)  # ATTENTION : déclenche une requête supplémentaire par post !
```

### defer() — charger tout sauf ces colonnes

```python
# Charger tout sauf le contenu long
posts = Post.objects.defer('content', 'raw_markdown')

# Équivalent à : SELECT id, title, slug, views, ... FROM blog_post
# (toutes les colonnes sauf content et raw_markdown)
```

### Quand utiliser only() / defer() ?

- `defer()` : colonnes volumineuses (TEXT long, JSONB, binaires) qu'on n'utilise pas dans la liste
- `only()` : quand on sait précisément qu'on n'a besoin que de 2-3 colonnes (ex: listes d'IDs, menus déroulants)

**Alternative plus sûre : `values()` ou `values_list()`**

```python
# values() : pas d'objet modèle, pas de risque d'accès inattendu
Post.objects.filter(is_active=True).values('id', 'title', 'slug')
# Retourne des dictionnaires — pas d'accès accidentel à un champ non chargé
```

---

## 4. iterator() — traiter de grands QuerySets sans exploser la mémoire

Par défaut, Django charge **tous les résultats d'un QuerySet en mémoire** au moment de l'évaluation. Pour 100 000 objets, cela peut consommer des gigaoctets de RAM.

### Le problème

```python
# DANGEREUX sur de grandes tables : charge TOUT en mémoire
posts = list(Post.objects.all())  # ex: 500 000 posts → peut crasher
for post in posts:
    traiter(post)
```

### La solution : iterator()

```python
# iterator() ne charge qu'un lot à la fois (chunk_size objets)
for post in Post.objects.all().iterator(chunk_size=2000):
    traiter(post)
```

`iterator()` utilise les curseurs de base de données pour récupérer les résultats par lots. La consommation mémoire reste constante, quelle que soit la taille du QuerySet.

**Important :** `iterator()` désactive le **cache du QuerySet**. On ne peut pas itérer deux fois sur le résultat.

### iterator() + only() — la combinaison optimale pour les grandes tables

```python
# Traiter 500 000 posts en ne chargeant que les colonnes nécessaires
for post in Post.objects.only('id', 'title', 'author_id').iterator(chunk_size=5000):
    # Traitement léger — pas de contenu chargé
    envoyer_notification(post.author_id, post.title)
```

---

## 5. Cas pratique — diagnostiquer et corriger une requête lente

### Étape 1 : identifier la requête lente

```python
# Dans un script de management ou les logs
import time
from django.db import connection, reset_queries
from django.conf import settings

settings.DEBUG = True
reset_queries()

t0 = time.time()
posts = list(Post.objects.filter(status='published').order_by('-created_at'))
t1 = time.time()

print(f"Temps : {(t1-t0)*1000:.1f}ms")
print(f"Requêtes : {len(connection.queries)}")
print(connection.queries[-1]['sql'])
```

### Étape 2 : voir le plan d'exécution

```python
import sqlite3

cur = conn.cursor()
plan = cur.execute(
    "EXPLAIN QUERY PLAN SELECT * FROM blog_post WHERE status = 'published' ORDER BY created_at DESC"
).fetchall()
for row in plan:
    print(row)
# → SCAN TABLE blog_post  (pas d'index sur status ou created_at)
```

### Étape 3 : ajouter les indexes

```python
# Dans le modèle
class Meta:
    indexes = [
        models.Index(fields=['status', '-created_at'], name='post_status_date_idx'),
    ]
```

```python
# Ou directement en SQL (pour tester sans migration)
cur.execute(
    "CREATE INDEX IF NOT EXISTS post_status_date_idx ON blog_post(status, created_at DESC)"
)
```

### Étape 4 : vérifier l'amélioration

```python
# Re-vérifier le plan
plan = cur.execute(
    "EXPLAIN QUERY PLAN SELECT * FROM blog_post WHERE status = 'published' ORDER BY created_at DESC"
).fetchall()
# → SEARCH TABLE blog_post USING INDEX post_status_date_idx (status=?)

# Comparer les temps
# Avant : 450ms sur 100 000 lignes
# Après : 3ms
```

---

## Résumé — Checklist d'optimisation

| Problème                              | Solution                                     |
|---------------------------------------|---------------------------------------------|
| Requête lente sur filtre              | Ajouter un index sur la colonne filtrée      |
| Requête lente sur ORDER BY            | Index sur la colonne de tri                  |
| Jointure lente                        | Index sur les colonnes de jointure (FK)      |
| SELECT * sur table large              | `only()` ou `defer()` pour les cols volumineuses |
| Itération sur des centaines de milliers d'objets | `iterator(chunk_size=N)`        |
| N+1 sur ForeignKey                    | `select_related()`                           |
| N+1 sur ManyToMany/reverse FK        | `prefetch_related()`                         |
| Doutes sur le plan d'exécution       | `EXPLAIN QUERY PLAN` (SQLite) ou `EXPLAIN ANALYZE` (PostgreSQL) |
| Statistiques périmées (PostgreSQL)   | `ANALYZE table_name`                         |
