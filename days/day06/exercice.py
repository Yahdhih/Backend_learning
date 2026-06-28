"""
Exercice Jour 06 — Classes et OOP Python

Implémente les classes ci-dessous selon les spécifications.
Lance : python3 exercice.py
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ─── EXERCICE 1 : Classe Pile (Stack) ────────────────────────────────────────
#
# Implémente une pile LIFO avec les opérations classiques.
# Une pile = comme une pile d'assiettes : on empile et on dépile par le dessus.

class Pile:
    """
    Pile LIFO (Last In, First Out).

    Usage :
        p = Pile()
        p.empiler(1)
        p.empiler(2)
        p.depiler()   # → 2
        len(p)        # → 1
        bool(p)       # → True (non vide)
    """

    def __init__(self):
        # TODO : initialise le stockage interne (utilise une liste)
        pass

    def empiler(self, valeur):
        """Ajoute un élément au sommet de la pile."""
        # TODO
        pass

    def depiler(self):
        """Retire et retourne le sommet. Lève IndexError si vide."""
        # TODO
        pass

    def sommet(self):
        """Retourne le sommet sans le retirer. Lève IndexError si vide."""
        # TODO
        pass

    def __len__(self):
        """Nombre d'éléments dans la pile."""
        # TODO
        pass

    def __bool__(self):
        """True si la pile n'est pas vide."""
        # TODO
        pass

    def __repr__(self):
        # TODO : ex: "Pile([1, 2, 3])"
        pass


# ─── EXERCICE 2 : Classe Compte bancaire ─────────────────────────────────────

class CompteBancaire:
    """
    Compte bancaire avec historique des transactions.

    Usage :
        c = CompteBancaire("Alice", solde_initial=100)
        c.deposer(50)           # solde = 150
        c.retirer(30)           # solde = 120
        c.retirer(200)          # lève ValueError (fonds insuffisants)
        print(c.solde)          # 120
        print(c.historique)     # [("dépôt", 100), ("dépôt", 50), ("retrait", 30)]
    """

    def __init__(self, proprietaire: str, solde_initial: float = 0):
        # TODO
        # self.proprietaire, self._solde, self._historique
        pass

    @property
    def solde(self) -> float:
        # TODO
        pass

    @property
    def historique(self) -> list:
        # TODO : retourner une copie (pas la liste interne directement)
        pass

    def deposer(self, montant: float):
        """Ajoute montant au solde. Lève ValueError si montant <= 0."""
        # TODO
        pass

    def retirer(self, montant: float):
        """Retire montant du solde. Lève ValueError si insuffisant ou montant <= 0."""
        # TODO
        pass

    def __repr__(self):
        return f"CompteBancaire(proprietaire={self.proprietaire!r}, solde={self.solde})"


# ─── EXERCICE 3 : Classe Vecteur2D ───────────────────────────────────────────
#
# Implémente un vecteur 2D avec les opérations mathématiques.

class Vecteur2D:
    """
    Vecteur à 2 dimensions.

    Usage :
        v1 = Vecteur2D(1, 2)
        v2 = Vecteur2D(3, 4)
        v1 + v2      # Vecteur2D(4, 6)
        v1 * 3       # Vecteur2D(3, 6)
        abs(v2)      # 5.0 (norme euclidienne)
        v1 == v1     # True
        list(v1)     # [1, 2]
    """

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Vecteur2D({self.x}, {self.y})"

    def __add__(self, autre: "Vecteur2D") -> "Vecteur2D":
        # TODO
        pass

    def __sub__(self, autre: "Vecteur2D") -> "Vecteur2D":
        # TODO
        pass

    def __mul__(self, scalaire: float) -> "Vecteur2D":
        # TODO : multiplication par un scalaire (nombre)
        pass

    def __eq__(self, autre) -> bool:
        # TODO
        pass

    def __abs__(self) -> float:
        """Norme euclidienne : sqrt(x² + y²)"""
        # TODO
        pass

    def __iter__(self):
        """Permet : x, y = vecteur ou list(vecteur)"""
        # TODO : yield x puis y
        pass

    def __bool__(self) -> bool:
        """False seulement si les deux composantes sont nulles."""
        # TODO
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

    # Tests Pile
    try:
        p = Pile()
        assert len(p) == 0
        assert not bool(p)
        p.empiler(1); p.empiler(2); p.empiler(3)
        assert len(p) == 3
        assert bool(p)
        assert p.sommet() == 3
        assert p.depiler() == 3
        assert p.depiler() == 2
        assert len(p) == 1
        ok("Pile")
    except Exception as e:
        echec("Pile", str(e))

    # Tests CompteBancaire
    try:
        c = CompteBancaire("Alice", 100)
        assert c.solde == 100
        c.deposer(50)
        assert c.solde == 150
        c.retirer(30)
        assert c.solde == 120
        try:
            c.retirer(500)
            echec("CompteBancaire", "Devrait lever ValueError")
        except ValueError:
            pass
        assert len(c.historique) == 3   # depot init + depot + retrait
        ok("CompteBancaire")
    except Exception as e:
        echec("CompteBancaire", str(e))

    # Tests Vecteur2D
    try:
        v1 = Vecteur2D(1, 2)
        v2 = Vecteur2D(3, 4)
        assert v1 + v2 == Vecteur2D(4, 6)
        assert v1 - v2 == Vecteur2D(-2, -2)
        assert v1 * 3 == Vecteur2D(3, 6)
        assert abs(v2) == 5.0
        assert list(v1) == [1, 2]
        assert bool(v1)
        assert not bool(Vecteur2D(0, 0))
        ok("Vecteur2D")
    except Exception as e:
        echec("Vecteur2D", str(e))

    print()
    if erreurs == 0:
        print("Tous les tests passent !")
    else:
        print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
