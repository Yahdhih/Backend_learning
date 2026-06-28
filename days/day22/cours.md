# Jour 22 — SQL Avancé : Sous-requêtes, INDEX et EXPLAIN (18 juillet 2026)

---

## Introduction

Le SQL fondamental (SELECT, WHERE, JOIN, GROUP BY) couvre la majorité des besoins quotidiens. Mais les applications réelles demandent davantage : des requêtes imbriquées, de la logique analytique, et de la performance. Ce cours couvre les outils qui font la différence entre un développeur backend junior et un développeur solide.

---

## 1. Les sous-requêtes (Subqueries)

Une sous-requête est une requête SQL à l'intérieur d'une autre requête. Elle peut apparaître à trois endroits différents.

### 1.1 Sous-requête dans WHERE

La forme la plus courante : la sous-requête retourne une valeur ou une liste de valeurs pour filtrer la requête principale.

```sql
-- Trouver les utilisateurs qui ont passé au moins une commande
SELECT name, email
FROM users
WHERE id IN (
    SELECT DISTINCT user_id
    FROM orders
    WHERE status = 'completed'
);

-- Produits plus chers que la moyenne
SELECT name, price
FROM products
WHERE price > (
    SELECT AVG(price) FROM products
);

-- Utiliser EXISTS (plus performant que IN pour les grandes tables)
SELECT u.name
FROM users u
WHERE EXISTS (
    SELECT 1
    FROM orders o
    WHERE o.user_id = u.id
      AND o.total_price > 500
);
```

**EXISTS vs IN :**
- `IN` récupère toutes les valeurs puis filtre
- `EXISTS` s'arrête dès qu'il trouve une correspondance — généralement plus rapide

### 1.2 Sous-requête corrélée

Une sous-requête **corrélée** fait référence à la table externe. Elle est exécutée une fois **pour chaque ligne** de la requête externe.

```sql
-- Pour chaque utilisateur, trouver sa commande la plus récente
SELECT
    u.name,
    (SELECT MAX(ordered_at)
     FROM orders o
     WHERE o.user_id = u.id) AS derniere_commande
FROM users u;

-- Pour chaque produit, le nombre de commandes
SELECT
    p.name,
    p.price,
    (SELECT COUNT(*)
     FROM orders o
     WHERE o.product_id = p.id) AS nb_commandes
FROM products p
ORDER BY nb_commandes DESC;
```

**Attention :** Les sous-requêtes corrélées peuvent être lentes sur de grandes tables car elles s'exécutent N fois (une par ligne). Préférez souvent un JOIN avec GROUP BY.

```sql
-- Equivalence plus performante avec JOIN
SELECT
    p.name,
    p.price,
    COUNT(o.id) AS nb_commandes
FROM products p
LEFT JOIN orders o ON p.id = o.product_id
GROUP BY p.id, p.name, p.price
ORDER BY nb_commandes DESC;
```

### 1.3 Sous-requête dans FROM (tables dérivées)

```sql
-- Calculer la dépense totale par utilisateur, puis filtrer
SELECT nom, total
FROM (
    SELECT u.name AS nom, SUM(o.total_price) AS total
    FROM users u
    JOIN orders o ON u.id = o.user_id
    GROUP BY u.id, u.name
) AS depenses_par_user
WHERE total > 200
ORDER BY total DESC;
```

La sous-requête dans FROM crée une "table temporaire" appelée **table dérivée**. Elle doit toujours avoir un alias.

---

## 2. CTEs — Common Table Expressions (WITH)

Les CTEs (aussi appelées "clauses WITH") sont une façon plus lisible d'écrire des sous-requêtes dans FROM. Elles n'ont **pas d'impact sur les performances** par rapport aux tables dérivées — c'est surtout une question de lisibilité.

### CTE basique

```sql
WITH depenses_par_user AS (
    SELECT
        u.id,
        u.name,
        SUM(o.total_price) AS total
    FROM users u
    JOIN orders o ON u.id = o.user_id
    GROUP BY u.id, u.name
)
SELECT name, total
FROM depenses_par_user
WHERE total > 200
ORDER BY total DESC;
```

### CTEs multiples (chaînées)

```sql
WITH
-- Etape 1 : dépenses par utilisateur
depenses AS (
    SELECT
        u.id,
        u.name,
        u.email,
        COUNT(o.id)        AS nb_commandes,
        SUM(o.total_price) AS total_depense
    FROM users u
    JOIN orders o ON u.id = o.user_id
    WHERE o.status != 'cancelled'
    GROUP BY u.id, u.name, u.email
),
-- Etape 2 : calculer la moyenne globale
moyenne AS (
    SELECT AVG(total_depense) AS moy FROM depenses
),
-- Etape 3 : utilisateurs au-dessus de la moyenne
au_dessus AS (
    SELECT d.name, d.email, d.total_depense, m.moy
    FROM depenses d, moyenne m
    WHERE d.total_depense > m.moy
)
SELECT
    name,
    email,
    ROUND(total_depense, 2) AS depense,
    ROUND(moy, 2)           AS moyenne_globale
FROM au_dessus
ORDER BY total_depense DESC;
```

### CTE récursive

Les CTEs peuvent être récursives — utile pour les hiérarchies (catégories imbriquées, organigrammes).

```sql
-- Exemple : générer une séquence de nombres
WITH RECURSIVE compteur(n) AS (
    SELECT 1           -- cas de base
    UNION ALL
    SELECT n + 1       -- cas récursif
    FROM compteur
    WHERE n < 10
)
SELECT n FROM compteur;
-- Résultat : 1, 2, 3, ..., 10
```

---

## 3. Fonctions de fenêtrage (Window Functions)

Les fonctions de fenêtrage sont l'une des fonctionnalités les plus puissantes de SQL moderne. Elles permettent de faire des calculs sur un **ensemble de lignes liées** sans effondrer les résultats comme GROUP BY le ferait.

### La syntaxe OVER()

```sql
fonction() OVER (
    PARTITION BY colonne    -- grouper (optionnel)
    ORDER BY colonne        -- ordonner dans chaque groupe
    ROWS/RANGE ...          -- définir la fenêtre (optionnel)
)
```

### ROW_NUMBER — Numéroter les lignes

```sql
-- Numéroter les commandes de chaque utilisateur par date
SELECT
    user_id,
    id AS order_id,
    ordered_at,
    total_price,
    ROW_NUMBER() OVER (
        PARTITION BY user_id
        ORDER BY ordered_at
    ) AS numero_commande
FROM orders;
```

Résultat :
```
user_id | order_id | ordered_at          | total_price | numero_commande
--------|----------|---------------------|-------------|----------------
      1 |        1 | 2026-07-01 10:00:00 |     1299.99 |               1
      1 |        2 | 2026-07-03 11:00:00 |       99.98 |               2
      1 |        3 | 2026-07-10 09:00:00 |       39.99 |               3
      2 |        4 | 2026-07-02 14:00:00 |      129.99 |               1
      2 |        5 | 2026-07-05 16:00:00 |       89.98 |               2
```

### RANK et DENSE_RANK — Classement

```sql
SELECT
    name,
    price,
    RANK()       OVER (ORDER BY price DESC) AS rang,
    DENSE_RANK() OVER (ORDER BY price DESC) AS rang_dense
FROM products;
```

Différence entre RANK et DENSE_RANK :
- `RANK` : si deux éléments sont ex-aequo au rang 2, le suivant est rang 4
- `DENSE_RANK` : si deux éléments sont ex-aequo au rang 2, le suivant est rang 3

### LAG et LEAD — Accéder aux lignes adjacentes

```sql
-- Comparer chaque commande avec la précédente du même utilisateur
SELECT
    user_id,
    ordered_at,
    total_price,
    LAG(total_price) OVER (
        PARTITION BY user_id
        ORDER BY ordered_at
    ) AS commande_precedente,
    total_price - LAG(total_price) OVER (
        PARTITION BY user_id
        ORDER BY ordered_at
    ) AS difference
FROM orders;
```

```sql
-- LEAD : regarder la prochaine commande
SELECT
    user_id,
    ordered_at,
    total_price,
    LEAD(ordered_at) OVER (
        PARTITION BY user_id
        ORDER BY ordered_at
    ) AS prochaine_commande
FROM orders;
```

### Fonctions d'agrégation comme fenêtres

```sql
-- Somme cumulée des dépenses par utilisateur
SELECT
    user_id,
    ordered_at,
    total_price,
    SUM(total_price) OVER (
        PARTITION BY user_id
        ORDER BY ordered_at
        ROWS UNBOUNDED PRECEDING  -- toutes les lignes précédentes
    ) AS depense_cumulee
FROM orders;

-- Pourcentage de chaque commande dans le total utilisateur
SELECT
    user_id,
    total_price,
    SUM(total_price) OVER (PARTITION BY user_id) AS total_utilisateur,
    ROUND(
        100.0 * total_price / SUM(total_price) OVER (PARTITION BY user_id),
        1
    ) AS pourcentage
FROM orders;
```

---

## 4. Les INDEX

### Qu'est-ce qu'un index ?

Un index est une structure de données séparée qui accélère la recherche dans une table. C'est comme l'index d'un livre : au lieu de lire toutes les pages pour trouver un mot, vous consultez l'index qui vous dit directement à quelle page aller.

### Structure B-tree (le type d'index le plus courant)

```
               [50]
              /    \
        [20,30]    [70,80]
        /  |  \    /  |  \
      [10][25][35][60][75][90]
```

Un B-tree (arbre équilibré) maintient les données triées et permet :
- Recherche en O(log n) au lieu de O(n)
- Insertions et suppressions efficaces
- Parcours ordonné des données

Sur une table de 1 million de lignes :
- Sans index : ~1 000 000 comparaisons
- Avec index B-tree : ~20 comparaisons (log2(1 000 000) ≈ 20)

### Créer un index

```sql
-- Index simple sur une colonne
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Index unique (équivalent à UNIQUE constraint)
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- Index composite (sur plusieurs colonnes)
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- Supprimer un index
DROP INDEX IF EXISTS idx_orders_user_id;
```

### Quand ajouter un index ?

**OUI, ajoutez un index sur :**
- Les colonnes utilisées dans WHERE fréquemment
- Les colonnes utilisées dans JOIN (clés étrangères)
- Les colonnes utilisées dans ORDER BY sur de grandes tables
- Les colonnes avec beaucoup de valeurs distinctes (haute cardinalité)

**NON, n'ajoutez pas d'index sur :**
- Les petites tables (< quelques milliers de lignes)
- Les colonnes rarement utilisées en filtre
- Les colonnes avec très peu de valeurs distinctes (ex: is_active avec TRUE/FALSE)
- Les tables soumises à de nombreux INSERT/UPDATE (l'index ralentit les écritures)

### Index composites — l'ordre des colonnes compte

```sql
-- Index composite
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- Cette requête UTILISE l'index (user_id en premier)
SELECT * FROM orders WHERE user_id = 1 AND status = 'completed';

-- Cette requête UTILISE aussi l'index (user_id seul)
SELECT * FROM orders WHERE user_id = 1;

-- Cette requête N'UTILISE PAS l'index (status seul, pas en premier)
SELECT * FROM orders WHERE status = 'completed';
```

Règle : un index composite `(A, B)` peut être utilisé pour filtrer sur `A` seul ou `A + B`, mais **pas** sur `B` seul.

---

## 5. EXPLAIN — Comprendre le plan d'exécution

`EXPLAIN` montre comment la base de données va exécuter une requête, **sans l'exécuter réellement**.

### EXPLAIN dans SQLite

```sql
EXPLAIN QUERY PLAN
SELECT * FROM orders WHERE user_id = 1;
```

Résultat sans index :
```
QUERY PLAN
`--SCAN TABLE orders
```
"SCAN TABLE" = lecture séquentielle de toute la table (lent sur grandes tables)

Résultat avec index sur user_id :
```
QUERY PLAN
`--SEARCH TABLE orders USING INDEX idx_orders_user_id (user_id=?)
```
"SEARCH ... USING INDEX" = utilisation de l'index (rapide)

### EXPLAIN ANALYZE dans PostgreSQL

PostgreSQL offre plus de détails :

```sql
EXPLAIN ANALYZE
SELECT u.name, COUNT(o.id) AS nb_commandes
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name;
```

Résultat typique :
```
GroupAggregate  (cost=35.75..37.75 rows=100 width=40)
               (actual time=0.123..0.145 rows=5 loops=1)
  Group Key: u.id
  ->  Sort  (cost=35.75..36.00 rows=100 width=40)
            (actual time=0.115..0.118 rows=10 loops=1)
        Sort Key: u.id
        Sort Method: quicksort  Memory: 25kB
        ->  Hash Left Join  (cost=...)
            Hash Cond: (o.user_id = u.id)
            ->  Seq Scan on orders o  (...)
            ->  Hash  (...)
                ->  Seq Scan on users u  (...)
Planning Time: 0.234 ms
Execution Time: 0.312 ms
```

**Termes clés à connaître :**

| Terme            | Signification                                      |
|------------------|----------------------------------------------------|
| `Seq Scan`       | Lecture séquentielle (toute la table, lent)        |
| `Index Scan`     | Utilisation d'un index (rapide)                    |
| `Bitmap Scan`    | Lecture via bitmap d'index (entre Seq et Index)    |
| `Hash Join`      | Join via table de hachage en mémoire               |
| `Nested Loop`    | Join par boucle imbriquée                          |
| `cost=X..Y`      | Coût estimé (X = premier résultat, Y = tous)       |
| `actual time`    | Temps réel d'exécution                             |
| `rows`           | Nombre de lignes estimé / réel                     |

### Lire un plan d'exécution

1. Lisez de **l'intérieur vers l'extérieur** (les nœuds les plus profonds s'exécutent en premier)
2. Cherchez les `Seq Scan` sur de grandes tables — candidats pour un index
3. Comparez `rows` estimé vs réel — un grand écart signale que les statistiques sont périmées

### EXPLAIN simple dans SQLite — exemple pratique

```python
import sqlite3

conn = sqlite3.connect(":memory:")
cur = conn.cursor()

# Créer une table et insérer des données
cur.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")
cur.executemany("INSERT INTO t VALUES (?, ?)", [(i, f"val_{i}") for i in range(10000)])

# Plan SANS index
print("Sans index :")
for row in cur.execute("EXPLAIN QUERY PLAN SELECT * FROM t WHERE val = 'val_5000'"):
    print(" ", row)
# -> SCAN TABLE t  (lecture de 10000 lignes)

# Ajouter un index
cur.execute("CREATE INDEX idx_val ON t(val)")

# Plan AVEC index
print("\nAvec index :")
for row in cur.execute("EXPLAIN QUERY PLAN SELECT * FROM t WHERE val = 'val_5000'"):
    print(" ", row)
# -> SEARCH TABLE t USING INDEX idx_val (val=?)
```

---

## 6. Exemples avancés combinant tout

### Trouver la première commande de chaque utilisateur

```sql
-- Avec sous-requête corrélée
SELECT o.*
FROM orders o
WHERE o.ordered_at = (
    SELECT MIN(o2.ordered_at)
    FROM orders o2
    WHERE o2.user_id = o.user_id
);

-- Avec CTE et ROW_NUMBER (plus élégant)
WITH commandes_numerotees AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY ordered_at
        ) AS rn
    FROM orders
)
SELECT * FROM commandes_numerotees WHERE rn = 1;
```

### Rapport mensuel avec totaux cumulés

```sql
WITH ventes_mensuelles AS (
    SELECT
        strftime('%Y-%m', ordered_at) AS mois,
        COUNT(*)           AS nb_commandes,
        SUM(total_price)   AS ca_mensuel
    FROM orders
    WHERE status != 'cancelled'
    GROUP BY mois
)
SELECT
    mois,
    nb_commandes,
    ROUND(ca_mensuel, 2) AS ca_mensuel,
    ROUND(SUM(ca_mensuel) OVER (ORDER BY mois), 2) AS ca_cumule
FROM ventes_mensuelles
ORDER BY mois;
```

---

## Résumé

| Concept           | Quand l'utiliser                                          |
|-------------------|-----------------------------------------------------------|
| Sous-requête WHERE| Filtrer selon des résultats d'une autre requête           |
| Sous-requête corrélée | Calculs ligne par ligne (attention aux perf.)         |
| CTE (WITH)        | Rendre les sous-requêtes lisibles et réutilisables        |
| ROW_NUMBER        | Numéroter, dédoublonner, trouver le N-ième élément        |
| RANK / DENSE_RANK | Classements avec gestion des ex-aequo                    |
| LAG / LEAD        | Comparer avec lignes précédentes/suivantes                |
| Index B-tree      | Accélérer WHERE, JOIN, ORDER BY                          |
| Index composite   | Requêtes avec plusieurs colonnes filtrées                 |
| EXPLAIN           | Diagnostiquer les requêtes lentes                        |

La maîtrise de ces outils vous permet de passer de "ça marche" à "ça marche vite, même avec 10 millions de lignes".
