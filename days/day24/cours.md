# Jour 24 — Django ORM Avancé : annotate, aggregate, Q et F (20 juillet 2026)

---

## Introduction

Les QuerySets de base (filter, exclude, get) couvrent les besoins courants. Mais une application réelle doit souvent **calculer** des données plutôt que simplement les lire : compter les commandes, calculer des totaux, comparer des champs entre eux. C'est le rôle d'`aggregate`, `annotate`, `Q` et `F`.

---

## Modèles de référence

```python
class User(models.Model):
    name       = models.CharField(max_length=100)
    email      = models.EmailField()
    is_active  = models.BooleanField(default=True)

class Product(models.Model):
    name        = models.CharField(max_length=200)
    category    = models.CharField(max_length=100)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    stock_count = models.IntegerField(default=0)
    min_stock   = models.IntegerField(default=5)

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
```

---

## 1. aggregate() — Calculer sur tout le QuerySet

`aggregate()` effectue un calcul sur **l'ensemble du QuerySet** et retourne un dictionnaire Python (pas un QuerySet). C'est le terminal de la chaîne — vous ne pouvez pas continuer à chaîner après.

```python
from django.db.models import Count, Sum, Avg, Min, Max

# Statistiques globales
stats = Order.objects.aggregate(
    total_commandes = Count("id"),
    ca_total        = Sum("total_price"),
    panier_moyen    = Avg("total_price"),
    plus_petite     = Min("total_price"),
    plus_grande     = Max("total_price"),
)
# Retourne un dict :
# {
#   "total_commandes": 10,
#   "ca_total": Decimal("2533.85"),
#   "panier_moyen": Decimal("253.38"),
#   "plus_petite": Decimal("29.99"),
#   "plus_grande": Decimal("1299.99")
# }
# SQL : SELECT COUNT(id), SUM(total_price), AVG(total_price),
#              MIN(total_price), MAX(total_price)
#        FROM orders;

# Avec filtre préalable
stats_juillet = Order.objects.filter(
    ordered_at__month=7,
    status="completed"
).aggregate(
    ca = Sum("total_price"),
    nb = Count("id")
)
```

### Fonctions d'agrégation disponibles

| Fonction         | SQL          | Description                          |
|------------------|--------------|--------------------------------------|
| `Count("field")` | COUNT(field) | Nombre de valeurs non-NULL           |
| `Count("*")`     | COUNT(*)     | Nombre de lignes total               |
| `Sum("field")`   | SUM(field)   | Somme                                |
| `Avg("field")`   | AVG(field)   | Moyenne                              |
| `Min("field")`   | MIN(field)   | Valeur minimale                      |
| `Max("field")`   | MAX(field)   | Valeur maximale                      |
| `StdDev`         | STDDEV       | Écart-type (PostgreSQL)              |
| `Variance`       | VARIANCE     | Variance (PostgreSQL)                |

### Count avec distinct

```python
# Nombre d'utilisateurs distincts ayant commandé
nb_clients = Order.objects.filter(status="completed").aggregate(
    nb_clients=Count("user", distinct=True)
)
# SQL : SELECT COUNT(DISTINCT user_id) FROM orders WHERE status='completed'
```

---

## 2. annotate() — Ajouter un champ calculé à chaque objet

`annotate()` ajoute un **champ calculé à chaque ligne** du QuerySet. C'est comme ajouter une colonne temporaire. Contrairement à `aggregate()`, il retourne un QuerySet avec lequel on peut continuer à travailler.

```python
from django.db.models import Count, Sum, Avg

# Nombre de commandes par utilisateur
users = User.objects.annotate(
    nb_commandes=Count("orders")
)
# SQL :
# SELECT users.*, COUNT(orders.id) AS nb_commandes
# FROM users
# LEFT OUTER JOIN orders ON orders.user_id = users.id
# GROUP BY users.id

for user in users:
    print(f"{user.name} : {user.nb_commandes} commandes")
    # nb_commandes est accessible comme un attribut normal

# Filtrer sur le champ annoté
clients_reguliers = User.objects.annotate(
    nb_commandes=Count("orders")
).filter(nb_commandes__gt=2)

# Trier par le champ annoté
top_clients = User.objects.annotate(
    total_depense=Sum("orders__total_price")
).order_by("-total_depense")[:5]
```

### annotate() vs aggregate()

| | annotate() | aggregate() |
|--|------------|-------------|
| Retourne | QuerySet (plusieurs objets) | Dict (une seule valeur) |
| Niveau | Par objet (par ligne) | Sur tout le QuerySet |
| SQL | SELECT ... GROUP BY | SELECT COUNT(*), SUM(...) |
| Enchaînable | Oui | Non (fin de chaîne) |

```python
# annotate() : chaque User a son nb_commandes
users_avec_stats = User.objects.annotate(nb_commandes=Count("orders"))
for u in users_avec_stats:
    print(u.nb_commandes)  # accès comme un attribut ordinaire

# aggregate() : une seule valeur globale
stats_globales = Order.objects.aggregate(total=Sum("total_price"))
print(stats_globales["total"])  # accès comme dict
print(stats_globales["total_price"])  # KeyError !
```

### Annotations complexes avec plusieurs champs

```python
from django.db.models import Count, Sum, Avg

# Annoter plusieurs champs à la fois
users = User.objects.annotate(
    nb_commandes    = Count("orders"),
    total_depense   = Sum("orders__total_price"),
    depense_moyenne = Avg("orders__total_price"),
).filter(
    nb_commandes__gt=0
).order_by("-total_depense")

# Traverser plusieurs niveaux de relation
# Produits avec le nombre de commandes ET la recette totale
products = Product.objects.annotate(
    nb_ventes = Count("orders"),
    recette   = Sum("orders__total_price"),
).filter(nb_ventes__gt=0).order_by("-recette")
```

---

## 3. Q objects — Requêtes OR, AND, NOT complexes

Par défaut, les arguments d'un `filter()` sont combinés avec AND. Les **Q objects** permettent des combinaisons OR, AND, NOT arbitraires.

```python
from django.db.models import Q

# OR : produits Electronics OU moins de 50€
products = Product.objects.filter(
    Q(category="Electronics") | Q(price__lt=50)
)
# SQL : WHERE (category = 'Electronics' OR price < 50)

# AND explicite (équivalent au filter() avec plusieurs args)
products = Product.objects.filter(
    Q(category="Electronics") & Q(price__lt=100)
)
# SQL : WHERE (category = 'Electronics' AND price < 100)

# NOT : opérateur ~ (tilde)
users = User.objects.filter(
    ~Q(is_active=False)
)
# SQL : WHERE NOT (is_active = False)
# Équivalent à : User.objects.exclude(is_active=False)
```

### Combinaisons complexes

```python
# Utilisateurs actifs dont le nom commence par A OU B
users = User.objects.filter(
    is_active=True
).filter(
    Q(name__startswith="A") | Q(name__startswith="B")
)
# SQL : WHERE is_active = True AND (name LIKE 'A%' OR name LIKE 'B%')

# Commandes complètes OU expédiées récentes
from django.utils import timezone
from datetime import timedelta

hier = timezone.now() - timedelta(days=1)
orders = Order.objects.filter(
    Q(status="completed") |
    (Q(status="shipped") & Q(ordered_at__gte=hier))
)
# SQL : WHERE (status='completed' OR (status='shipped' AND ordered_at >= ...))

# Moteur de recherche multi-champs
def rechercher_produits(terme: str):
    return Product.objects.filter(
        Q(name__icontains=terme) |
        Q(category__icontains=terme)
    ).distinct()
```

### Construire des Q dynamiquement

```python
from django.db.models import Q

def filtrer_commandes(statuts=None, min_prix=None, utilisateur_id=None):
    """Construit un filtre dynamique selon les paramètres fournis."""
    condition = Q()  # Q() vide = toujours True (neutre pour &)

    if statuts:
        condition &= Q(status__in=statuts)

    if min_prix is not None:
        condition &= Q(total_price__gte=min_prix)

    if utilisateur_id is not None:
        condition &= Q(user_id=utilisateur_id)

    return Order.objects.filter(condition)

# Usage
orders = filtrer_commandes(statuts=["completed", "shipped"], min_prix=100)
```

---

## 4. F objects — Références aux champs en base de données

Un **F object** fait référence à la valeur d'un champ dans la base de données, **sans charger les données en Python**. Cela permet des comparaisons champ-à-champ et des mises à jour atomiques en une seule requête SQL.

```python
from django.db.models import F

# MAUVAIS : charge tous les produits en Python (N SELECT + N UPDATE)
for product in Product.objects.all():
    product.price = product.price * 1.10
    product.save()

# BON : une seule requête SQL, atomique
Product.objects.update(price=F("price") * 1.10)
# SQL : UPDATE products SET price = price * 1.10

# Décrémenter le stock (atomique, sans race condition)
Product.objects.filter(id=1).update(
    stock_count=F("stock_count") - 1
)
# SQL : UPDATE products SET stock_count = stock_count - 1 WHERE id = 1
```

### F pour comparer des champs entre eux

```python
# Produits dont le stock actuel est inférieur au stock minimum
produits_en_rupture = Product.objects.filter(
    stock_count__lt=F("min_stock")
)
# SQL : WHERE stock_count < min_stock
# Impossible à faire sans F : impossible de comparer deux colonnes autrement

# Produits dont le prix a augmenté (si on avait un champ prix_original)
# produits_plus_chers = Product.objects.filter(price__gt=F("prix_original"))
```

### F dans les annotations avec ExpressionWrapper

```python
from django.db.models import ExpressionWrapper, DecimalField, F

# Valeur du stock = prix * quantité en stock
products = Product.objects.annotate(
    valeur_stock=ExpressionWrapper(
        F("price") * F("stock_count"),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )
).order_by("-valeur_stock")
# SQL : SELECT *, price * stock_count AS valeur_stock FROM products
#        ORDER BY valeur_stock DESC

for p in products:
    print(f"{p.name}: valeur stock = {p.valeur_stock:.2f}€")
```

---

## 5. Case/When — Expressions conditionnelles (CASE WHEN)

```python
from django.db.models import Case, When, Value, CharField, IntegerField

# Ajouter un label de catégorie de prix à chaque produit
products = Product.objects.annotate(
    tranche_prix=Case(
        When(price__lt=50,   then=Value("Économique")),
        When(price__lt=200,  then=Value("Moyen de gamme")),
        When(price__lt=500,  then=Value("Haut de gamme")),
        default=Value("Premium"),
        output_field=CharField()
    )
)

for p in products:
    print(f"{p.name} ({p.price}€) : {p.tranche_prix}")
```

### Pivot avec Case/When dans aggregate()

```python
# Compter les commandes par statut sans GROUP BY — en une seule requête
stats = Order.objects.aggregate(
    nb_total     = Count("id"),
    nb_pending   = Count(Case(When(status="pending",   then=1), output_field=IntegerField())),
    nb_completed = Count(Case(When(status="completed", then=1), output_field=IntegerField())),
    nb_shipped   = Count(Case(When(status="shipped",   then=1), output_field=IntegerField())),
    nb_cancelled = Count(Case(When(status="cancelled", then=1), output_field=IntegerField())),
)
# SQL :
# SELECT
#   COUNT(id),
#   COUNT(CASE WHEN status='pending'   THEN 1 END),
#   COUNT(CASE WHEN status='completed' THEN 1 END),
#   ...
# FROM orders
```

---

## 6. Combiner Q, F, annotate() — Exemples complets

### Tableau de bord analytique

```python
from django.db.models import Count, Sum, Avg, Q, F, Case, When, IntegerField

def get_dashboard():
    # Statistiques globales en une requête
    global_stats = Order.objects.aggregate(
        total        = Count("id"),
        ca_total     = Sum("total_price"),
        avg_panier   = Avg("total_price"),
        nb_completed = Count(Case(
            When(status="completed", then=1),
            output_field=IntegerField()
        )),
        nb_cancelled = Count(Case(
            When(status="cancelled", then=1),
            output_field=IntegerField()
        )),
    )

    # Top 5 clients (avec annotation + filtre)
    top_clients = User.objects.annotate(
        nb_commandes  = Count("orders"),
        total_depense = Sum("orders__total_price"),
    ).filter(
        nb_commandes__gt=0
    ).order_by("-total_depense")[:5]

    # Produits en rupture de stock
    ruptures = Product.objects.filter(
        stock_count__lte=F("min_stock")
    ).annotate(
        nb_ventes=Count("orders")
    ).order_by("-nb_ventes")

    # Clients "VIP" : plus de 2 commandes ET dépense > 500€
    vip = User.objects.annotate(
        nb_commandes  = Count("orders"),
        total_depense = Sum("orders__total_price"),
    ).filter(
        Q(nb_commandes__gt=2) & Q(total_depense__gt=500)
    )

    return {
        "stats": global_stats,
        "top_clients": top_clients,
        "ruptures": ruptures,
        "vip": vip,
    }
```

### Recherche multicritères avec Q dynamique

```python
def recherche_avancee(terme=None, categorie=None, prix_min=None, prix_max=None, en_stock=True):
    qs = Product.objects.all()

    if terme:
        qs = qs.filter(
            Q(name__icontains=terme) | Q(category__icontains=terme)
        )

    if categorie:
        qs = qs.filter(category=categorie)

    if prix_min is not None:
        qs = qs.filter(price__gte=prix_min)

    if prix_max is not None:
        qs = qs.filter(price__lte=prix_max)

    if en_stock:
        qs = qs.filter(stock_count__gt=0)

    return qs.order_by("price")
```

---

## Résumé comparatif

| Outil         | Quand l'utiliser                                            | Retourne     |
|---------------|-------------------------------------------------------------|--------------|
| `aggregate()` | Un calcul global sur tout le QuerySet                       | dict         |
| `annotate()`  | Ajouter un champ calculé à chaque objet                     | QuerySet     |
| `Q object`    | Conditions OR, NOT, combinaisons complexes                  | (modificateur) |
| `F object`    | Comparer/modifier des champs sans charger en Python         | (modificateur) |
| `Case/When`   | Expressions conditionnelles (CASE WHEN en SQL)              | (expression) |

La combinaison de ces outils vous permet de faire en **une seule requête SQL** ce qui nécessiterait sinon plusieurs requêtes et du traitement Python — c'est crucial pour la performance à l'échelle.
