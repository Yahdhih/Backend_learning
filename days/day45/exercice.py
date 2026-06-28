"""
Exercice Jour 45 — XSS et SQL Injection : attaques et défenses

Lance : python3 exercice.py
"""

import sqlite3
from django.utils.html import escape


# ─── PARTIE 1 : SQL Injection ────────────────────────────────────────────────

# Setup DB
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()
cursor.executescript("""
    CREATE TABLE utilisateurs (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT);
    INSERT INTO utilisateurs VALUES (1, 'alice', 'alice123', 'user');
    INSERT INTO utilisateurs VALUES (2, 'bob', 'bob123', 'user');
    INSERT INTO utilisateurs VALUES (3, 'admin', 'supersecret', 'admin');

    CREATE TABLE articles (id INTEGER PRIMARY KEY, titre TEXT, contenu TEXT, auteur_id INTEGER);
    INSERT INTO articles VALUES (1, 'Article public', 'Contenu public', 1);
    INSERT INTO articles VALUES (2, 'Article confidentiel', 'DONNÉES SECRÈTES', 3);
""")
conn.commit()


def login_vulnerable(username: str, password: str) -> dict | None:
    """
    Login VULNÉRABLE à l'injection SQL.
    Ne change pas cette fonction — elle sert à démontrer l'attaque.
    """
    query = f"SELECT * FROM utilisateurs WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    row = cursor.fetchone()
    if row:
        return {"id": row[0], "username": row[1], "role": row[3]}
    return None


def login_securise(username: str, password: str) -> dict | None:
    """
    Login sécurisé avec requête paramétrée.

    TODO : même logique que login_vulnerable mais avec des paramètres
    (pas de concaténation de strings SQL)
    """
    # TODO : cursor.execute("SELECT ... WHERE username = ? AND password = ?", (username, password))
    pass


def rechercher_articles_vulnerable(terme: str) -> list:
    """Recherche VULNÉRABLE."""
    query = f"SELECT titre, contenu FROM articles WHERE titre LIKE '%{terme}%'"
    cursor.execute(query)
    return cursor.fetchall()


def rechercher_articles_securise(terme: str) -> list:
    """
    Recherche sécurisée.
    TODO : même chose mais avec paramètre ? (pas de concaténation)
    Le LIKE avec paramètre : cursor.execute("... LIKE ?", [f"%{terme}%"])
    """
    # TODO
    pass


# ─── PARTIE 2 : XSS ──────────────────────────────────────────────────────────

def generer_page_vulnerable(commentaires: list) -> str:
    """Génère une page HTML VULNÉRABLE au XSS."""
    items = ""
    for c in commentaires:
        items += f"<li>{c}</li>"   # pas d'échappement !
    return f"<html><body><ul>{items}</ul></body></html>"


def generer_page_securisee(commentaires: list) -> str:
    """
    Génère une page HTML protégée contre XSS.
    TODO : utilise escape() de Django pour chaque commentaire
    """
    items = ""
    for c in commentaires:
        # TODO : c_safe = escape(c)
        items += f"<li>{c}</li>"  # TODO : utiliser c_safe
    return f"<html><body><ul>{items}</ul></body></html>"


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    erreurs = 0
    def ok(n): print(f"  OK    {n}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    print("=== SQL Injection ===\n")

    # Démonstration attaque
    print("-- Login vulnérable --")
    # Login normal
    user = login_vulnerable("alice", "alice123")
    print(f"  Login normal (alice) : {user}")

    # Bypass auth
    user_bypass = login_vulnerable("admin' --", "n'importe_quoi")
    print(f"  Bypass auth (admin' --) : {user_bypass}")
    if user_bypass and user_bypass["username"] == "admin":
        print("  DANGER : authentification contournée !")

    # UNION attack — voir données d'autres tables
    payload = "x' UNION SELECT id, username, password, role FROM utilisateurs --"
    try:
        resultats = rechercher_articles_vulnerable(payload)
        print(f"\n  UNION attack sur recherche :")
        for r in resultats:
            print(f"    {r}")
        if len(resultats) > 0:
            print("  DANGER : données volées via UNION !")
    except Exception as e:
        print(f"  Erreur UNION : {e}")

    print("\n-- Login sécurisé --")
    try:
        user_sec = login_securise("alice", "alice123")
        assert user_sec is not None and user_sec["username"] == "alice"
        ok("Login sécurisé — alice valide")
    except Exception as e: echec("login sécurisé valide", e)

    try:
        bypass = login_securise("admin' --", "n'importe")
        assert bypass is None, "La requête paramétrée ne doit pas bypasser l'auth"
        ok("Login sécurisé — bypass impossible")
    except Exception as e: echec("login sécurisé bypass", e)

    try:
        resultats = rechercher_articles_securise("article")
        assert resultats is not None
        union_attack = rechercher_articles_securise("x' UNION SELECT 1,2 --")
        # Avec requête paramétrée, le ' est traité comme caractère littéral
        ok("Recherche sécurisée — pas d'injection")
    except Exception as e: echec("recherche sécurisée", e)

    print("\n=== XSS ===\n")

    commentaires = [
        "Super article !",
        "<script>document.cookie = 'volé'</script>",
        "<img src=x onerror=alert('XSS')>",
        "Commentaire <b>normal</b>",
    ]

    page_vuln = generer_page_vulnerable(commentaires)
    print("-- Page vulnérable (vérifier que <script> n'est PAS échappé) --")
    for ligne in page_vuln.split("\n"):
        if "script" in ligne.lower() or "onerror" in ligne.lower():
            print(f"  DANGER : {ligne.strip()}")

    try:
        page_safe = generer_page_securisee(commentaires)
        assert "<script>" not in page_safe, "Les <script> doivent être échappés"
        assert "&lt;script&gt;" in page_safe or "script" not in page_safe
        ok("Page sécurisée — <script> échappé en &lt;script&gt;")
    except Exception as e: echec("XSS protection", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
