"""
Jour 21 — SQL Fondamentaux : SELECT, WHERE, JOIN, GROUP BY
Exercice avec sqlite3 (base de données en mémoire)
"""

import sqlite3


def creer_base_de_donnees():
    """Crée une base de données en mémoire avec les tables et les données."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row  # permet d'accéder aux colonnes par nom
    cur = conn.cursor()

    # --- Création des tables ---
    cur.executescript("""
        CREATE TABLE users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
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
            ordered_at  TEXT DEFAULT CURRENT_TIMESTAMP,
            status      TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id)    REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)

    # --- Insertion des données ---
    cur.executemany(
        "INSERT INTO users (name, email, is_active) VALUES (?, ?, ?)",
        [
            ("Alice Martin",   "alice@example.com",   1),
            ("Bob Dupont",     "bob@example.com",     1),
            ("Charlie Morin",  "charlie@example.com", 1),
            ("Diana Prince",   "diana@example.com",   0),
            ("Eve Lambert",    "eve@example.com",     1),
        ]
    )

    cur.executemany(
        "INSERT INTO products (name, category, price, stock_count) VALUES (?, ?, ?, ?)",
        [
            ("Laptop Pro",          "Electronics", 1299.99, 15),
            ("Wireless Mouse",      "Electronics",   49.99, 50),
            ("Mechanical Keyboard", "Electronics",  129.99, 30),
            ("Python Book",         "Books",          39.99, 100),
            ("Django Book",         "Books",          44.99, 80),
            ("Standing Desk",       "Furniture",     599.99,  8),
            ("Office Chair",        "Furniture",     349.99, 12),
            ("USB Hub",             "Electronics",    29.99, 60),
        ]
    )

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
        ]
    )

    conn.commit()
    return conn


def afficher_resultats(titre, rows):
    """Affiche les résultats d'une requête de façon lisible."""
    print(f"\n{'='*60}")
    print(f"  {titre}")
    print(f"{'='*60}")
    if not rows:
        print("  (aucun résultat)")
        return
    # Afficher les noms de colonnes
    cols = rows[0].keys()
    print("  " + " | ".join(f"{c:<20}" for c in cols))
    print("  " + "-" * (23 * len(list(cols))))
    for row in rows:
        print("  " + " | ".join(f"{str(row[c]):<20}" for c in cols))


# ============================================================
# EXERCICE 1 : SELECT basique
# ============================================================

def exercice_1_select_basique(conn):
    """
    TODO : Écrivez les requêtes suivantes.

    1a. Sélectionnez le nom et l'email de tous les utilisateurs actifs.
    1b. Sélectionnez tous les produits de la catégorie "Electronics"
        dont le prix est inférieur à 100€, triés par prix croissant.
    1c. Sélectionnez les 3 produits les plus chers.
    """
    cur = conn.cursor()

    print("\n--- EXERCICE 1 : SELECT basique ---")

    # 1a. TODO : nom et email des utilisateurs actifs
    # Remplacez "SELECT 'TODO' AS resultat" par votre requête
    query_1a = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_1a = """
    #     SELECT name, email
    #     FROM users
    #     WHERE is_active = 1
    # """
    rows = cur.execute(query_1a).fetchall()
    afficher_resultats("1a : Utilisateurs actifs", rows)

    # 1b. TODO : Electronics < 100€, triés par prix
    query_1b = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_1b = """
    #     SELECT name, category, price
    #     FROM products
    #     WHERE category = 'Electronics' AND price < 100
    #     ORDER BY price ASC
    # """
    rows = cur.execute(query_1b).fetchall()
    afficher_resultats("1b : Electronics < 100€", rows)

    # 1c. TODO : 3 produits les plus chers
    query_1c = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_1c = """
    #     SELECT name, price
    #     FROM products
    #     ORDER BY price DESC
    #     LIMIT 3
    # """
    rows = cur.execute(query_1c).fetchall()
    afficher_resultats("1c : Top 3 produits les plus chers", rows)


# ============================================================
# EXERCICE 2 : WHERE avec opérateurs avancés
# ============================================================

def exercice_2_where_avance(conn):
    """
    TODO : Utilisez LIKE, IN, BETWEEN, IS NULL.

    2a. Trouvez tous les produits dont le nom contient "Book".
    2b. Trouvez les commandes avec le statut 'completed' OU 'shipped'
        (utilisez IN).
    2c. Trouvez les produits dont le prix est entre 50 et 300€.
    2d. Trouvez les commandes passées entre le 5 et le 10 juillet 2026.
    """
    cur = conn.cursor()

    print("\n--- EXERCICE 2 : WHERE avancé ---")

    # 2a. TODO : produits contenant "Book"
    query_2a = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_2a = "SELECT name, price FROM products WHERE name LIKE '%Book%'"
    rows = cur.execute(query_2a).fetchall()
    afficher_resultats("2a : Produits contenant 'Book'", rows)

    # 2b. TODO : commandes completed ou shipped
    query_2b = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_2b = "SELECT id, user_id, total_price, status FROM orders WHERE status IN ('completed', 'shipped')"
    rows = cur.execute(query_2b).fetchall()
    afficher_resultats("2b : Commandes completed ou shipped", rows)

    # 2c. TODO : produits entre 50 et 300€
    query_2c = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_2c = "SELECT name, price FROM products WHERE price BETWEEN 50 AND 300 ORDER BY price"
    rows = cur.execute(query_2c).fetchall()
    afficher_resultats("2c : Produits entre 50 et 300€", rows)

    # 2d. TODO : commandes entre le 5 et le 10 juillet
    query_2d = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_2d = """
    #     SELECT id, user_id, total_price, ordered_at, status
    #     FROM orders
    #     WHERE ordered_at BETWEEN '2026-07-05' AND '2026-07-10 23:59:59'
    #     ORDER BY ordered_at
    # """
    rows = cur.execute(query_2d).fetchall()
    afficher_resultats("2d : Commandes 5-10 juillet", rows)


# ============================================================
# EXERCICE 3 : JOIN
# ============================================================

def exercice_3_join(conn):
    """
    TODO : Pratiquez les JOIN.

    3a. Affichez chaque commande avec le nom de l'utilisateur
        et le nom du produit (INNER JOIN sur 3 tables).
    3b. Affichez tous les utilisateurs et le nombre de commandes
        qu'ils ont passées (y compris ceux avec 0 commandes).
        Utilisez LEFT JOIN + COUNT.
    3c. Trouvez les produits qui n'ont jamais été commandés.
        Utilisez LEFT JOIN + WHERE ... IS NULL.
    """
    cur = conn.cursor()

    print("\n--- EXERCICE 3 : JOIN ---")

    # 3a. TODO : commandes avec noms utilisateur et produit
    query_3a = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_3a = """
    #     SELECT
    #         o.id        AS order_id,
    #         u.name      AS utilisateur,
    #         p.name      AS produit,
    #         o.quantity,
    #         o.total_price,
    #         o.status
    #     FROM orders o
    #     INNER JOIN users    u ON o.user_id    = u.id
    #     INNER JOIN products p ON o.product_id = p.id
    #     ORDER BY o.id
    # """
    rows = cur.execute(query_3a).fetchall()
    afficher_resultats("3a : Commandes avec noms", rows)

    # 3b. TODO : utilisateurs avec nombre de commandes
    query_3b = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_3b = """
    #     SELECT
    #         u.name,
    #         COUNT(o.id) AS nb_commandes
    #     FROM users u
    #     LEFT JOIN orders o ON u.id = o.user_id
    #     GROUP BY u.id, u.name
    #     ORDER BY nb_commandes DESC
    # """
    rows = cur.execute(query_3b).fetchall()
    afficher_resultats("3b : Utilisateurs et nb commandes", rows)

    # 3c. TODO : produits jamais commandés
    query_3c = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_3c = """
    #     SELECT p.name, p.category, p.price
    #     FROM products p
    #     LEFT JOIN orders o ON p.id = o.product_id
    #     WHERE o.id IS NULL
    # """
    rows = cur.execute(query_3c).fetchall()
    afficher_resultats("3c : Produits jamais commandés", rows)


# ============================================================
# EXERCICE 4 : GROUP BY et agrégations
# ============================================================

def exercice_4_group_by(conn):
    """
    TODO : Pratiquez GROUP BY, HAVING et les fonctions d'agrégation.

    4a. Calculez le chiffre d'affaires total par catégorie de produit.
        (joindre orders et products, grouper par category)
    4b. Trouvez les utilisateurs qui ont passé plus d'une commande.
        Affichez leur nom et leur nombre de commandes.
    4c. Calculez le prix moyen, minimum et maximum par catégorie.
    4d. Trouvez le top 3 des utilisateurs par dépense totale
        (en excluant les commandes annulées).
    """
    cur = conn.cursor()

    print("\n--- EXERCICE 4 : GROUP BY et agrégations ---")

    # 4a. TODO : CA par catégorie
    query_4a = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_4a = """
    #     SELECT
    #         p.category,
    #         COUNT(o.id)        AS nb_ventes,
    #         SUM(o.total_price) AS ca_total
    #     FROM orders o
    #     INNER JOIN products p ON o.product_id = p.id
    #     GROUP BY p.category
    #     ORDER BY ca_total DESC
    # """
    rows = cur.execute(query_4a).fetchall()
    afficher_resultats("4a : CA par catégorie", rows)

    # 4b. TODO : utilisateurs avec plus d'une commande
    query_4b = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_4b = """
    #     SELECT
    #         u.name,
    #         COUNT(o.id) AS nb_commandes
    #     FROM users u
    #     INNER JOIN orders o ON u.id = o.user_id
    #     GROUP BY u.id, u.name
    #     HAVING COUNT(o.id) > 1
    #     ORDER BY nb_commandes DESC
    # """
    rows = cur.execute(query_4b).fetchall()
    afficher_resultats("4b : Utilisateurs avec plus d'une commande", rows)

    # 4c. TODO : statistiques de prix par catégorie
    query_4c = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_4c = """
    #     SELECT
    #         category,
    #         ROUND(AVG(price), 2) AS prix_moyen,
    #         MIN(price)           AS prix_min,
    #         MAX(price)           AS prix_max
    #     FROM products
    #     GROUP BY category
    #     ORDER BY prix_moyen DESC
    # """
    rows = cur.execute(query_4c).fetchall()
    afficher_resultats("4c : Stats prix par catégorie", rows)

    # 4d. TODO : top 3 utilisateurs par dépense (hors annulées)
    query_4d = "SELECT 'TODO' AS resultat"
    # SOLUTION :
    # query_4d = """
    #     SELECT
    #         u.name,
    #         SUM(o.total_price) AS depense_totale
    #     FROM users u
    #     INNER JOIN orders o ON u.id = o.user_id
    #     WHERE o.status != 'cancelled'
    #     GROUP BY u.id, u.name
    #     ORDER BY depense_totale DESC
    #     LIMIT 3
    # """
    rows = cur.execute(query_4d).fetchall()
    afficher_resultats("4d : Top 3 utilisateurs par dépense", rows)


# ============================================================
# FONCTION TESTER
# ============================================================

def tester():
    """
    Lance tous les exercices et vérifie les résultats avec les solutions.
    """
    print("\n" + "="*60)
    print("   JOUR 21 — SQL Fondamentaux")
    print("="*60)

    conn = creer_base_de_donnees()

    # Vérification de la base de données
    cur = conn.cursor()
    nb_users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    nb_products = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    nb_orders = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    print(f"\nBase de données créée : {nb_users} users, {nb_products} produits, {nb_orders} commandes")

    # Lancer les exercices
    exercice_1_select_basique(conn)
    exercice_2_where_avance(conn)
    exercice_3_join(conn)
    exercice_4_group_by(conn)

    # --- Tests automatiques avec les solutions ---
    print("\n" + "="*60)
    print("   VERIFICATION DES SOLUTIONS")
    print("="*60)

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
        "Utilisateurs actifs = 4",
        "SELECT COUNT(*) AS n FROM users WHERE is_active = 1",
        lambda rows: rows[0]["n"] == 4
    )

    verifier(
        "Electronics < 100€ : 3 produits",
        "SELECT COUNT(*) AS n FROM products WHERE category = 'Electronics' AND price < 100",
        lambda rows: rows[0]["n"] == 3
    )

    verifier(
        "Top 3 produits les plus chers",
        "SELECT name, price FROM products ORDER BY price DESC LIMIT 3",
        lambda rows: rows[0]["price"] == 1299.99 and len(rows) == 3
    )

    verifier(
        "Commandes completed ou shipped = 7",
        "SELECT COUNT(*) AS n FROM orders WHERE status IN ('completed', 'shipped')",
        lambda rows: rows[0]["n"] == 7
    )

    verifier(
        "Produit jamais commandé existe",
        """
        SELECT COUNT(*) AS n FROM products p
        LEFT JOIN orders o ON p.id = o.product_id
        WHERE o.id IS NULL
        """,
        lambda rows: rows[0]["n"] >= 1
    )

    verifier(
        "CA total toutes catégories > 0",
        """
        SELECT SUM(total_price) AS total FROM orders
        WHERE status != 'cancelled'
        """,
        lambda rows: rows[0]["total"] > 0
    )

    verifier(
        "Alice a le plus de commandes (3)",
        """
        SELECT u.name, COUNT(o.id) AS n
        FROM users u JOIN orders o ON u.id = o.user_id
        GROUP BY u.id ORDER BY n DESC LIMIT 1
        """,
        lambda rows: rows[0]["name"] == "Alice Martin" and rows[0]["n"] == 3
    )

    print(f"\n  Résultat : {tests_passes}/{tests_total} tests passés")
    conn.close()


if __name__ == "__main__":
    tester()
