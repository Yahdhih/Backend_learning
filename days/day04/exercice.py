"""
Exercice Jour 04 — Python : types, fonctions, comprehensions

Complète chaque fonction. Ne change pas les signatures.
Lance : python3 exercice.py
Si tout est correct, tu vois "Tous les tests passent !"
"""


# ─── PARTIE 1 : Manipulation de collections ─────────────────────────────────

def filtrer_positifs(nombres):
    """
    Retourne une liste contenant uniquement les nombres positifs (> 0).
    Utilise une list comprehension.

    >>> filtrer_positifs([1, -2, 3, -4, 5])
    [1, 3, 5]
    >>> filtrer_positifs([-1, -2, -3])
    []
    """
    # TODO : une list comprehension ici
    return [i for i in nombres if i > 0]
    pass


def carres_pairs(n):
    """
    Retourne les carrés de tous les nombres pairs de 1 à n (inclus).
    Utilise une list comprehension.

    >>> carres_pairs(10)
    [4, 16, 36, 64, 100]
    """
    # TODO
    return [i**2 for i in range(1,n+1) if i%2 == 0]
    pass


def construire_index(utilisateurs):
    """
    Reçoit une liste de dicts {"id": ..., "nom": ...}
    Retourne un dict {id: nom}.
    Utilise une dict comprehension.

    >>> construire_index([{"id": 1, "nom": "Alice"}, {"id": 2, "nom": "Bob"}])
    {1: 'Alice', 2: 'Bob'}
    """
    # TODO
    dictionnaire = {}
    for i in utilisateurs : 
        a = i["id"]
        dictionnaire[a] = i["nom"]
    return dictionnaire
    pass


# ─── PARTIE 2 : Fonctions avec *args et **kwargs ────────────────────────────

def moyenne(*nombres):
    """
    Calcule la moyenne d'un nombre quelconque d'arguments.

    >>> moyenne(10, 20, 30)
    20.0
    >>> moyenne(5)
    5.0
    """
    # TODO 
    return sum(nombres) / len(nombres)

    pass


def construire_url(base, **params):
    """
    Construit une URL avec des query parameters.
    Les paramètres sont triés alphabétiquement.

    >>> construire_url("https://api.com/users", page=2, limit=10)
    'https://api.com/users?limit=10&page=2'
    >>> construire_url("https://api.com/users")
    'https://api.com/users'
    """
    # TODO : si pas de params, retourner base seul
    # sinon, construire "base?key1=val1&key2=val2" (trié par clé)
    pass


# ─── PARTIE 3 : Manipulation de chaînes ─────────────────────────────────────

def compter_mots(phrase):
    """
    Retourne un dict {mot: nombre_occurrences}.
    Les mots sont en minuscules. Ignore la ponctuation.

    >>> compter_mots("le chat et le chien")
    {'le': 2, 'chat': 1, 'et': 1, 'chien': 1}
    """
    # TODO : split la phrase, convertir en minuscules, compter avec un dict
    pass


def inverser_dict(d):
    """
    Inverse les clés et valeurs d'un dict.

    >>> inverser_dict({"a": 1, "b": 2, "c": 3})
    {1: 'a', 2: 'b', 3: 'c'}
    """
    # TODO : dict comprehension
    pass


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    erreurs = 0

    def verifier(nom, resultat, attendu):
        nonlocal erreurs
        if resultat != attendu:
            print(f"  ECHEC {nom}: obtenu {resultat!r}, attendu {attendu!r}")
            erreurs += 1
        else:
            print(f"  OK    {nom}")

    verifier("filtrer_positifs", filtrer_positifs([1, -2, 3, -4, 5]), [1, 3, 5])
    verifier("filtrer_positifs vide", filtrer_positifs([-1, -2]), [])
    verifier("carres_pairs", carres_pairs(10), [4, 16, 36, 64, 100])
    verifier("construire_index", construire_index([{"id": 1, "nom": "Alice"}, {"id": 2, "nom": "Bob"}]), {1: "Alice", 2: "Bob"})
    verifier("moyenne", moyenne(10, 20, 30), 20.0)
    verifier("moyenne seul", moyenne(5), 5.0)
    verifier("construire_url avec params", construire_url("https://api.com/users", page=2, limit=10), "https://api.com/users?limit=10&page=2")
    verifier("construire_url sans params", construire_url("https://api.com/users"), "https://api.com/users")
    verifier("compter_mots", compter_mots("le chat et le chien"), {"le": 2, "chat": 1, "et": 1, "chien": 1})
    verifier("inverser_dict", inverser_dict({"a": 1, "b": 2}), {1: "a", 2: "b"})

    print()
    if erreurs == 0:
        print("Tous les tests passent !")
    else:
        print(f"{erreurs} test(s) échoué(s). Continue !")


if __name__ == "__main__":
    tester()
