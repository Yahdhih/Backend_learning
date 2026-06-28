# Jour 23 — Django ORM : QuerySets, filter, exclude, get (19 juillet 2026)

---

## Introduction : Pourquoi un ORM ?

Un ORM (Object-Relational Mapper) est une couche d'abstraction qui permet d'interagir avec une base de données en utilisant des objets Python plutôt que du SQL brut.

**Sans ORM :**
```python
import sqlite3
conn = sqlite3.connect("db.sqlite3")
cur = conn.cursor()
cur.execute("SELECT * FROM users WHERE is_active = 1 ORDER BY name")
users = cur.fetchall()  # liste de tuples, pas d'objets
```

**Avec Django ORM :**
```python
users = User.objects.filter(is_active=True).order_by("name")
# users est un QuerySet — des objets User avec attributs
for user in users:
    print(user.name, user.email)  # accès par attribut, pas par index
```

L'ORM offre :
- Sécurité : protection automatique contre les injections SQL
- Portabilité : le même code Python fonctionne avec PostgreSQL, MySQL, SQLite
- Productivité : moins de code, plus de lisibilité
- Intégration : les modèles Django gèrent aussi les migrations, la validation, etc.

---

## Les modèles de référence

Pour ce cours, nous utilisons ces modèles Django :

```python
# models.py
from django.db import models

class User(models.Model):
    name       = models.CharField(max_length=100)
    email      = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active  = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    name        = models.CharField(max_length=200)
    category    = models.CharField(max_length=100)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    stock_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending",   "En attente"),
        ("completed", "Complété"),
        ("shipped",   "Expédié"),
        ("cancelled", "Annulé"),
    ]

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    product     = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="orders")
    quantity    = models.IntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    ordered_at  = models.DateTimeField(auto_now_add=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    def __str__(self):
        return f"Order #{self.pk} — {self.user} — {self.status}"
```

---

## 1. Qu'est-ce qu'un QuerySet ?

Un **QuerySet** est un objet Python qui représente une collection de résultats de base de données. Il est **paresseux (lazy)** : la requête SQL n'est **pas exécutée** immédiatement.

```python
# Cette ligne ne touche PAS la base de données
qs = User.objects.filter(is_active=True)

# La requête SQL s'exécute ici, quand on itère
for user in qs:
    print(user.name)
```

### Quand est-ce que la requête s'exécute ?

La requête SQL est exécutée ("évaluée") dans ces situations :

```python
qs = User.objects.filter(is_active=True)

# 1. Itération
for user in qs: ...

# 2. Slicing avec step ou index précis
users = qs[0]      # devient LIMIT 1
users = qs[0:5]    # devient LIMIT 5 OFFSET 0

# 3. Conversion explicite
list(qs)           # force l'évaluation

# 4. Appels spéciaux
qs.count()         # SELECT COUNT(*) ...
qs.exists()        # SELECT (1) AS "a" WHERE ... LIMIT 1
qs.first()         # ... ORDER BY id LIMIT 1
qs.last()          # ... ORDER BY id DESC LIMIT 1

# 5. Affichage (repr())
print(qs)          # évalue et affiche
qs                 # dans le shell Django, évalue aussi
```

### QuerySets sont immuables et chaînables

Chaque méthode retourne un **nouveau** QuerySet sans modifier l'original :

```python
base_qs = User.objects.filter(is_active=True)
# base_qs n'est pas encore exécuté

alice_qs = base_qs.filter(name="Alice")  # nouveau QS, n'affecte pas base_qs
# base_qs est toujours "tous les actifs"
```

---

## 2. all(), filter(), exclude(), get()

### all() — Tous les objets

```python
# Sélectionne tous les utilisateurs
users = User.objects.all()
# SQL : SELECT * FROM users;

# "all" est souvent implicite, ces deux lignes sont équivalentes
users = User.objects.all()
users = User.objects     # le manager retourne déjà "all" par défaut
```

### filter() — Filtrer

```python
# Utilisateurs actifs
User.objects.filter(is_active=True)
# SQL : SELECT * FROM users WHERE is_active = True;

# Produits d'une catégorie
Product.objects.filter(category="Electronics")
# SQL : SELECT * FROM products WHERE category = 'Electronics';

# Plusieurs conditions = AND
Product.objects.filter(category="Electronics", price__lt=100)
# SQL : SELECT * FROM products WHERE category = 'Electronics' AND price < 100;
```

### exclude() — Exclure

```python
# Tous les utilisateurs sauf les inactifs
User.objects.exclude(is_active=False)
# SQL : SELECT * FROM users WHERE NOT (is_active = False);

# Tous les produits sauf la catégorie Furniture
Product.objects.exclude(category="Furniture")
# SQL : SELECT * FROM products WHERE NOT (category = 'Furniture');
```

### get() — Un seul objet

```python
# Retourne exactement un objet ou lève une exception
user = User.objects.get(id=1)
# SQL : SELECT * FROM users WHERE id = 1 LIMIT 2;

# Exceptions possibles :
# - User.DoesNotExist : aucune ligne trouvée
# - User.MultipleObjectsReturned : plus d'une ligne trouvée

try:
    user = User.objects.get(email="alice@example.com")
except User.DoesNotExist:
    print("Utilisateur introuvable")
except User.MultipleObjectsReturned:
    print("Plusieurs utilisateurs avec cet email !")
```

**get() ne doit être utilisé que pour les lookups garantis uniques** (par id, email unique, etc.)

---

## 3. Field lookups — Les opérateurs de filtre

Django utilise la syntaxe `champ__opérateur` (double underscore) pour les opérateurs de comparaison.

### Lookups numériques et de chaînes

```python
# __exact — égalité (défaut si aucun lookup)
User.objects.filter(name__exact="Alice")
User.objects.filter(name="Alice")  # idem
# SQL : WHERE name = 'Alice'

# __iexact — égalité insensible à la casse
User.objects.filter(name__iexact="alice")
# SQL : WHERE UPPER(name) = UPPER('alice')

# __gt, __gte, __lt, __lte — comparaisons
Product.objects.filter(price__gt=100)          # > 100
Product.objects.filter(price__gte=100)         # >= 100
Product.objects.filter(stock_count__lt=10)     # < 10
Product.objects.filter(stock_count__lte=0)     # <= 0
# SQL : WHERE price > 100, etc.

# __in — dans une liste
User.objects.filter(id__in=[1, 2, 3])
Product.objects.filter(category__in=["Electronics", "Books"])
# SQL : WHERE id IN (1, 2, 3)

# __range — intervalle (inclus des deux côtés)
Product.objects.filter(price__range=(50, 200))
# SQL : WHERE price BETWEEN 50 AND 200
```

### Lookups de chaînes (LIKE)

```python
# __contains — contient (sensible à la casse)
Product.objects.filter(name__contains="Pro")
# SQL : WHERE name LIKE '%Pro%'

# __icontains — contient (insensible à la casse)
Product.objects.filter(name__icontains="pro")
# SQL : WHERE UPPER(name) LIKE UPPER('%pro%')

# __startswith — commence par
Product.objects.filter(name__startswith="Laptop")
# SQL : WHERE name LIKE 'Laptop%'

# __istartswith — commence par (insensible à la casse)
Product.objects.filter(name__istartswith="laptop")

# __endswith — se termine par
User.objects.filter(email__endswith="@example.com")
# SQL : WHERE email LIKE '%@example.com'
```

### Lookups NULL

```python
# __isnull — valeur NULL
Product.objects.filter(category__isnull=True)   # IS NULL
Product.objects.filter(category__isnull=False)  # IS NOT NULL
# SQL : WHERE category IS NULL
```

### Lookups de dates et heures

```python
from django.utils import timezone

# __date — comparaison de date seule
Order.objects.filter(ordered_at__date=timezone.now().date())

# __year, __month, __day, __hour
Order.objects.filter(ordered_at__year=2026)
Order.objects.filter(ordered_at__month=7)

# __week_day (1=Dimanche, 2=Lundi, ..., 7=Samedi)
Order.objects.filter(ordered_at__week_day=2)  # Lundi
```

### Traverser les relations (double underscore)

```python
# Accéder aux champs d'un modèle lié via ForeignKey
# orders dont l'utilisateur s'appelle Alice
Order.objects.filter(user__name="Alice")
# SQL : JOIN users u ON orders.user_id = u.id WHERE u.name = 'Alice'

# Chaîner les relations
Order.objects.filter(user__email__icontains="@gmail.com")

# Multiples niveaux de relation
# (si Product avait une FK vers Category avec un champ 'name')
# Order.objects.filter(product__category__name="Electronics")
```

---

## 4. Chaîner les filtres

```python
# Chaque filter() retourne un nouveau QuerySet — on peut chaîner
qs = (
    User.objects
    .filter(is_active=True)
    .filter(name__startswith="A")
    .exclude(email__endswith="@spam.com")
)
# SQL : WHERE is_active = True AND name LIKE 'A%'
#        AND NOT (email LIKE '%@spam.com')

# Equivalents :
qs1 = User.objects.filter(is_active=True, name__startswith="A")
qs2 = User.objects.filter(is_active=True).filter(name__startswith="A")
# Ces deux lignes produisent la même requête SQL
```

**Différence entre plusieurs filter() et un seul filter() avec plusieurs arguments :**

```python
# Quand on traverse des relations, cela PEUT faire une différence
# filter() avec plusieurs args = une seule jointure
Order.objects.filter(user__is_active=True, user__name="Alice")
# SQL : JOIN users u WHERE u.is_active AND u.name = 'Alice'

# Deux filter() séparés = deux jointures distinctes (comportement différent)
Order.objects.filter(user__is_active=True).filter(user__name="Alice")
# SQL : JOIN users u1 WHERE u1.is_active JOIN users u2 WHERE u2.name='Alice'
```

Dans la pratique, pour les cas simples (pas de traversal de relation), les deux sont équivalents.

---

## 5. values() et values_list()

### values() — Retourne des dictionnaires

```python
# Au lieu d'objets User, retourne des dicts
users = User.objects.filter(is_active=True).values("name", "email")
# Résultat : [{"name": "Alice", "email": "alice@..."}, ...]
# SQL : SELECT name, email FROM users WHERE is_active = True

for u in users:
    print(u["name"])  # accès par clé, pas par attribut
```

### values_list() — Retourne des tuples

```python
# Retourne des tuples
noms = User.objects.values_list("name", "email")
# Résultat : [("Alice", "alice@..."), ("Bob", "bob@..."), ...]

# flat=True si une seule colonne — retourne une liste plate
emails = User.objects.values_list("email", flat=True)
# Résultat : ["alice@...", "bob@...", ...]
# SQL : SELECT email FROM users

# Utile pour l'interopérabilité
list(emails)  # ["alice@...", "bob@...", ...]
```

**Quand utiliser values() / values_list() :**
- Quand vous n'avez besoin que de quelques colonnes
- Quand vous exportez des données (JSON, CSV)
- Plus performant que de charger des objets complets

---

## 6. count(), exists(), first(), last()

```python
# count() — nombre de résultats
nb = User.objects.filter(is_active=True).count()
# SQL : SELECT COUNT(*) FROM users WHERE is_active = True
# Retourne un int, pas un QuerySet

# exists() — vérifie si au moins un résultat existe
a_des_commandes = Order.objects.filter(user_id=1).exists()
# SQL : SELECT (1) AS "a" WHERE user_id = 1 LIMIT 1
# Retourne True ou False — plus rapide que count() > 0

# first() — premier objet (ou None)
user = User.objects.order_by("created_at").first()
# SQL : SELECT * FROM users ORDER BY created_at ASC LIMIT 1
# Retourne None si aucun résultat (pas d'exception)

# last() — dernier objet
derniere_commande = Order.objects.order_by("ordered_at").last()
# SQL : SELECT * FROM orders ORDER BY ordered_at DESC LIMIT 1
```

---

## 7. order_by() et slicing

### order_by()

```python
# Ordre croissant (défaut)
Product.objects.order_by("price")
# SQL : ORDER BY price ASC

# Ordre décroissant (préfixe -)
Product.objects.order_by("-price")
# SQL : ORDER BY price DESC

# Plusieurs colonnes
Product.objects.order_by("category", "-price")
# SQL : ORDER BY category ASC, price DESC

# Ordre aléatoire (ATTENTION : très lent sur grandes tables)
User.objects.order_by("?")
# SQL : ORDER BY RANDOM()

# Supprimer l'ordre défini dans Meta.ordering
User.objects.order_by()  # pas de ORDER BY dans la requête
```

### Slicing

```python
# Correspondance directe avec LIMIT/OFFSET
# Premier utilisateur
user = User.objects.all()[0]
# SQL : SELECT * FROM users ORDER BY name LIMIT 1

# 5 premiers
users = User.objects.all()[:5]
# SQL : SELECT * FROM users LIMIT 5

# Avec offset
users = User.objects.all()[10:20]
# SQL : SELECT * FROM users LIMIT 10 OFFSET 10

# ATTENTION : les index négatifs ne sont pas supportés
# User.objects.all()[-1]  # ERREUR
# Utilisez .last() à la place
```

---

## 8. Tableau récapitulatif SQL ↔ ORM

| SQL                                      | Django ORM                                      |
|------------------------------------------|-------------------------------------------------|
| `SELECT * FROM users`                    | `User.objects.all()`                            |
| `WHERE name = 'Alice'`                   | `.filter(name="Alice")`                         |
| `WHERE name != 'Alice'`                  | `.exclude(name="Alice")`                        |
| `WHERE price > 100`                      | `.filter(price__gt=100)`                        |
| `WHERE name LIKE '%Pro%'`                | `.filter(name__icontains="pro")`                |
| `WHERE id IN (1, 2, 3)`                  | `.filter(id__in=[1, 2, 3])`                     |
| `WHERE price BETWEEN 50 AND 200`         | `.filter(price__range=(50, 200))`               |
| `WHERE category IS NULL`                 | `.filter(category__isnull=True)`                |
| `ORDER BY price DESC`                    | `.order_by("-price")`                           |
| `LIMIT 5`                                | `[:5]`                                          |
| `LIMIT 5 OFFSET 10`                      | `[10:15]`                                       |
| `SELECT COUNT(*)`                        | `.count()`                                      |
| `SELECT name, email`                     | `.values("name", "email")`                      |
| `SELECT name FROM users LIMIT 1`         | `.values_list("name", flat=True)[:1]`           |

---

## 9. Voir le SQL généré

Pour voir exactement quelle requête SQL est générée :

```python
# Dans le shell Django
qs = User.objects.filter(is_active=True).order_by("name")
print(qs.query)
# -> SELECT "users_user"."id", "users_user"."name", ...
#    FROM "users_user"
#    WHERE "users_user"."is_active" = True
#    ORDER BY "users_user"."name" ASC

# Voir toutes les requêtes exécutées
from django.db import connection
print(connection.queries)  # liste de dicts {"sql": ..., "time": ...}

# Attention : DEBUG = True doit être activé pour connection.queries
```

---

## Bonnes pratiques

1. **Utilisez `exists()` plutôt que `count() > 0`** — bien plus rapide
2. **Utilisez `get()` uniquement pour les lookups garantis uniques** (pk, email unique)
3. **Préférez `filter().first()` à `get()`** quand vous n'êtes pas sûr du nombre de résultats
4. **Utilisez `values()` ou `values_list()`** quand vous n'avez besoin que de quelques champs
5. **Ne chargez pas tous les objets en mémoire** si vous n'en avez besoin que du compte

```python
# Mauvais : charge tous les objets en mémoire
if User.objects.filter(is_active=True).count() > 0:
    ...

# Bon : SQL minimal
if User.objects.filter(is_active=True).exists():
    ...
```
