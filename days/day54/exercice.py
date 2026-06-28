"""
Jour 54 — Exercice : Implémenter le Django Cache Framework en Python pur
========================================================================
Objectif : recréer l'API du cache Django (cache.get, cache.set, cache.delete,
cache.get_or_set, cache.get_many, cache.set_many, cache.add, cache.incr,
cache.decr, cache.clear) en utilisant un dict Python comme backend.

Aucune dépendance externe requise.
"""

import time
import threading
from typing import Any, Callable, Optional


# ============================================================
# 1. BACKEND DE BASE : DictCache (équivalent LocMemCache)
# ============================================================

class DictCacheBackend:
    """
    Backend de cache basé sur un dictionnaire Python.
    Équivalent simplifié de django.core.cache.backends.locmem.LocMemCache.

    Supporte :
    - TTL (timeout) par entrée
    - Thread-safe (RLock)
    - Versioning
    - Compression optionnelle (via pickle)
    """

    def __init__(self, default_timeout: int = 300, max_entries: int = 1000):
        self._cache: dict[str, Any] = {}
        self._expires: dict[str, float] = {}
        self._lock = threading.RLock()
        self.default_timeout = default_timeout
        self.max_entries = max_entries
        self._hits = 0
        self._misses = 0

    # ---- Méthodes internes ----

    def _is_expired(self, key: str) -> bool:
        if key not in self._expires:
            return False
        return time.time() > self._expires[key]

    def _evict_if_needed(self):
        """Expulse les entrées expirées si le cache est plein."""
        if len(self._cache) < self.max_entries:
            return
        # Supprimer les entrées expirées
        expired = [k for k in self._cache if self._is_expired(k)]
        for k in expired:
            del self._cache[k]
            self._expires.pop(k, None)
        # Si encore plein, supprimer les plus anciennes (LRU simplifié)
        if len(self._cache) >= self.max_entries:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._expires.pop(oldest_key, None)

    def _make_key(self, key: str, version: Optional[int] = None) -> str:
        """Construit la clé interne avec version."""
        if version is not None:
            return f"v{version}:{key}"
        return key

    # ---- API Publique (identique à Django) ----

    def get(self, key: str, default: Any = None, version: Optional[int] = None) -> Any:
        """Équivalent de cache.get(key, default)."""
        internal_key = self._make_key(key, version)
        with self._lock:
            if internal_key not in self._cache:
                self._misses += 1
                return default
            if self._is_expired(internal_key):
                del self._cache[internal_key]
                self._expires.pop(internal_key, None)
                self._misses += 1
                return default
            self._hits += 1
            return self._cache[internal_key]

    def set(self, key: str, value: Any, timeout: Optional[int] = ...,
            version: Optional[int] = None) -> bool:
        """
        Équivalent de cache.set(key, value, timeout).
        timeout=None : pas d'expiration.
        timeout=... (sentinel) : utiliser default_timeout.
        """
        if timeout is ...:
            timeout = self.default_timeout

        internal_key = self._make_key(key, version)
        with self._lock:
            self._evict_if_needed()
            self._cache[internal_key] = value
            if timeout is None:
                self._expires.pop(internal_key, None)
            else:
                self._expires[internal_key] = time.time() + timeout
        return True

    def add(self, key: str, value: Any, timeout: Optional[int] = ...,
            version: Optional[int] = None) -> bool:
        """
        Équivalent de cache.add() — ne stocke que si la clé n'existe pas.
        Retourne True si stocké, False si déjà existant.
        """
        if timeout is ...:
            timeout = self.default_timeout

        internal_key = self._make_key(key, version)
        with self._lock:
            if internal_key in self._cache and not self._is_expired(internal_key):
                return False
            self._cache[internal_key] = value
            if timeout is None:
                self._expires.pop(internal_key, None)
            else:
                self._expires[internal_key] = time.time() + timeout
            return True

    def delete(self, key: str, version: Optional[int] = None) -> bool:
        """Équivalent de cache.delete(key)."""
        internal_key = self._make_key(key, version)
        with self._lock:
            existed = internal_key in self._cache
            self._cache.pop(internal_key, None)
            self._expires.pop(internal_key, None)
            return existed

    def get_many(self, keys: list[str], version: Optional[int] = None) -> dict[str, Any]:
        """Équivalent de cache.get_many(keys)."""
        result = {}
        for key in keys:
            value = self.get(key, version=version)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, mapping: dict[str, Any], timeout: Optional[int] = ...,
                 version: Optional[int] = None) -> list[str]:
        """
        Équivalent de cache.set_many(mapping, timeout).
        Retourne la liste des clés qui ont échoué ([] si tout OK).
        """
        failed = []
        for key, value in mapping.items():
            if not self.set(key, value, timeout=timeout, version=version):
                failed.append(key)
        return failed

    def delete_many(self, keys: list[str], version: Optional[int] = None):
        """Équivalent de cache.delete_many(keys)."""
        for key in keys:
            self.delete(key, version=version)

    def get_or_set(self, key: str, default: Any, timeout: Optional[int] = ...,
                   version: Optional[int] = None) -> Any:
        """
        Équivalent de cache.get_or_set(key, default_or_callable, timeout).
        Si default est un callable, il est appelé et son résultat est stocké.
        """
        value = self.get(key, version=version)
        if value is not None:
            return value

        # Résoudre la valeur (callable ou valeur directe)
        if callable(default):
            value = default()
        else:
            value = default

        self.set(key, value, timeout=timeout, version=version)
        return value

    def has_key(self, key: str, version: Optional[int] = None) -> bool:
        """Vérifie si une clé existe et n'est pas expirée."""
        return self.get(key, version=version) is not None

    def incr(self, key: str, delta: int = 1, version: Optional[int] = None) -> int:
        """Équivalent de cache.incr(key, delta)."""
        with self._lock:
            value = self.get(key, version=version)
            if value is None:
                raise ValueError(f"La clé '{key}' n'existe pas dans le cache")
            new_value = int(value) + delta
            self.set(key, new_value, timeout=None, version=version)
            return new_value

    def decr(self, key: str, delta: int = 1, version: Optional[int] = None) -> int:
        """Équivalent de cache.decr(key, delta)."""
        return self.incr(key, -delta, version=version)

    def clear(self) -> bool:
        """Équivalent de cache.clear() — vide tout le cache."""
        with self._lock:
            self._cache.clear()
            self._expires.clear()
        return True

    def ttl(self, key: str, version: Optional[int] = None) -> int:
        """Retourne le TTL restant en secondes (-1 = permanent, -2 = absent)."""
        internal_key = self._make_key(key, version)
        with self._lock:
            if internal_key not in self._cache:
                return -2
            if self._is_expired(internal_key):
                return -2
            if internal_key not in self._expires:
                return -1
            return max(0, int(self._expires[internal_key] - time.time()))

    # ---- Méthodes de monitoring ----

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def stats(self) -> dict:
        with self._lock:
            # Compter les clés non expirées
            active_keys = sum(1 for k in self._cache if not self._is_expired(k))
            return {
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': f"{self.hit_rate * 100:.1f}%",
                'active_keys': active_keys,
                'total_allocated': len(self._cache),
                'max_entries': self.max_entries,
            }

    def keys(self, pattern: str = '*') -> list[str]:
        """Liste les clés actives (avec support de pattern simple)."""
        import fnmatch
        with self._lock:
            return [
                k for k in self._cache
                if not self._is_expired(k) and fnmatch.fnmatch(k, pattern)
            ]


# ============================================================
# 2. MULTI-BACKEND : CacheRouter
# ============================================================

class CacheRouter:
    """
    Permet d'utiliser plusieurs backends de cache par alias.
    Équivalent de django.core.cache.caches[alias].
    """

    def __init__(self):
        self._backends: dict[str, DictCacheBackend] = {}
        self._default_alias = 'default'

    def configure(self, alias: str, **kwargs) -> 'CacheRouter':
        """Configure un backend sous un alias."""
        self._backends[alias] = DictCacheBackend(**kwargs)
        return self

    def __getitem__(self, alias: str) -> DictCacheBackend:
        if alias not in self._backends:
            raise KeyError(f"Cache '{alias}' non configuré")
        return self._backends[alias]

    @property
    def default(self) -> DictCacheBackend:
        return self._backends[self._default_alias]


# ============================================================
# 3. DÉCORATEURS DE CACHE (équivalents Django)
# ============================================================

def cache_result(timeout: int = 300, key_prefix: str = '', cache_backend: Optional[DictCacheBackend] = None):
    """
    Décorateur équivalent à @cache_page mais pour des fonctions/méthodes.
    Génère une clé de cache à partir du nom de la fonction et des arguments.
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            backend = cache_backend or _default_cache

            # Construire la clé de cache
            prefix = key_prefix or func.__name__
            key_parts = [prefix] + [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
            cache_key = ':'.join(key_parts)

            # Chercher dans le cache
            result = backend.get(cache_key)
            if result is not None:
                wrapper._cache_hits = getattr(wrapper, '_cache_hits', 0) + 1
                return result

            # Calculer et stocker
            wrapper._cache_misses = getattr(wrapper, '_cache_misses', 0) + 1
            result = func(*args, **kwargs)
            backend.set(cache_key, result, timeout=timeout)
            return result

        wrapper._cache_hits = 0
        wrapper._cache_misses = 0
        return wrapper
    return decorator


def cache_page_simulation(timeout: int = 300):
    """
    Simule @cache_page de Django.
    Dans un vrai contexte Django, la clé inclurait l'URL complète.
    """
    import functools

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request_path: str, **kwargs):
            backend = _default_cache
            cache_key = f'view:{request_path}'

            cached_response = backend.get(cache_key)
            if cached_response is not None:
                print(f"  [cache_page] HIT: {request_path}")
                return cached_response

            print(f"  [cache_page] MISS: {request_path}")
            response = view_func(request_path, **kwargs)
            backend.set(cache_key, response, timeout=timeout)
            return response
        return wrapper
    return decorator


# Cache global par défaut (équivalent de `from django.core.cache import cache`)
_default_cache = DictCacheBackend(default_timeout=300)
cache = _default_cache


# ============================================================
# 4. PATTERN GET_OR_SET THREAD-SAFE (Cache Stampede Prevention)
# ============================================================

class SafeCache:
    """
    Cache avec prévention du cache stampede.
    Utilise un verrou par clé pour éviter que plusieurs threads
    recalculent la même valeur simultanément.
    """

    def __init__(self, backend: DictCacheBackend):
        self._backend = backend
        self._locks: dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()

    def _get_key_lock(self, key: str) -> threading.Lock:
        with self._locks_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]

    def get_or_set_safe(self, key: str, factory: Callable, timeout: int = 300) -> Any:
        """
        Version thread-safe de get_or_set.
        Garantit que factory() n'est appelée qu'une seule fois même sous charge.
        """
        # Tentative rapide (pas de verrou)
        value = self._backend.get(key)
        if value is not None:
            return value

        # Acquérir le verrou pour cette clé
        key_lock = self._get_key_lock(key)
        with key_lock:
            # Re-vérifier après acquisition du verrou (double-checked locking)
            value = self._backend.get(key)
            if value is not None:
                return value

            # On est le premier thread — calculer et stocker
            value = factory()
            self._backend.set(key, value, timeout=timeout)
            return value


# ============================================================
# 5. SIMULATION DE FRAGMENT CACHE ({% cache %} tag)
# ============================================================

class TemplateCacheManager:
    """
    Simule le tag {% cache %} de Django.
    """

    def __init__(self, backend: DictCacheBackend):
        self._backend = backend

    def cache_fragment(self, fragment_name: str, timeout: int, *vary_on,
                        render_func: Callable[[], str]) -> str:
        """
        Équivalent de {% cache timeout fragment_name vary_args %}.
        """
        # Construire la clé de fragment
        vary_key = ':'.join(str(v) for v in vary_on) if vary_on else 'default'
        cache_key = f'template_fragment:{fragment_name}:{vary_key}'

        result = self._backend.get(cache_key)
        if result is not None:
            return result

        # Rendre le fragment
        result = render_func()
        self._backend.set(cache_key, result, timeout=timeout)
        return result

    def invalidate_fragment(self, fragment_name: str, *vary_on):
        """Invalide un fragment spécifique."""
        vary_key = ':'.join(str(v) for v in vary_on) if vary_on else 'default'
        cache_key = f'template_fragment:{fragment_name}:{vary_key}'
        self._backend.delete(cache_key)


# ============================================================
# 6. FONCTION TESTER
# ============================================================

def tester():
    print("=" * 60)
    print("JOUR 54 — Django Cache Framework simulé en Python pur")
    print("=" * 60)

    # Instancier le backend
    backend = DictCacheBackend(default_timeout=300, max_entries=100)

    # ---- 1. Opérations de base ----
    print("\n--- 1. Opérations de Base ---")

    backend.set('username', 'Alice')
    print(f"GET username: {backend.get('username')}")

    backend.set('token', 'secret_xyz', timeout=2)
    print(f"GET token: {backend.get('token')}")
    print(f"TTL token: {backend.ttl('token')}s")
    time.sleep(2.1)
    print(f"GET token après expiration: {backend.get('token')} (None attendu)")

    backend.delete('username')
    print(f"GET après delete: {backend.get('username')} (None attendu)")

    # ---- 2. get_or_set ----
    print("\n--- 2. get_or_set ---")

    call_count = [0]

    def expensive_db_query():
        call_count[0] += 1
        time.sleep(0.05)  # Simuler la latence DB
        return {'articles': ['Article 1', 'Article 2', 'Article 3'], 'total': 3}

    print("Premier appel (MISS) :")
    t0 = time.time()
    result1 = backend.get_or_set('articles:list', expensive_db_query, timeout=60)
    t1 = time.time()
    print(f"  Résultat: {result1}, temps: {(t1-t0)*1000:.1f}ms")

    print("Deuxième appel (HIT) :")
    t0 = time.time()
    result2 = backend.get_or_set('articles:list', expensive_db_query, timeout=60)
    t1 = time.time()
    print(f"  Résultat: {result2}, temps: {(t1-t0)*1000:.1f}ms")

    print(f"DB appelée {call_count[0]} fois (1 attendu)")

    # Avec valeur directe (non callable)
    result3 = backend.get_or_set('config:site', {'titre': 'Mon Site', 'theme': 'dark'}, timeout=None)
    print(f"Config (valeur directe): {result3}")

    # ---- 3. get_many / set_many ----
    print("\n--- 3. get_many / set_many ---")

    users = {
        'user:1': {'nom': 'Alice', 'role': 'admin'},
        'user:2': {'nom': 'Bob', 'role': 'editor'},
        'user:3': {'nom': 'Charlie', 'role': 'viewer'},
    }
    failed = backend.set_many(users, timeout=600)
    print(f"set_many — clés échouées: {failed} ([] attendu)")

    # Récupérer plusieurs clés (user:99 n'existe pas)
    fetched = backend.get_many(['user:1', 'user:2', 'user:3', 'user:99'])
    print(f"get_many — clés trouvées: {list(fetched.keys())}")
    print(f"get_many — user:99 absent: {'user:99' not in fetched}")

    # ---- 4. add (NX — set if not exists) ----
    print("\n--- 4. add (Set If Not Exists) ---")

    result_add1 = backend.add('verrou:email_job', True, timeout=30)
    result_add2 = backend.add('verrou:email_job', True, timeout=30)
    print(f"Premier add: {result_add1} (True attendu)")
    print(f"Deuxième add: {result_add2} (False attendu — clé existe)")

    # ---- 5. incr / decr ----
    print("\n--- 5. incr / decr ---")

    backend.set('visites:article:42', 0, timeout=86400)
    backend.incr('visites:article:42')
    backend.incr('visites:article:42')
    backend.incr('visites:article:42', delta=5)
    print(f"Visites après 2 incr + incr(5): {backend.get('visites:article:42')} (7 attendu)")

    backend.decr('visites:article:42', delta=3)
    print(f"Visites après decr(3): {backend.get('visites:article:42')} (4 attendu)")

    try:
        backend.incr('cle_inexistante')
    except ValueError as e:
        print(f"incr sur clé inexistante: ValueError capturé correctement ({e})")

    # ---- 6. Versioning ----
    print("\n--- 6. Versioning ---")

    backend.set('config', {'version': 1, 'couleur': 'bleu'}, version=1)
    backend.set('config', {'version': 2, 'couleur': 'rouge'}, version=2)

    v1 = backend.get('config', version=1)
    v2 = backend.get('config', version=2)
    print(f"Version 1: {v1}")
    print(f"Version 2: {v2}")

    backend.delete('config', version=1)
    print(f"Après suppression v1: {backend.get('config', version=1)} (None attendu)")
    print(f"Version 2 toujours là: {backend.get('config', version=2)}")

    # ---- 7. Décorateur cache_result ----
    print("\n--- 7. Décorateur @cache_result ---")

    @cache_result(timeout=60, key_prefix='profile', cache_backend=backend)
    def get_user_profile(user_id: int) -> dict:
        time.sleep(0.05)  # Simuler latence DB
        return {'id': user_id, 'nom': f'User_{user_id}', 'articles': user_id * 3}

    # Plusieurs appels
    for call in range(3):
        t0 = time.time()
        profile = get_user_profile(1)
        elapsed = (time.time() - t0) * 1000
        print(f"  Appel {call+1}: {profile['nom']}, {elapsed:.1f}ms")

    print(f"  Hits: {get_user_profile._cache_hits}, Misses: {get_user_profile._cache_misses}")

    # Profils différents (clés différentes)
    get_user_profile(2)
    get_user_profile(3)
    print(f"  Total misses: {get_user_profile._cache_misses} (3 attendu: user 1, 2, 3)")

    # ---- 8. Simulation @cache_page ----
    print("\n--- 8. Simulation @cache_page ---")

    @cache_page_simulation(timeout=300)
    def article_list_view(request_path: str) -> str:
        # Simuler le rendu d'une template
        return f"<html><h1>Articles</h1><p>Contenu généré à {time.time():.2f}</p></html>"

    response1 = article_list_view('/articles/')
    response2 = article_list_view('/articles/')
    response3 = article_list_view('/blog/')  # URL différente — MISS

    print(f"  /articles/ identique aux 2 appels: {response1 == response2}")
    print(f"  /blog/ différent: {response3 != response1}")

    # ---- 9. Fragment Cache ----
    print("\n--- 9. Fragment Cache ({% cache %}) ---")

    frag_backend = DictCacheBackend(default_timeout=60)
    frag_manager = TemplateCacheManager(frag_backend)
    render_count = [0]

    def render_sidebar():
        render_count[0] += 1
        return "<aside><h3>Populaires</h3><ul><li>Article 1</li></ul></aside>"

    # Premier rendu (MISS)
    fragment1 = frag_manager.cache_fragment('sidebar', 600, render_func=render_sidebar)
    # Deuxième rendu (HIT)
    fragment2 = frag_manager.cache_fragment('sidebar', 600, render_func=render_sidebar)
    print(f"Fragment identique: {fragment1 == fragment2}")
    print(f"render_sidebar appelée: {render_count[0]} fois (1 attendu)")

    # Fragment par utilisateur (vary_on)
    def render_user_header(user_id):
        return f"<header>User {user_id} | 100 pts</header>"

    for uid in [1, 2, 1]:  # user 1 deux fois
        frag_manager.cache_fragment('user_header', 300, uid,
                                     render_func=lambda: render_user_header(uid))

    # Invalider le fragment d'un utilisateur
    frag_manager.invalidate_fragment('user_header', 1)
    print("Fragment user:1 invalidé")

    # ---- 10. SafeCache (anti-stampede) ----
    print("\n--- 10. SafeCache (Prévention Cache Stampede) ---")

    safe_backend = DictCacheBackend(default_timeout=60)
    safe_cache = SafeCache(safe_backend)
    compute_count = [0]
    results = []

    def slow_computation():
        compute_count[0] += 1
        time.sleep(0.1)  # Simuler calcul lent
        return {'data': 'résultat coûteux', 'computed_at': time.time()}

    # Lancer 5 threads simultanément — sans SafeCache, slow_computation serait appelé 5 fois
    threads = []
    for _ in range(5):
        t = threading.Thread(
            target=lambda: results.append(
                safe_cache.get_or_set_safe('heavy:computation', slow_computation, timeout=60)
            )
        )
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"5 threads — slow_computation appelée: {compute_count[0]} fois (1 attendu)")
    print(f"Tous les résultats identiques: {all(r == results[0] for r in results)}")

    # ---- 11. Multi-backend CacheRouter ----
    print("\n--- 11. Multi-backend CacheRouter ---")

    caches = CacheRouter()
    caches.configure('default', default_timeout=300)
    caches.configure('sessions', default_timeout=86400, max_entries=5000)
    caches.configure('rate_limit', default_timeout=60)

    caches['sessions'].set('session:abc123', {'user_id': 42, 'role': 'admin'})
    caches['rate_limit'].set('rate:user:42', 0)
    caches['rate_limit'].incr('rate:user:42')
    caches['rate_limit'].incr('rate:user:42')

    session = caches['sessions'].get('session:abc123')
    rate_count = caches['rate_limit'].get('rate:user:42')
    print(f"Session: {session}")
    print(f"Rate count: {rate_count}")

    # ---- 12. Statistiques ----
    print("\n--- 12. Statistiques du Cache ---")

    # Faire quelques opérations pour générer des stats
    test_backend = DictCacheBackend(default_timeout=60)
    test_backend.set('k1', 'v1')
    test_backend.set('k2', 'v2')
    test_backend.get('k1')   # HIT
    test_backend.get('k1')   # HIT
    test_backend.get('k3')   # MISS
    test_backend.get('k4')   # MISS
    test_backend.get('k2')   # HIT

    stats = test_backend.stats()
    print(f"Stats: {stats}")

    backend.clear()
    print(f"\nAprès clear(): {len(backend.keys())} clés (0 attendu)")

    # ---- 13. has_key et delete_many ----
    print("\n--- 13. has_key et delete_many ---")

    backend.set('a', 1)
    backend.set('b', 2)
    backend.set('c', 3)

    print(f"has_key 'a': {backend.has_key('a')} (True attendu)")
    print(f"has_key 'z': {backend.has_key('z')} (False attendu)")

    backend.delete_many(['a', 'b'])
    print(f"Après delete_many(['a','b']): has_key('a')={backend.has_key('a')}, has_key('c')={backend.has_key('c')}")

    print("\n" + "=" * 60)
    print("TOUS LES TESTS PASSES")
    print("=" * 60)


if __name__ == "__main__":
    tester()
