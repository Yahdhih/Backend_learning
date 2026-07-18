"""
Exercice Jour 05 — Décorateurs Python

Complète les décorateurs ci-dessous.
Lance : python3 exercice.py
"""

import time
from functools import wraps


# ─── EXERCICE 1 : Décorateur timer ──────────────────────────────────────────
#
# Crée un décorateur @timer qui mesure et affiche le temps d'exécution.
#
# Utilisation attendue :
#   @timer
#   def calcul_lent():
#       time.sleep(0.1)
#       return 42
#
#   calcul_lent()
#   # Affiche : "calcul_lent a pris 0.100s"

def timer(func):
    @wraps(func)
    def wrapper(*arg, **kwrags):
        debut = time.time()
        resultat = func(*arg,**kwrags)
        fin = time.time()
        elapsed = fin - debut
        print(f"{func.__name__} a pris {elapsed:.3f}s")
        return resultat
    return wrapper
    # TODO : implémente le décorateur
    # Utilise time.time() avant et après l'appel
    # Affiche : f"{func.__name__} a pris {elapsed:.3f}s"
    pass


# ─── EXERCICE 2 : Décorateur logger ─────────────────────────────────────────
#
# Crée un décorateur @logger qui affiche les arguments et le résultat.
#
# Utilisation attendue :
#   @logger
#   def additionner(a, b):
#       return a + b
#
#   additionner(3, 4)
#   # Affiche :
#   # → additionner(3, 4)
#   # ← 7

def logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        args_str = ", ".join([str(a) for a in args])
        print(f"→ {func.__name__}({args_str})")
        resultat = func(*args, **kwargs)
        print(f"← {resultat}")
        return resultat
    return wrapper

    # TODO
    # Affiche "→ nom(args, kwargs)" avant l'appel
    # Affiche "← résultat" après l'appel
    pass


# ─── EXERCICE 3 : Décorateur retry avec argument ────────────────────────────
#
# Crée un décorateur @retry(n) qui réessaie n fois si une exception est levée.
#
# Utilisation attendue :
#   @retry(3)
#   def fonction_instable():
#       ...
#
# Si la fonction réussit : retourner le résultat normalement
# Si elle échoue n fois : laisser la dernière exception se propager

def retry(n):
    def decorateur(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            derniere_exception = None
            for tentative in range(n):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    derniere_exception = e
            raise derniere_exception
        return wrapper
    return decorateur
  
    # TODO : 3 couches (argument → decorateur → wrapper)
    pass


# ─── EXERCICE 4 : Décorateur memoize ────────────────────────────────────────
#
# Crée un décorateur @memoize qui met en cache les résultats.
# Si la fonction est appelée avec les mêmes arguments, retourner le cache.
#
# Utilisation :
#   @memoize
#   def fibonacci(n):
#       if n <= 1: return n
#       return fibonacci(n-1) + fibonacci(n-2)
#
#   fibonacci(10)  # calcule
#   fibonacci(10)  # retourne depuis le cache (rapide)

def memoize(func):
    # TODO : utilise un dict comme cache
    # La clé = args (les arguments de la fonction)
    pass


# ─── EXERCICE 5 : Décorateur validate_types ─────────────────────────────────
#
# Crée un décorateur @validate_types qui vérifie les types des arguments
# basé sur les annotations de type.
#
# Utilisation :
#   @validate_types
#   def additionner(a: int, b: int) -> int:
#       return a + b
#
#   additionner(1, 2)     # OK → 3
#   additionner("a", 2)   # lève TypeError: argument 'a' doit être int

def validate_types(func):
    # TODO : utilise func.__annotations__ pour obtenir les types attendus
    # inspect.signature(func).parameters pour les noms des arguments
    import inspect
    pass


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    print("=== Test timer ===")
    if timer is not None and not isinstance(timer(lambda: None), type(None)):
        @timer
        def lent():
            time.sleep(0.05)
            return 42
        resultat = lent()
        assert resultat == 42, "timer doit retourner le résultat de la fonction"
        print("  OK")
    else:
        print("  À implémenter")

    print("\n=== Test logger ===")
    if logger is not None:
        @logger
        def additionner(a, b):
            return a + b
        r = additionner(3, 4)
        assert r == 7
        print("  OK (vérifie l'affichage ci-dessus)")

    print("\n=== Test retry ===")
    if retry is not None:
        compteur = {"essais": 0}
        @retry(3)
        def echoue_2_fois():
            compteur["essais"] += 1
            if compteur["essais"] < 3:
                raise ValueError("Échec temporaire")
            return "succès"
        r = echoue_2_fois()
        assert r == "succès", f"Attendu 'succès', obtenu {r!r}"
        assert compteur["essais"] == 3
        print("  OK")

    print("\n=== Test memoize ===")
    if memoize is not None:
        appels = {"n": 0}
        @memoize
        def fib(n):
            appels["n"] += 1
            if n <= 1:
                return n
            return fib(n - 1) + fib(n - 2)
        r = fib(10)
        assert r == 55, f"fib(10) doit être 55, obtenu {r}"
        print(f"  OK — fib(10)={r}, appels={appels['n']} (sans memoize: 177)")

    print("\nFini ! Vérifie les résultats ci-dessus.")


if __name__ == "__main__":
    tester()
