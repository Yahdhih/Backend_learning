"""
Exercice Jour 07 — Générateurs et Context Managers

Complète les fonctions ci-dessous.
Lance : python3 exercice.py
"""

import time
from contextlib import contextmanager


# ─── EXERCICE 1 : Générateurs de base ───────────────────────────────────────

def fibonacci():
    """
    Générateur infini de la suite de Fibonacci.
    0, 1, 1, 2, 3, 5, 8, 13, 21, ...

    Usage :
        gen = fibonacci()
        next(gen)   # 0
        next(gen)   # 1
        next(gen)   # 1
        next(gen)   # 2
    """
    # TODO : utilise deux variables a, b et boucle infinie
    pass


def prendre(generateur, n):
    """
    Prend les n premiers éléments d'un générateur.
    Retourne une liste.

    >>> prendre(fibonacci(), 7)
    [0, 1, 1, 2, 3, 5, 8]
    """
    # TODO : utilise une list comprehension ou une boucle
    pass


def nombres_pairs_depuis(debut):
    """
    Générateur infini de nombres pairs à partir de 'debut'.
    Si debut est impair, commence au pair suivant.

    >>> list(prendre(nombres_pairs_depuis(3), 5))
    [4, 6, 8, 10, 12]
    """
    # TODO
    pass


# ─── EXERCICE 2 : Pipeline de données ───────────────────────────────────────

LOGS = [
    "INFO  2026-06-27 démarrage du serveur",
    "DEBUG 2026-06-27 connexion établie",
    "ERROR 2026-06-27 base de données inaccessible",
    "INFO  2026-06-27 retry en cours",
    "ERROR 2026-06-27 timeout après 3 essais",
    "INFO  2026-06-27 connexion rétablie",
    "DEBUG 2026-06-27 requête reçue",
]


def filtrer_niveau(logs, niveau):
    """
    Générateur qui filtre les logs par niveau (INFO, ERROR, DEBUG).

    >>> list(filtrer_niveau(LOGS, "ERROR"))
    ["ERROR 2026-06-27 base de données inaccessible", "ERROR 2026-06-27 timeout..."]
    """
    # TODO : yield uniquement les lignes qui commencent par niveau
    pass


def parser_log(logs):
    """
    Générateur qui transforme chaque ligne en dict.

    "ERROR 2026-06-27 message" → {"niveau": "ERROR", "date": "2026-06-27", "message": "message"}
    """
    # TODO : split chaque ligne et yield un dict
    pass


# ─── EXERCICE 3 : Context Managers ──────────────────────────────────────────

@contextmanager
def chronometre(label):
    """
    Context manager qui mesure et affiche la durée d'exécution.

    Usage :
        with chronometre("traitement"):
            time.sleep(0.1)
        # Affiche : "traitement : 0.100s"
    """
    # TODO :
    # - noter l'heure de début
    # - yield
    # - calculer et afficher la durée
    pass


@contextmanager
def attraper(exception_type, message_par_defaut="Erreur"):
    """
    Context manager qui attrape une exception et affiche un message.
    Le programme continue après.

    Usage :
        with attraper(ValueError, "Valeur invalide"):
            int("pas un nombre")
        print("Le programme continue")
        # Affiche :
        # Valeur invalide: invalid literal for int() with base 10: 'pas un nombre'
        # Le programme continue
    """
    # TODO : try/except autour du yield
    pass


class GestionnaireFichier:
    """
    Context manager qui ouvre un fichier et garantit sa fermeture.
    Implémente __enter__ et __exit__.

    Usage :
        with GestionnaireFichier("test.txt", "w") as f:
            f.write("bonjour")
        # Le fichier est automatiquement fermé après le with
    """

    def __init__(self, chemin, mode="r"):
        self.chemin = chemin
        self.mode = mode
        self._fichier = None

    def __enter__(self):
        # TODO : ouvrir le fichier et le retourner
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO : fermer le fichier
        # Retourner False (ne pas supprimer les exceptions)
        pass


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    erreurs = 0

    def ok(nom):
        print(f"  OK    {nom}")

    def echec(nom, msg):
        nonlocal erreurs
        erreurs += 1
        print(f"  ECHEC {nom}: {msg}")

    # Test fibonacci
    try:
        gen = fibonacci()
        resultat = [next(gen) for _ in range(8)]
        assert resultat == [0, 1, 1, 2, 3, 5, 8, 13], f"Obtenu {resultat}"
        ok("fibonacci")
    except Exception as e:
        echec("fibonacci", str(e))

    # Test prendre
    try:
        assert prendre(fibonacci(), 5) == [0, 1, 1, 2, 3]
        ok("prendre")
    except Exception as e:
        echec("prendre", str(e))

    # Test nombres_pairs_depuis
    try:
        resultat = prendre(nombres_pairs_depuis(3), 4)
        assert resultat == [4, 6, 8, 10], f"Obtenu {resultat}"
        ok("nombres_pairs_depuis")
    except Exception as e:
        echec("nombres_pairs_depuis", str(e))

    # Test filtrer_niveau
    try:
        erreurs_log = list(filtrer_niveau(LOGS, "ERROR"))
        assert len(erreurs_log) == 2
        assert all(l.startswith("ERROR") for l in erreurs_log)
        ok("filtrer_niveau")
    except Exception as e:
        echec("filtrer_niveau", str(e))

    # Test parser_log
    try:
        parsed = list(parser_log(LOGS[:2]))
        assert parsed[0]["niveau"] == "INFO"
        assert "démarrage" in parsed[0]["message"]
        ok("parser_log")
    except Exception as e:
        echec("parser_log", str(e))

    # Test chronometre
    try:
        print("\n  Test chronometre :")
        with chronometre("pause"):
            time.sleep(0.05)
        ok("chronometre")
    except Exception as e:
        echec("chronometre", str(e))

    # Test attraper
    try:
        print("\n  Test attraper :")
        with attraper(ValueError, "Valeur invalide"):
            int("pas un nombre")
        ok("attraper")
    except Exception as e:
        echec("attraper", str(e))

    # Test GestionnaireFichier
    try:
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp:
            chemin = tmp.name
        with GestionnaireFichier(chemin, "w") as f:
            f.write("test")
        with GestionnaireFichier(chemin, "r") as f:
            contenu = f.read()
        os.unlink(chemin)
        assert contenu == "test"
        ok("GestionnaireFichier")
    except Exception as e:
        echec("GestionnaireFichier", str(e))

    print()
    if erreurs == 0:
        print("Tous les tests passent !")
    else:
        print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
