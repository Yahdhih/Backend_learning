# Jour 56 — Optimisation SQL
📅 21 août 2026 · Module : Cache & Performance

---

## Lire un plan EXPLAIN

`EXPLAIN` montre comment la DB va exécuter ta requête **sans** l'exécuter.
`EXPLAIN ANALYZE` l'exécute et montre les temps réels.

### SQLite (EXPLAIN QUERY PLAN)

```sql
EXPLAIN QUERY PLAN
SELECT * FROM articles WHERE statut = 'publie';
```

```
QUERY PLAN
└─ SCAN TABLE articles   ← scan complet = lent !
```

Avec un index :
```
└─ SEARCH TABLE articles USING INDEX idx_statut (statut=?)  ← rapide !
```

### PostgreSQL (EXPLAIN ANALYZE)

```sql
EXPLAIN ANALYZE SELECT * FROM articles WHERE statut = 'publie';
```

```
Seq Scan on articles  (cost=0.00..123.50 rows=1500 width=200) (actual time=0.05..5.23 rows=1489 loops=1)
  Filter: (statut = 'publie')
  Rows Removed by Filter: 511
Planning Time: 0.3 ms
Execution Time: 5.8 ms
```

- **Seq Scan** = scan complet (mauvais sur grande table)
- **Index Scan** = utilise un index (bon)
- **cost** = estimation du coût (relatif)
- **actual time** = temps réel en ms
- **rows** = nombre de lignes

---

## Les indexes

Un index est une structure de données qui accélère la recherche, au prix d'espace disque et de temps d'écriture.

### Quand ajouter un index ?

```
Colonne filtrée fréquemment :
    WHERE statut = 'publie'     → index sur statut

Colonne utilisée en JOIN :
    ON a.auteur_id = u.id       → index sur auteur_id (souvent auto via ForeignKey)

Colonne utilisée en ORDER BY :
    ORDER BY date_creation DESC → index sur date_creation

Recherche de texte :
    WHERE titre LIKE 'Python%'  → index sur titre (ILIKE = GIN index sur PostgreSQL)
```

### En Django

```python
class Article(models.Model):
    statut = models.CharField(max_length=20, db_index=True)   # index simple

    class Meta:
        indexes = [
            models.Index(fields=["statut"]),               # même chose
            models.Index(fields=["-date_creation"]),        # index pour tri
            models.Index(fields=["statut", "auteur"]),      # index composite
            models.Index(                                   # index partiel (PostgreSQL)
                fields=["statut"],
                condition=models.Q(statut="publie"),
                name="idx_articles_publies"
            ),
        ]
```

### Index composite : l'ordre compte !

```python
# Pour cette requête :
Article.objects.filter(statut="publie", auteur=user).order_by("-date_creation")

# Index optimal : (statut, auteur, date_creation)
models.Index(fields=["statut", "auteur", "-date_creation"])

# Pas : (date_creation, statut, auteur) — le premier champ est utilisé en premier
```

---

## Requêtes lentes courantes

### SELECT * — charger trop de colonnes

```python
# Mauvais : charge tous les champs (contenu = gros TextField)
articles = Article.objects.filter(statut="publie")
for a in articles:
    print(a.titre)

# Bon : seulement ce dont on a besoin
articles = Article.objects.filter(statut="publie").values("id", "titre")
# ou
articles = Article.objects.filter(statut="publie").only("id", "titre")
```

### Compter sans COUNT

```python
# Mauvais : charge tous les objets pour les compter
nb = len(Article.objects.filter(statut="publie"))  # charge N articles !

# Bon : un COUNT(*) SQL
nb = Article.objects.filter(statut="publie").count()
```

### exists() vs count()

```python
# Pour vérifier l'existence, exists() est plus rapide que count()
if Article.objects.filter(auteur=user).count() > 0:   # COUNT(*)
    ...

if Article.objects.filter(auteur=user).exists():   # SELECT 1 LIMIT 1 — plus rapide
    ...
```

---

## iterator() pour les grands volumes

```python
# Mauvais : charge 100 000 articles en RAM
for article in Article.objects.all():
    traiter(article)

# Bon : traite par chunks de 500 (jamais tout en mémoire)
for article in Article.objects.iterator(chunk_size=500):
    traiter(article)
```

---

## Connection pooling (production)

Django ouvre/ferme des connexions DB à chaque requête. En prod, utilise **pgBouncer** ou `CONN_MAX_AGE` :

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "CONN_MAX_AGE": 60,    # réutilise la connexion pendant 60s
    }
}
```
