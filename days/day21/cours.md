# Jour 21 — SQL Fondamentaux : SELECT, WHERE, JOIN, GROUP BY (17 juillet 2026)

---

## Introduction : Qu'est-ce qu'une base de données relationnelle ?

Une **base de données relationnelle** organise les données en **tables** (aussi appelées relations). Chaque table ressemble à un tableau : des colonnes définissent la structure, des lignes contiennent les données.

Le modèle relationnel repose sur trois idées fondamentales :

1. **Les tables** sont indépendantes mais peuvent être liées entre elles via des clés.
2. **Les clés primaires** (PRIMARY KEY) identifient chaque ligne de façon unique.
3. **Les clés étrangères** (FOREIGN KEY) créent des liens entre les tables.

```
Table: users                    Table: orders
+----+----------+----------+    +----+---------+----------+--------+
| id | name     | email    |    | id | user_id | product  | amount |
+----+----------+----------+    +----+---------+----------+--------+
|  1 | Alice    | a@ex.com |    |  1 |       1 | Laptop   |   999  |
|  2 | Bob      | b@ex.com |    |  2 |       1 | Mouse    |    29  |
|  3 | Charlie  | c@ex.com |    |  3 |       2 | Keyboard |    79  |
+----+----------+----------+    +----+---------+----------+--------+
                                        ^
                                        |
                               FOREIGN KEY -> users.id
```

**SQL (Structured Query Language)** est le langage standard pour interagir avec ces bases de données. Il est déclaratif : vous dites *quoi* vous voulez, pas *comment* l'obtenir.

---

## Schéma de référence

Tout au long de ce cours, nous utiliserons ce schéma :

```sql
-- Utilisateurs
users(id, name, email, created_at, is_active)

-- Produits
products(id, name, category, price, stock_count)

-- Commandes
orders(id, user_id, product_id, quantity, total_price, ordered_at, status)
```

---

## 1. CREATE TABLE — Créer des tables

### Types de données courants

| Type SQL         | Description                              | Exemple               |
|------------------|------------------------------------------|-----------------------|
| `INTEGER`        | Entier                                   | 42, -7, 0             |
| `REAL` / `FLOAT` | Nombre décimal                           | 3.14, 99.99           |
| `TEXT`           | Texte de longueur variable               | 'Bonjour'             |
| `VARCHAR(n)`     | Texte limité à n caractères              | 'Alice' (max 50 car.) |
| `BOOLEAN`        | Vrai/Faux (souvent 0/1 en SQLite)        | TRUE, FALSE           |
| `TIMESTAMP`      | Date et heure                            | '2026-07-17 10:30:00' |
| `DATE`           | Date sans heure                          | '2026-07-17'          |

### Création des tables

```sql
CREATE TABLE users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active  BOOLEAN DEFAULT TRUE
);

CREATE TABLE products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(200) NOT NULL,
    category    VARCHAR(100),
    price       REAL NOT NULL CHECK (price >= 0),
    stock_count INTEGER DEFAULT 0
);

CREATE TABLE orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    product_id  INTEGER NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 1,
    total_price REAL NOT NULL,
    ordered_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status      VARCHAR(50) DEFAULT 'pending',
    FOREIGN KEY (user_id)    REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

**Contraintes importantes :**
- `PRIMARY KEY` : identifiant unique, jamais NULL
- `NOT NULL` : la colonne doit toujours avoir une valeur
- `UNIQUE` : pas deux lignes avec la même valeur
- `DEFAULT` : valeur si rien n'est fourni
- `CHECK` : validation de données
- `FOREIGN KEY` : intégrité référentielle

---

## 2. INSERT, UPDATE, DELETE

### INSERT — Insérer des données

```sql
-- Insérer une ligne
INSERT INTO users (name, email) VALUES ('Alice Martin', 'alice@example.com');

-- Insérer plusieurs lignes d'un coup
INSERT INTO users (name, email, is_active) VALUES
    ('Bob Dupont',   'bob@example.com',     TRUE),
    ('Charlie Morin','charlie@example.com',  TRUE),
    ('Diana Prince', 'diana@example.com',    FALSE);

-- Insérer des produits
INSERT INTO products (name, category, price, stock_count) VALUES
    ('Laptop Pro',    'Electronics', 1299.99, 15),
    ('Wireless Mouse','Electronics',   49.99, 50),
    ('Mechanical Keyboard', 'Electronics', 129.99, 30),
    ('Python Book',   'Books',         39.99, 100),
    ('Standing Desk', 'Furniture',    599.99,  8);
```

### UPDATE — Modifier des données

```sql
-- Modifier une ligne précise
UPDATE users SET is_active = FALSE WHERE id = 4;

-- Modifier plusieurs colonnes
UPDATE products
SET price = 44.99, stock_count = 45
WHERE name = 'Wireless Mouse';

-- Augmenter tous les prix d'une catégorie de 10%
UPDATE products
SET price = price * 1.10
WHERE category = 'Electronics';
```

**ATTENTION :** Un UPDATE sans WHERE modifie TOUTES les lignes !

### DELETE — Supprimer des données

```sql
-- Supprimer une ligne précise
DELETE FROM orders WHERE id = 7;

-- Supprimer toutes les commandes annulées
DELETE FROM orders WHERE status = 'cancelled';

-- Supprimer tous les utilisateurs inactifs (dangereux !)
DELETE FROM users WHERE is_active = FALSE;
```

---

## 3. SELECT — Lire des données

### La structure d'un SELECT

```sql
SELECT   colonne1, colonne2, ...    -- Quelles colonnes afficher
FROM     table                      -- Depuis quelle table
WHERE    condition                  -- Filtrer les lignes
ORDER BY colonne ASC|DESC           -- Trier les résultats
LIMIT    n                          -- Limiter le nombre de lignes
OFFSET   m;                         -- Sauter les m premières lignes
```

### Exemples de base

```sql
-- Sélectionner toutes les colonnes
SELECT * FROM users;

-- Sélectionner des colonnes spécifiques
SELECT name, email FROM users;

-- Renommer une colonne dans le résultat (alias)
SELECT name AS nom_utilisateur, email AS adresse_email
FROM users;

-- Faire des calculs
SELECT name, price, price * 1.20 AS prix_avec_tva
FROM products;
```

---

## 4. WHERE — Filtrer les données

### Opérateurs de comparaison

```sql
-- Égalité
SELECT * FROM users WHERE name = 'Alice Martin';

-- Différence
SELECT * FROM products WHERE category != 'Electronics';

-- Comparaisons numériques
SELECT * FROM products WHERE price > 100;
SELECT * FROM products WHERE price >= 100;
SELECT * FROM products WHERE price < 50;
SELECT * FROM products WHERE stock_count <= 10;
```

### LIKE — Recherche par motif

```sql
-- % remplace n'importe quelle séquence de caractères
SELECT * FROM users WHERE email LIKE '%@example.com';   -- se termine par
SELECT * FROM products WHERE name LIKE 'Laptop%';       -- commence par
SELECT * FROM products WHERE name LIKE '%Pro%';         -- contient

-- _ remplace un seul caractère
SELECT * FROM users WHERE name LIKE 'A____';  -- A + exactement 4 caractères
```

### IN — Valeur dans une liste

```sql
-- Trouver les utilisateurs par IDs
SELECT * FROM users WHERE id IN (1, 3, 5);

-- Trouver des catégories spécifiques
SELECT * FROM products WHERE category IN ('Electronics', 'Books');

-- Inverse : NOT IN
SELECT * FROM products WHERE category NOT IN ('Furniture');
```

### BETWEEN — Intervalle

```sql
-- Prix entre 50 et 200 euros
SELECT * FROM products WHERE price BETWEEN 50 AND 200;

-- Commandes d'une période
SELECT * FROM orders
WHERE ordered_at BETWEEN '2026-07-01' AND '2026-07-31';

-- Equivalent à : WHERE ordered_at >= '2026-07-01' AND ordered_at <= '2026-07-31'
```

### IS NULL / IS NOT NULL

```sql
-- Utilisateurs sans catégorie de produit (colonne NULL)
SELECT * FROM products WHERE category IS NULL;

-- Commandes avec un prix renseigné
SELECT * FROM orders WHERE total_price IS NOT NULL;
```

### AND, OR, NOT — Combiner les conditions

```sql
-- AND : les deux conditions doivent être vraies
SELECT * FROM products
WHERE category = 'Electronics' AND price < 100;

-- OR : au moins une condition doit être vraie
SELECT * FROM products
WHERE category = 'Electronics' OR category = 'Books';

-- NOT : inverse la condition
SELECT * FROM users WHERE NOT is_active;

-- Combinaison complexe (parenthèses importantes !)
SELECT * FROM products
WHERE (category = 'Electronics' OR category = 'Books')
  AND price < 200
  AND stock_count > 0;
```

---

## 5. ORDER BY, LIMIT, OFFSET

### ORDER BY — Trier

```sql
-- Ordre croissant (défaut)
SELECT * FROM products ORDER BY price ASC;
SELECT * FROM products ORDER BY price;       -- idem

-- Ordre décroissant
SELECT * FROM products ORDER BY price DESC;

-- Trier par plusieurs colonnes
SELECT * FROM products ORDER BY category ASC, price DESC;

-- Trier par position de colonne
SELECT name, price FROM products ORDER BY 2 DESC;  -- trie par price
```

### LIMIT et OFFSET — Pagination

```sql
-- Les 5 produits les plus chers
SELECT * FROM products ORDER BY price DESC LIMIT 5;

-- Pagination : page 2, 10 éléments par page
-- Page 1 : LIMIT 10 OFFSET 0
-- Page 2 : LIMIT 10 OFFSET 10
-- Page 3 : LIMIT 10 OFFSET 20
SELECT * FROM products ORDER BY id LIMIT 10 OFFSET 10;
```

---

## 6. JOIN — Combiner plusieurs tables

Un JOIN combine des lignes de deux tables (ou plus) selon une condition.

### INNER JOIN — Uniquement les lignes qui correspondent

```sql
-- Afficher les commandes avec le nom de l'utilisateur
SELECT
    orders.id,
    users.name,
    orders.total_price,
    orders.status
FROM orders
INNER JOIN users ON orders.user_id = users.id;
```

Résultat : **seules les commandes qui ont un utilisateur correspondant** apparaissent. Si une commande référence un user_id inexistant, elle est exclue.

```
orders:           users:              INNER JOIN résultat:
+----+---------+  +----+-------+      +----+---------+-------+
| id | user_id |  | id | name  |      | id | user_id | name  |
+----+---------+  +----+-------+      +----+---------+-------+
|  1 |       1 |  |  1 | Alice |  ->  |  1 |       1 | Alice |
|  2 |       2 |  |  2 | Bob   |  ->  |  2 |       2 | Bob   |
|  3 |      99 |  |  3 | Carol |      (exclue: user 99 inexistant)
+----+---------+  +----+-------+
```

### LEFT JOIN — Toutes les lignes de gauche

```sql
-- Tous les utilisateurs, même ceux sans commandes
SELECT
    users.name,
    orders.id    AS order_id,
    orders.total_price
FROM users
LEFT JOIN orders ON users.id = orders.user_id;
```

```
users:             orders:             LEFT JOIN résultat:
+----+-------+     +----+---------+   +-------+----------+-------------+
| id | name  |     | id | user_id |   | name  | order_id | total_price |
+----+-------+     +----+---------+   +-------+----------+-------------+
|  1 | Alice |  -> |  1 |       1 |   | Alice |        1 |      999.00 |
|  2 | Bob   |  -> |  2 |       1 |   | Alice |        2 |       29.00 |
|  3 | Carol |     |  3 |       2 |   | Bob   |        3 |       79.00 |
+----+-------+     +----+---------+   | Carol |     NULL |        NULL | <- Carol apparaît !
```

### RIGHT JOIN — Toutes les lignes de droite

```sql
-- Toutes les commandes, même si le produit a été supprimé
SELECT
    orders.id,
    products.name AS product_name,
    orders.total_price
FROM orders
RIGHT JOIN products ON orders.product_id = products.id;
```

Note : RIGHT JOIN est rare. On préfère généralement inverser les tables et utiliser LEFT JOIN.

### FULL OUTER JOIN — Toutes les lignes des deux côtés

```sql
-- Tous les utilisateurs ET toutes les commandes
-- (les non-correspondances ont NULL des deux côtés)
SELECT
    users.name,
    orders.id AS order_id
FROM users
FULL OUTER JOIN orders ON users.id = orders.user_id;
```

Note : SQLite ne supporte pas FULL OUTER JOIN nativement. On peut le simuler avec UNION.

### JOIN avec alias (syntaxe raccourcie)

```sql
-- Utiliser des alias pour alléger la syntaxe
SELECT
    u.name,
    p.name  AS product_name,
    o.quantity,
    o.total_price
FROM orders o
INNER JOIN users    u ON o.user_id    = u.id
INNER JOIN products p ON o.product_id = p.id
WHERE o.status = 'completed'
ORDER BY o.ordered_at DESC;
```

---

## 7. GROUP BY et HAVING

### GROUP BY — Regrouper les lignes

GROUP BY regroupe les lignes qui ont la même valeur dans une (ou plusieurs) colonnes, pour appliquer des **fonctions d'agrégation**.

```sql
-- Nombre de commandes par utilisateur
SELECT
    user_id,
    COUNT(*) AS nombre_commandes
FROM orders
GROUP BY user_id;

-- Dépense totale par utilisateur
SELECT
    user_id,
    SUM(total_price) AS depense_totale
FROM orders
GROUP BY user_id;

-- Avec un JOIN pour avoir le nom
SELECT
    u.name,
    COUNT(o.id)      AS nb_commandes,
    SUM(o.total_price) AS total_depense
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name;
```

**Règle importante :** Chaque colonne dans le SELECT doit être soit :
- dans le GROUP BY, soit
- dans une fonction d'agrégation (COUNT, SUM, AVG, MIN, MAX)

### HAVING — Filtrer après le regroupement

WHERE filtre **avant** le GROUP BY. HAVING filtre **après**.

```sql
-- Utilisateurs qui ont dépensé plus de 500€
SELECT
    u.name,
    SUM(o.total_price) AS total
FROM users u
JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name
HAVING SUM(o.total_price) > 500;

-- Catégories avec plus de 5 produits
SELECT
    category,
    COUNT(*) AS nb_produits
FROM products
GROUP BY category
HAVING COUNT(*) > 5;

-- Combinaison WHERE + HAVING
SELECT
    u.name,
    COUNT(o.id) AS nb_commandes
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.status = 'completed'        -- filtre avant regroupement
GROUP BY u.id, u.name
HAVING COUNT(o.id) >= 3;            -- filtre après regroupement
```

---

## 8. Fonctions d'agrégation

### COUNT — Compter

```sql
-- Nombre total de lignes
SELECT COUNT(*) FROM orders;

-- Compter seulement les valeurs non-NULL
SELECT COUNT(total_price) FROM orders;

-- Compter les valeurs distinctes
SELECT COUNT(DISTINCT user_id) FROM orders;
```

### SUM — Somme

```sql
-- Chiffre d'affaires total
SELECT SUM(total_price) AS ca_total FROM orders;

-- Chiffre d'affaires par statut
SELECT status, SUM(total_price) AS ca
FROM orders
GROUP BY status;
```

### AVG — Moyenne

```sql
-- Prix moyen des produits
SELECT AVG(price) AS prix_moyen FROM products;

-- Prix moyen par catégorie
SELECT category, AVG(price) AS prix_moyen
FROM products
GROUP BY category;
```

### MIN et MAX — Minimum et Maximum

```sql
-- Le produit le moins et le plus cher
SELECT
    MIN(price) AS prix_min,
    MAX(price) AS prix_max,
    MAX(price) - MIN(price) AS ecart
FROM products;

-- La première et dernière commande par utilisateur
SELECT
    user_id,
    MIN(ordered_at) AS premiere_commande,
    MAX(ordered_at) AS derniere_commande
FROM orders
GROUP BY user_id;
```

---

## 9. L'ordre d'exécution d'une requête SQL

SQL s'exécute dans un ordre précis, **différent** de l'ordre d'écriture :

```
1. FROM        -- Quelle(s) table(s) ?
2. JOIN        -- Combiner les tables
3. WHERE       -- Filtrer les lignes
4. GROUP BY    -- Regrouper
5. HAVING      -- Filtrer les groupes
6. SELECT      -- Calculer les colonnes à afficher
7. ORDER BY    -- Trier
8. LIMIT/OFFSET -- Paginer
```

C'est pourquoi vous ne pouvez pas utiliser un alias défini dans SELECT dans une clause WHERE :

```sql
-- ERREUR : total n'est pas encore défini au moment du WHERE
SELECT SUM(total_price) AS total FROM orders WHERE total > 100;

-- CORRECT : utiliser HAVING après GROUP BY
SELECT user_id, SUM(total_price) AS total
FROM orders
GROUP BY user_id
HAVING SUM(total_price) > 100;
```

---

## 10. Requêtes complètes d'exemple

### Rapport de ventes par catégorie

```sql
SELECT
    p.category,
    COUNT(DISTINCT o.user_id)  AS nb_clients,
    COUNT(o.id)                AS nb_ventes,
    SUM(o.quantity)            AS unites_vendues,
    SUM(o.total_price)         AS ca_total,
    AVG(o.total_price)         AS panier_moyen,
    MIN(o.ordered_at)          AS premiere_vente,
    MAX(o.ordered_at)          AS derniere_vente
FROM products p
LEFT JOIN orders o ON p.id = o.product_id
WHERE o.status IN ('completed', 'shipped')
GROUP BY p.category
HAVING COUNT(o.id) > 0
ORDER BY ca_total DESC;
```

### Top 5 clients par dépense

```sql
SELECT
    u.name,
    u.email,
    COUNT(o.id)        AS nb_commandes,
    SUM(o.total_price) AS total_depense,
    AVG(o.total_price) AS panier_moyen
FROM users u
INNER JOIN orders o ON u.id = o.user_id
WHERE u.is_active = TRUE
  AND o.status != 'cancelled'
GROUP BY u.id, u.name, u.email
ORDER BY total_depense DESC
LIMIT 5;
```

### Produits jamais commandés

```sql
SELECT
    p.name,
    p.category,
    p.price,
    p.stock_count
FROM products p
LEFT JOIN orders o ON p.id = o.product_id
WHERE o.id IS NULL
ORDER BY p.category, p.name;
```

---

## Résumé

| Clause      | Rôle                                      | Ordre d'exécution |
|-------------|-------------------------------------------|-------------------|
| FROM        | Source des données                        | 1                 |
| JOIN        | Combiner des tables                       | 2                 |
| WHERE       | Filtrer les lignes individuelles          | 3                 |
| GROUP BY    | Regrouper pour les agrégations            | 4                 |
| HAVING      | Filtrer les groupes                       | 5                 |
| SELECT      | Définir les colonnes du résultat          | 6                 |
| ORDER BY    | Trier le résultat final                   | 7                 |
| LIMIT/OFFSET| Paginer le résultat                       | 8                 |

Le SQL est la compétence fondamentale de tout développeur backend. Avant de maîtriser Django ORM (jours 23-24), il est essentiel de comprendre ce que SQL fait réellement en dessous.
