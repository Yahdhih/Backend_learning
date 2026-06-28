"""
Jour 22 — SQL Avancé : Sous-requêtes, INDEX et EXPLAIN
Exercice avec sqlite3 (base de données en mémoire)
"""

import sqlite3
import time


def creer_base_de_donnees():
    """Crée la base de données avec les données de test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT NOT NULL UNIQUE,
            is_active  INTEGER DEFAULT 1
        );

        CREATE TABLE products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT,
            price       REAL NOT NULL,
            stock_count INTEGER DEFAULT 0
        );

        CREATE TABLE orders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            quantity    INTEGER NOT NULL DEFAULT 1,
            total_price REAL NOT NULL,
            ordered_at  TEXT,
            status      TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id)    REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)

    cur.executemany("INSERT INTO users (name, email, is_active) VALUES (?, ?, ?)", [
        ("Alice Martin",    "alice@example.com",    1),
        ("Bob Dupont",      "bob@example.com",      1),
        ("Charlie Morin",   "charlie@example.com",  1),
        ("Diana Prince",    "diana@example.com",    0),
        ("Eve Lambert",     "eve@example.com",      1),
        ("Frank Leclerc",   "frank@example.com",    1),
    ])

    cur.executemany("INSERT INTO products (name, category, price, stock_count) VALUES (?, ?, ?, ?)", [
        ("Laptop Pro",          "Electronics", 1299.99, 15),
        ("Wireless Mouse",      "Electronics",   49.99, 50),
        ("Mechanical Keyboard", "Electronics",  129.99, 30),
        ("Python Book",         "Books",          39.99, 100),
        ("Django Book",         "Books",          44.99, 80),
        ("Standing Desk",       "Furniture",     599.99,  8),
        ("Office Chair",        "Furniture",     349.99, 12),
        ("USB Hub",             "Electronics",    29.99, 60),
    ])

    cur.executemany(
        "INSERT INTO orders (user_id, product_id, quantity, total_price, ordered_at, status) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, 1, 1, 1299.99, "2026-07-01 10:00:00", "completed"),
            (1, 2, 2,   99.98, "2026-07-03 11:00:00", "completed"),
            (1, 4, 1,   39.99, "2026-07-10 09:00:00", "pending"),
            (2, 3, 1,  129.99, "2026-07-02 14:00:00", "completed"),
            (2, 5, 2,   89.98, "2026-07-05 16:00:00", "completed"),
            (3, 6, 1,  599.99, "2026-07-08 12:00:00", "shipped"),
            (3, 7, 1,  349.99, "2026-07-09 13:00:00", "pending"),
            (4, 2, 1,   49.99, "2026-07-11 15:00:00", "cancelled"),
            (5, 8, 3,   89.97, "2026-07-12 17:00:00", "completed"),
            (5, 1, 1, 1299.99, "2026-07-15 10:00:00", "pending"),
            (6, 4, 2,   79.98, "2026-07-01 08:00:00", "completed"),
            (6, 5, 1,   44.99, "2026-07-06 11:00:00", "completed"),
            (1, 8, 1,   29.99, "2026-07-17 14:00:00", "completed"),
        ]
    )

    conn.commit()
    return conn


def afficher_resultats(titre, rows):
    print(f"\n{'='*65}")
    print(f"  {titre}")
    print(f"{'='*65}")
    if not rows:
        print("  (aucun résultat)")
        return
    cols = list(rows[0].keys())
    print("  " + " | ".join(f"{c:<22}" for c in cols))
    print("  " + "-" * (25 * len(cols)))
    for row in rows:
        print("  " + " | ".join(f"{str(row[c]):<22}" for c in cols))


# ============================================================
# EXERCICE 1 : Sous-requêtes dans WHERE
# ============================================================

def exercice_1_sous_requetes_where(conn):
    """
    TODO : Écrivez des requêtes avec des sous-requêtes dans WHERE.

    1a. Trouvez les utilisateurs qui ont passé au moins une commande
        avec le statut 'completed'. Utilisez IN avec une sous-requête.

    1b. Trouvez les produits dont le prix est supérieur
        au prix moyen de tous les produits.

    1c. Trouvez les utilisateurs qui ont passé une commande
        avec un total_price > 500. Utilisez EXISTS.
    """
    cur = conn.cursor()
    print("\n--- EXERCICE 1 : Sous-requêtes dans WHERE ---")

    # 1a. TODO : utilisateurs avec au moins une commande 'completed'
    query_1a = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_1a = """
    #     SELECT name, email
    #     FROM users
    #     WHERE id IN (
    #         SELECT DISTINCT user_id
    #         FROM orders
    #         WHERE status = 'completed'
    #     )
    # """
    rows = cur.execute(query_1a).fetchall()
    afficher_resultats("1a : Utilisateurs avec commande completed", rows)

    # 1b. TODO : produits au-dessus du prix moyen
    query_1b = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_1b = """
    #     SELECT name, price,
    #            ROUND((SELECT AVG(price) FROM products), 2) AS prix_moyen
    #     FROM products
    #     WHERE price > (SELECT AVG(price) FROM products)
    #     ORDER BY price DESC
    # """
    rows = cur.execute(query_1b).fetchall()
    afficher_resultats("1b : Produits au-dessus du prix moyen", rows)

    # 1c. TODO : utilisateurs avec EXISTS
    query_1c = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_1c = """
    #     SELECT name, email
    #     FROM users u
    #     WHERE EXISTS (
    #         SELECT 1 FROM orders o
    #         WHERE o.user_id = u.id AND o.total_price > 500
    #     )
    # """
    rows = cur.execute(query_1c).fetchall()
    afficher_resultats("1c : Utilisateurs avec commande > 500 (EXISTS)", rows)


# ============================================================
# EXERCICE 2 : CTEs
# ============================================================

def exercice_2_ctes(conn):
    """
    TODO : Réécrivez ces requêtes en utilisant des CTEs (WITH).

    2a. Avec une CTE, calculez la dépense totale par utilisateur,
        puis sélectionnez seulement ceux qui ont dépensé plus de 200€.

    2b. Avec deux CTEs chaînées :
        - CTE 1 : dépense totale par utilisateur
        - CTE 2 : moyenne des dépenses
        Résultat : utilisateurs au-dessus de la moyenne avec leur écart.

    2c. Trouvez la première commande de chaque utilisateur
        en utilisant une CTE avec ROW_NUMBER().
    """
    cur = conn.cursor()
    print("\n--- EXERCICE 2 : CTEs ---")

    # 2a. TODO : CTE avec filtre sur dépense > 200
    query_2a = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_2a = """
    #     WITH depenses AS (
    #         SELECT
    #             u.name,
    #             u.email,
    #             SUM(o.total_price) AS total
    #         FROM users u
    #         JOIN orders o ON u.id = o.user_id
    #         WHERE o.status != 'cancelled'
    #         GROUP BY u.id, u.name, u.email
    #     )
    #     SELECT name, email, ROUND(total, 2) AS total
    #     FROM depenses
    #     WHERE total > 200
    #     ORDER BY total DESC
    # """
    rows = cur.execute(query_2a).fetchall()
    afficher_resultats("2a : Utilisateurs ayant dépensé > 200€ (CTE)", rows)

    # 2b. TODO : deux CTEs chaînées
    query_2b = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_2b = """
    #     WITH
    #     depenses AS (
    #         SELECT u.name, SUM(o.total_price) AS total
    #         FROM users u JOIN orders o ON u.id = o.user_id
    #         WHERE o.status != 'cancelled'
    #         GROUP BY u.id, u.name
    #     ),
    #     stats AS (
    #         SELECT AVG(total) AS moyenne FROM depenses
    #     )
    #     SELECT
    #         d.name,
    #         ROUND(d.total, 2)          AS depense,
    #         ROUND(s.moyenne, 2)        AS moyenne,
    #         ROUND(d.total - s.moyenne, 2) AS ecart
    #     FROM depenses d, stats s
    #     WHERE d.total > s.moyenne
    #     ORDER BY d.total DESC
    # """
    rows = cur.execute(query_2b).fetchall()
    afficher_resultats("2b : Au-dessus de la moyenne (2 CTEs)", rows)

    # 2c. TODO : première commande par utilisateur avec ROW_NUMBER
    # Note: SQLite >= 3.25 supporte les window functions
    query_2c = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_2c = """
    #     WITH commandes_numerotees AS (
    #         SELECT
    #             o.id,
    #             o.user_id,
    #             u.name,
    #             o.ordered_at,
    #             o.total_price,
    #             ROW_NUMBER() OVER (
    #                 PARTITION BY o.user_id
    #                 ORDER BY o.ordered_at
    #             ) AS rn
    #         FROM orders o
    #         JOIN users u ON o.user_id = u.id
    #     )
    #     SELECT name, ordered_at, total_price
    #     FROM commandes_numerotees
    #     WHERE rn = 1
    #     ORDER BY ordered_at
    # """
    rows = cur.execute(query_2c).fetchall()
    afficher_resultats("2c : Première commande par utilisateur", rows)


# ============================================================
# EXERCICE 3 : Fonctions de fenêtrage
# ============================================================

def exercice_3_window_functions(conn):
    """
    TODO : Utilisez les fonctions de fenêtrage.

    3a. Pour chaque commande, affichez :
        - le nom de l'utilisateur
        - le total_price de la commande
        - le total cumulé des dépenses de cet utilisateur (dans l'ordre chronologique)

    3b. Classez les produits par prix dans leur catégorie
        (RANK() OVER PARTITION BY category ORDER BY price DESC).

    3c. Pour chaque commande, montrez la différence de prix
        avec la commande précédente du même utilisateur (LAG).
    """
    cur = conn.cursor()
    print("\n--- EXERCICE 3 : Window Functions ---")

    # 3a. TODO : total cumulé par utilisateur
    query_3a = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_3a = """
    #     SELECT
    #         u.name,
    #         o.ordered_at,
    #         o.total_price,
    #         ROUND(SUM(o.total_price) OVER (
    #             PARTITION BY o.user_id
    #             ORDER BY o.ordered_at
    #             ROWS UNBOUNDED PRECEDING
    #         ), 2) AS cumule
    #     FROM orders o
    #     JOIN users u ON o.user_id = u.id
    #     ORDER BY o.user_id, o.ordered_at
    # """
    rows = cur.execute(query_3a).fetchall()
    afficher_resultats("3a : Total cumulé par utilisateur", rows)

    # 3b. TODO : classement dans la catégorie
    query_3b = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_3b = """
    #     SELECT
    #         category,
    #         name,
    #         price,
    #         RANK() OVER (
    #             PARTITION BY category
    #             ORDER BY price DESC
    #         ) AS rang_dans_categorie
    #     FROM products
    #     ORDER BY category, rang_dans_categorie
    # """
    rows = cur.execute(query_3b).fetchall()
    afficher_resultats("3b : Classement par prix dans la catégorie", rows)

    # 3c. TODO : différence avec commande précédente
    query_3c = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_3c = """
    #     SELECT
    #         u.name,
    #         o.ordered_at,
    #         o.total_price,
    #         LAG(o.total_price) OVER (
    #             PARTITION BY o.user_id
    #             ORDER BY o.ordered_at
    #         ) AS commande_precedente,
    #         ROUND(o.total_price - LAG(o.total_price) OVER (
    #             PARTITION BY o.user_id
    #             ORDER BY o.ordered_at
    #         ), 2) AS difference
    #     FROM orders o
    #     JOIN users u ON o.user_id = u.id
    #     ORDER BY o.user_id, o.ordered_at
    # """
    rows = cur.execute(query_3c).fetchall()
    afficher_resultats("3c : Différence avec commande précédente (LAG)", rows)


# ============================================================
# EXERCICE 4 : INDEX et EXPLAIN
# ============================================================

def exercice_4_index_explain(conn):
    """
    Démonstration de l'impact des INDEX sur les plans d'exécution.
    Pas de TODO ici — observez et comprenez les résultats.
    """
    cur = conn.cursor()
    print("\n--- EXERCICE 4 : INDEX et EXPLAIN ---")

    # Plan SANS index sur user_id
    print("\n  Plan SANS index sur orders.user_id :")
    plan = cur.execute("EXPLAIN QUERY PLAN SELECT * FROM orders WHERE user_id = 1").fetchall()
    for row in plan:
        print(f"    {tuple(row)}")

    # Ajouter un index
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
    print("\n  -> Index créé : idx_orders_user_id")

    # Plan AVEC index
    print("\n  Plan AVEC index sur orders.user_id :")
    plan = cur.execute("EXPLAIN QUERY PLAN SELECT * FROM orders WHERE user_id = 1").fetchall()
    for row in plan:
        print(f"    {tuple(row)}")

    # Index composite
    cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_status ON orders(user_id, status)")
    print("\n  -> Index composite créé : idx_orders_user_status(user_id, status)")

    print("\n  Plan avec filtre user_id + status (utilise l'index composite) :")
    plan = cur.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM orders WHERE user_id = 1 AND status = 'completed'"
    ).fetchall()
    for row in plan:
        print(f"    {tuple(row)}")

    print("\n  Plan avec filtre status seul (N'utilise PAS l'index composite) :")
    plan = cur.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM orders WHERE status = 'completed'"
    ).fetchall()
    for row in plan:
        print(f"    {tuple(row)}")

    print("\n  Observation : un index composite (A, B) aide les filtres sur A ou A+B,")
    print("  mais PAS sur B seul. L'ordre des colonnes dans l'index est crucial.")


# ============================================================
# FONCTION TESTER
# ============================================================

def tester():
    print("\n" + "="*65)
    print("   JOUR 22 — SQL Avancé : Sous-requêtes, INDEX, EXPLAIN")
    print("="*65)

    conn = creer_base_de_donnees()
    cur = conn.cursor()

    nb = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    print(f"\nBase de données : {nb} commandes chargées")

    exercice_1_sous_requetes_where(conn)
    exercice_2_ctes(conn)
    exercice_3_window_functions(conn)
    exercice_4_index_explain(conn)

    # --- Tests automatiques ---
    print("\n" + "="*65)
    print("   VERIFICATION DES SOLUTIONS")
    print("="*65)

    tests_passes = 0
    tests_total = 0

    def verifier(description, query, condition_fn):
        nonlocal tests_passes, tests_total
        tests_total += 1
        try:
            rows = cur.execute(query).fetchall()
            if condition_fn(rows):
                print(f"  OK  {description}")
                tests_passes += 1
            else:
                print(f"  !!  {description} — résultat inattendu")
        except Exception as e:
            print(f"  ERR {description} — {e}")

    verifier(
        "Utilisateurs avec commande completed >= 4",
        """
        SELECT COUNT(DISTINCT u.id) AS n FROM users u
        WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id AND o.status = 'completed')
        """,
        lambda rows: rows[0]["n"] >= 4
    )

    verifier(
        "Produits au-dessus du prix moyen existent",
        """
        SELECT COUNT(*) AS n FROM products
        WHERE price > (SELECT AVG(price) FROM products)
        """,
        lambda rows: rows[0]["n"] >= 1
    )

    verifier(
        "CTE : au moins un utilisateur a dépensé > 200€",
        """
        WITH d AS (
            SELECT u.id, SUM(o.total_price) AS total
            FROM users u JOIN orders o ON u.id = o.user_id
            WHERE o.status != 'cancelled'
            GROUP BY u.id
        )
        SELECT COUNT(*) AS n FROM d WHERE total > 200
        """,
        lambda rows: rows[0]["n"] >= 1
    )

    verifier(
        "ROW_NUMBER fonctionne (première commande)",
        """
        WITH cn AS (
            SELECT user_id,
                   ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY ordered_at) AS rn
            FROM orders
        )
        SELECT COUNT(*) AS n FROM cn WHERE rn = 1
        """,
        lambda rows: rows[0]["n"] == 6  # 6 utilisateurs distincts
    )

    verifier(
        "LAG retourne NULL pour la première commande",
        """
        SELECT
            user_id,
            ordered_at,
            LAG(ordered_at) OVER (PARTITION BY user_id ORDER BY ordered_at) AS precedente
        FROM orders
        WHERE user_id = 1
        ORDER BY ordered_at
        LIMIT 1
        """,
        lambda rows: rows[0]["precedente"] is None
    )

    print(f"\n  Résultat : {tests_passes}/{tests_total} tests passés")
    conn.close()


if __name__ == "__main__":
    tester()
