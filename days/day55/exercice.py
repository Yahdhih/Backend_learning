"""
Exercice Jour 55 — Stratégies de cache et invalidation

Lance : python3 exercice.py
"""

import time
import threading
from typing import Any, Optional, Callable


# Simule une base de données lente
DB = {
    "article:1": {"id": 1, "titre": "Python avancé", "vues": 100},
    "article:2": {"id": 2, "titre": "Django REST", "vues": 50},
    "article:3": {"id": 3, "titre": "Bases de données", "vues": 200},
}

def db_lire(cle: str) -> Optional[dict]:
    """Simule une requête DB lente (50ms)."""
    time.sleep(0.05)
    return DB.get(cle)

def db_ecrire(cle: str, valeur: dict):
    """Simule une écriture DB."""
    time.sleep(0.02)
    DB[cle] = valeur


# ─── EXERCICE 1 : Cache-Aside ────────────────────────────────────────────────

class CacheSimple:
    """Cache en mémoire simple avec TTL."""

    def __init__(self):
        self._store = {}  # {clé: (valeur, expiration)}

    def get(self, cle: str) -> Optional[Any]:
        """Retourne la valeur ou None si absente/expirée."""
        if cle not in self._store:
            return None
        valeur, expiration = self._store[cle]
        if time.time() > expiration:
            del self._store[cle]
            return None
        return valeur

    def set(self, cle: str, valeur: Any, ttl: int = 60):
        """Stocke une valeur avec TTL en secondes."""
        self._store[cle] = (valeur, time.time() + ttl)

    def delete(self, cle: str):
        self._store.pop(cle, None)

    def clear(self):
        self._store.clear()

    @property
    def taille(self) -> int:
        return len(self._store)


cache = CacheSimple()


def lire_article_cache_aside(article_id: int) -> Optional[dict]:
    """
    Pattern cache-aside :
    1. Chercher dans le cache
    2. Si trouvé → retourner (cache hit)
    3. Si non trouvé → lire en DB, mettre en cache, retourner

    TODO : implémenter ce pattern
    """
    cle = f"article:{article_id}"
    # TODO
    pass


def mettre_a_jour_article(article_id: int, nouveau_titre: str):
    """
    Mise à jour avec invalidation du cache.
    1. Écrire en DB
    2. Invalider le cache (delete, pas update)

    TODO : implémenter
    """
    cle = f"article:{article_id}"
    # TODO : db_ecrire + cache.delete
    pass


# ─── EXERCICE 2 : Cache Stampede ─────────────────────────────────────────────

appels_db = {"count": 0}  # compteur pour mesurer


def lire_avec_stampede(article_id: int) -> dict:
    """
    Version SANS protection contre le stampede.
    Si 10 requêtes arrivent simultanément quand le cache est vide,
    toutes vont en DB en même temps.
    """
    cle = f"article:{article_id}"
    valeur = cache.get(cle)
    if valeur is None:
        appels_db["count"] += 1
        valeur = db_lire(cle)
        cache.set(cle, valeur, ttl=1)  # TTL court pour le test
    return valeur


_locks = {}

def lire_avec_mutex(article_id: int) -> dict:
    """
    Version avec mutex pour éviter le stampede.
    Un seul thread va en DB, les autres attendent et lisent depuis le cache.

    TODO :
    1. Vérifier le cache d'abord
    2. Si absent, acquérir un lock (threading.Lock) pour cet article_id
    3. Re-vérifier le cache sous le lock (double-checked locking)
    4. Si toujours absent : aller en DB + mettre en cache
    5. Libérer le lock
    """
    cle = f"article:{article_id}"
    # TODO
    pass


# ─── EXERCICE 3 : Versioning du cache ────────────────────────────────────────

class CacheVersionne:
    """
    Cache avec versioning global.
    Incrémenter la version invalide TOUTES les entrées d'un coup.
    Utile pour les déploiements : incrementer la version = vider le cache.
    """

    def __init__(self):
        self._store = {}
        self._version = 1

    def _cle_avec_version(self, cle: str) -> str:
        """Préfixe la clé avec la version actuelle."""
        # TODO : retourner f"v{self._version}:{cle}"
        pass

    def get(self, cle: str) -> Optional[Any]:
        """Cherche avec la version actuelle."""
        # TODO
        pass

    def set(self, cle: str, valeur: Any):
        """Stocke avec la version actuelle."""
        # TODO
        pass

    def invalider_tout(self):
        """Incrémente la version → toutes les entrées deviennent inaccessibles."""
        # TODO : self._version += 1
        pass


# ─── EXERCICE 4 : Calculer le hit rate ───────────────────────────────────────

class CacheAvecStats(CacheSimple):
    """Cache qui suit ses statistiques."""

    def __init__(self):
        super().__init__()
        self._hits = 0
        self._misses = 0

    def get(self, cle: str) -> Optional[Any]:
        valeur = super().get(cle)
        if valeur is not None:
            self._hits += 1
        else:
            self._misses += 1
        return valeur

    @property
    def hit_rate(self) -> float:
        """Pourcentage de cache hits (0.0 à 1.0)."""
        total = self._hits + self._misses
        # TODO : retourner hits/total ou 0 si total == 0
        pass

    @property
    def stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self.hit_rate:.1%}",
            "total": self._hits + self._misses,
        }


# ─── TESTS ───────────────────────────────────────────────────────────────────

def tester():
    erreurs = 0
    def ok(n, extra=""): print(f"  OK    {n}{' (' + extra + ')' if extra else ''}")
    def echec(n, m): nonlocal erreurs; erreurs += 1; print(f"  ECHEC {n}: {m}")

    print("=== Cache-Aside ===")
    cache.clear()
    try:
        debut = time.time()
        art = lire_article_cache_aside(1)
        t1 = time.time() - debut  # lent (DB)
        assert art is not None and art["id"] == 1

        debut = time.time()
        art2 = lire_article_cache_aside(1)
        t2 = time.time() - debut  # rapide (cache)
        assert art2["id"] == 1

        assert t2 < t1 / 2, f"Le cache doit être plus rapide : {t1:.3f}s vs {t2:.3f}s"
        ok("Cache-Aside", f"DB:{t1*1000:.0f}ms, Cache:{t2*1000:.0f}ms")
    except Exception as e: echec("cache-aside", e)

    print("\n=== Invalidation ===")
    try:
        lire_article_cache_aside(2)  # met en cache
        assert cache.get("article:2") is not None

        mettre_a_jour_article(2, "Django REST Framework")
        assert cache.get("article:2") is None, "Le cache doit être invalidé"
        art = lire_article_cache_aside(2)   # relit depuis DB
        assert art["titre"] == "Django REST Framework"
        ok("Invalidation après update")
    except Exception as e: echec("invalidation", e)

    print("\n=== Cache Stampede (simulation) ===")
    try:
        cache.clear()
        appels_db["count"] = 0

        # Simuler 5 threads simultanés sans protection
        threads = [threading.Thread(target=lire_avec_stampede, args=(1,)) for _ in range(5)]
        [t.start() for t in threads]
        [t.join() for t in threads]

        print(f"  Sans mutex : {appels_db['count']} appels DB pour 5 requêtes simultanées")

        if lire_avec_mutex(1) is not None:
            cache.clear()
            appels_db["count"] = 0
            threads = [threading.Thread(target=lire_avec_mutex, args=(1,)) for _ in range(5)]
            [t.start() for t in threads]
            [t.join() for t in threads]
            print(f"  Avec mutex : {appels_db['count']} appels DB pour 5 requêtes simultanées")
            ok("Mutex réduit le stampede")
    except Exception as e: echec("stampede", e)

    print("\n=== Versioning ===")
    try:
        cv = CacheVersionne()
        cv.set("article:1", {"id": 1})
        assert cv.get("article:1") is not None
        cv.invalider_tout()
        assert cv.get("article:1") is None, "Tout doit être invalidé"
        ok("Versioning du cache")
    except Exception as e: echec("versioning", e)

    print("\n=== Hit Rate ===")
    try:
        cs = CacheAvecStats()
        cs.set("x", 42)
        cs.get("x")   # hit
        cs.get("x")   # hit
        cs.get("y")   # miss
        cs.get("z")   # miss
        assert cs.hit_rate == 0.5
        ok("Hit rate", str(cs.stats))
    except Exception as e: echec("hit rate", e)

    print()
    if erreurs == 0: print("Tous les tests passent !")
    else: print(f"{erreurs} test(s) échoué(s).")


if __name__ == "__main__":
    tester()
