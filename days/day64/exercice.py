"""
Exercice Jour 64 — Caching et Performance

Objectifs :
1. Implémenter l'invalidation du cache via les signaux Django
2. Écrire un test de charge Locust complet
3. Mesurer l'impact du cache sur les performances

Pour exécuter :
    python exercice.py

Note : Certaines parties nécessitent Django configuré et Redis running.
"""
import time
import statistics
import hashlib
import json
import os
from typing import Any


# ===========================================================
# PARTIE 1 : Invalidation du cache avec les signaux
# ===========================================================

CACHE_CODE = '''
# blog/signals.py — Invalidation du cache par signaux

import logging
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Post

logger = logging.getLogger(__name__)

CACHE_KEY_POST_DETAIL = "post_detail:{post_id}"
CACHE_KEY_POSTS_LIST_PATTERN = "*posts_list:*"


def build_post_detail_key(post_id: int) -> str:
    """Construire la clé de cache pour un post individuel."""
    return CACHE_KEY_POST_DETAIL.format(post_id=post_id)


def build_list_cache_key(page: int = 1, status: str = "published", search: str = "") -> str:
    """Construire la clé de cache pour une page de liste."""
    params = json.dumps(
        {"page": page, "status": status, "search": search},
        sort_keys=True
    )
    params_hash = hashlib.md5(params.encode()).hexdigest()[:8]
    return f"posts_list:{params_hash}"


def invalidate_post_caches(post_id: int) -> dict:
    """
    Invalider tous les caches liés à un post.

    Retourne un dictionnaire avec le nombre d'entrées supprimées :
    {
        'detail_deleted': bool,
        'list_deleted_count': int,
    }
    """
    result = {
        'detail_deleted': False,
        'list_deleted_count': 0,
    }

    # 1. Supprimer le cache du post individuel
    detail_key = build_post_detail_key(post_id)
    result['detail_deleted'] = cache.delete(detail_key)

    # 2. Supprimer tous les caches de liste
    # delete_pattern() est disponible avec django-redis
    try:
        deleted = cache.delete_pattern(CACHE_KEY_POSTS_LIST_PATTERN)
        result['list_deleted_count'] = deleted or 0
    except AttributeError:
        # Fallback si le backend ne supporte pas delete_pattern
        # (ex: LocMemCache en dev)
        cache.clear()
        result['list_deleted_count'] = -1  # Inconnu

    logger.info(
        "Cache invalidé pour post #%s : detail=%s, listes=%s",
        post_id,
        result['detail_deleted'],
        result['list_deleted_count'],
    )
    return result


@receiver(post_save, sender=Post)
def on_post_saved(sender, instance: Post, created: bool, **kwargs) -> None:
    """
    Invalider le cache quand un Post est créé ou modifié.

    - Création : seulement les listes (le post n'existait pas en cache)
    - Modification : le post ET les listes
    """
    if created:
        # Nouveau post : les listes sont potentiellement obsolètes
        try:
            cache.delete_pattern(CACHE_KEY_POSTS_LIST_PATTERN)
        except AttributeError:
            cache.clear()
        logger.info("Nouveau post #%s créé : caches de liste invalidés", instance.id)
    else:
        # Post modifié : invalider detail + listes
        invalidate_post_caches(instance.id)


@receiver(post_delete, sender=Post)
def on_post_deleted(sender, instance: Post, **kwargs) -> None:
    """
    Invalider le cache quand un Post est supprimé.
    """
    invalidate_post_caches(instance.id)
    logger.info("Post #%s supprimé : cache invalidé", instance.id)
'''

print("=== PARTIE 1 : Code des signaux ===")
print(CACHE_CODE)


# ===========================================================
# PARTIE 2 : Fichier Locust complet
# ===========================================================

LOCUST_CODE = '''
# locustfile.py — Test de charge complet pour le Blog API
"""
Usage :
    # Interface web
    locust -f locustfile.py --host http://localhost:8000

    # Mode headless — 50 users, spawn 5/s, durée 60s
    locust -f locustfile.py --headless \\
        --host http://localhost:8000 \\
        --users 50 --spawn-rate 5 --run-time 60s \\
        --csv results/load_test \\
        --html results/report.html
"""
import random
from locust import HttpUser, TaskSet, task, between, events
from locust.exception import StopUser


# -------------------------------------------------------
# Données de test
# -------------------------------------------------------
TEST_USER = {
    "username": "testuser",
    "password": "testpassword123",
}

SEARCH_TERMS = ["python", "django", "api", "docker", "backend"]
POST_STATUSES = ["published", "draft"]


# -------------------------------------------------------
# Tâches
# -------------------------------------------------------
class ReadOnlyTasks(TaskSet):
    """Tâches en lecture seule — utilisateur anonyme."""

    @task(10)
    def list_posts(self):
        """Endpoint le plus fréquent."""
        page = random.randint(1, 3)
        with self.client.get(
            f"/api/posts/?page={page}",
            name="/api/posts/ [list]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if 'results' not in data:
                    response.failure("Réponse inattendue : pas de 'results'")
            else:
                response.failure(f"Status {response.status_code}")

    @task(5)
    def search_posts(self):
        """Recherche — teste l'index de la base de données."""
        term = random.choice(SEARCH_TERMS)
        self.client.get(
            f"/api/posts/?search={term}",
            name="/api/posts/ [search]"
        )

    @task(3)
    def health_check(self):
        """Vérification de santé — ne doit jamais échouer."""
        with self.client.get(
            "/health/",
            name="/health/",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")

    @task(1)
    def robots_txt(self):
        """Robots.txt — très léger."""
        self.client.get("/robots.txt", name="/robots.txt")


class AuthenticatedTasks(TaskSet):
    """Tâches authentifiées — utilisateur connecté."""

    token = None
    post_ids = []

    def on_start(self):
        """Se connecter au démarrage."""
        self._authenticate()
        if self.token:
            self._load_post_ids()

    def _authenticate(self):
        """Obtenir un token JWT."""
        response = self.client.post(
            "/api/auth/token/",
            json=TEST_USER,
            name="/api/auth/token/ [login]",
        )
        if response.status_code == 200:
            self.token = response.json().get("access")
        else:
            raise StopUser()  # Impossible de s\'authentifier : arrêter

    def _load_post_ids(self):
        """Charger quelques IDs de posts pour les tests."""
        response = self.client.get(
            "/api/posts/?page_size=20",
            headers=self._headers(),
        )
        if response.status_code == 200:
            results = response.json().get("results", [])
            self.post_ids = [p["id"] for p in results]

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(5)
    def list_posts(self):
        self.client.get("/api/posts/", headers=self._headers(), name="/api/posts/ [list-auth]")

    @task(3)
    def get_post_detail(self):
        if not self.post_ids:
            return
        post_id = random.choice(self.post_ids)
        self.client.get(
            f"/api/posts/{post_id}/",
            headers=self._headers(),
            name="/api/posts/{id}/ [detail]"
        )

    @task(2)
    def create_post(self):
        suffix = random.randint(1, 100000)
        self.client.post(
            "/api/posts/",
            json={
                "title": f"Test post {suffix}",
                "content": "Contenu de test généré par Locust.",
                "status": "draft",
            },
            headers=self._headers(),
            name="/api/posts/ [create]"
        )

    @task(1)
    def refresh_token(self):
        """Rafraîchir le token (simule une longue session)."""
        if random.random() < 0.1:  # 10% des fois
            self._authenticate()


# -------------------------------------------------------
# Utilisateurs
# -------------------------------------------------------
class AnonymousUser(HttpUser):
    """Visiteur non connecté — 70% du trafic."""
    tasks = [ReadOnlyTasks]
    wait_time = between(1, 5)
    weight = 7

class AuthenticatedUser(HttpUser):
    """Utilisateur connecté — 30% du trafic."""
    tasks = [AuthenticatedTasks]
    wait_time = between(0.5, 3)
    weight = 3


# -------------------------------------------------------
# Rapport final
# -------------------------------------------------------
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats.total
    print("\\n=== RAPPORT DE CHARGE ===")
    print(f"Requêtes totales  : {stats.num_requests}")
    print(f"Échecs            : {stats.num_failures} ({stats.fail_ratio:.1%})")
    print(f"RPS               : {stats.current_rps:.1f}")
    print(f"Temps médian      : {stats.median_response_time}ms")
    print(f"P95               : {stats.get_response_time_percentile(0.95):.0f}ms")
    print(f"P99               : {stats.get_response_time_percentile(0.99):.0f}ms")
'''

print("\n\n=== PARTIE 2 : Fichier Locust ===")
print(LOCUST_CODE)


# ===========================================================
# PARTIE 3 : tester() — Démonstration de l'impact du cache
# ===========================================================

def simulate_db_query(post_id: int) -> dict:
    """
    Simuler une requête lente à la base de données.
    En production, ceci serait un vrai queryset Django.
    """
    time.sleep(0.05)  # Simule 50ms de requête SQL
    return {
        "id": post_id,
        "title": f"Post numéro {post_id}",
        "content": "Contenu du post...",
        "author": {"id": 1, "username": "alice"},
        "tags": ["python", "django"],
        "created_at": "2026-08-29T10:00:00Z",
    }


class SimpleCache:
    """Cache en mémoire simple pour la démonstration."""

    def __init__(self, timeout_seconds: float = 300.0):
        self._store: dict[str, tuple[Any, float]] = {}
        self.timeout = timeout_seconds
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any:
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            self.misses += 1
            return None
        self.hits += 1
        return value

    def set(self, key: str, value: Any, timeout: float = None) -> None:
        ttl = timeout or self.timeout
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


def get_post_with_cache(post_id: int, cache: SimpleCache) -> dict:
    """
    Récupérer un post avec mise en cache.
    Simule le comportement du PostViewSet.retrieve().
    """
    cache_key = f"post_detail:{post_id}"
    data = cache.get(cache_key)
    if data is not None:
        return data

    # Cache miss : requête à la DB
    data = simulate_db_query(post_id)
    cache.set(cache_key, data, timeout=600)
    return data


def tester():
    """
    Démonstration de l'impact du cache sur les performances.

    Scénario :
    - 5 posts différents, accédés de manière aléatoire
    - 200 requêtes au total (simule un trafic réaliste)
    - Mesure le temps avec et sans cache
    """
    import random

    print("=" * 60)
    print("DÉMONSTRATION : Impact du cache sur les performances")
    print("=" * 60)
    print()

    post_ids = [1, 2, 3, 4, 5]
    # Distribution réaliste : certains posts sont plus populaires
    weights = [40, 25, 15, 10, 10]
    n_requests = 200

    # -------------------------------------------------------
    # Scénario 1 : Sans cache (100% DB)
    # -------------------------------------------------------
    print("Scénario 1 : Sans cache (toutes les requêtes vont à la DB)")
    print("-" * 50)

    times_no_cache = []
    for i in range(n_requests):
        start = time.perf_counter()
        simulate_db_query(random.choices(post_ids, weights=weights)[0])
        elapsed = (time.perf_counter() - start) * 1000
        times_no_cache.append(elapsed)

    mean_no_cache = statistics.mean(times_no_cache)
    p95_no_cache = sorted(times_no_cache)[int(0.95 * n_requests)]
    total_no_cache = sum(times_no_cache)

    print(f"  Requêtes totales : {n_requests}")
    print(f"  Temps moyen      : {mean_no_cache:.1f}ms")
    print(f"  P95              : {p95_no_cache:.1f}ms")
    print(f"  Temps total      : {total_no_cache:.0f}ms ({total_no_cache/1000:.1f}s)")

    # -------------------------------------------------------
    # Scénario 2 : Avec cache (TTL 60s)
    # -------------------------------------------------------
    print()
    print("Scénario 2 : Avec cache Redis (TTL = 60 secondes)")
    print("-" * 50)

    cache = SimpleCache(timeout_seconds=60.0)
    times_with_cache = []

    for i in range(n_requests):
        start = time.perf_counter()
        get_post_with_cache(
            random.choices(post_ids, weights=weights)[0],
            cache
        )
        elapsed = (time.perf_counter() - start) * 1000
        times_with_cache.append(elapsed)

    mean_with_cache = statistics.mean(times_with_cache)
    p95_with_cache = sorted(times_with_cache)[int(0.95 * n_requests)]
    total_with_cache = sum(times_with_cache)

    print(f"  Requêtes totales : {n_requests}")
    print(f"  Cache hits       : {cache.hits} ({cache.hit_rate:.1%})")
    print(f"  Cache misses     : {cache.misses}")
    print(f"  Temps moyen      : {mean_with_cache:.1f}ms")
    print(f"  P95              : {p95_with_cache:.1f}ms")
    print(f"  Temps total      : {total_with_cache:.0f}ms ({total_with_cache/1000:.1f}s)")

    # -------------------------------------------------------
    # Comparaison
    # -------------------------------------------------------
    speedup = mean_no_cache / mean_with_cache if mean_with_cache > 0 else float('inf')
    time_saved = total_no_cache - total_with_cache

    print()
    print("=" * 60)
    print("COMPARAISON")
    print("=" * 60)
    print(f"  Accélération    : {speedup:.1f}x plus rapide avec le cache")
    print(f"  Temps économisé : {time_saved:.0f}ms sur {n_requests} requêtes")
    print(f"  Hit rate        : {cache.hit_rate:.1%}")
    print()

    # -------------------------------------------------------
    # Démonstration d'invalidation du cache
    # -------------------------------------------------------
    print("Démonstration de l'invalidation du cache :")
    print("-" * 50)

    # Peupler le cache
    test_cache = SimpleCache()
    for pid in post_ids:
        get_post_with_cache(pid, test_cache)

    initial_hits = test_cache.hits
    initial_misses = test_cache.misses
    print(f"  Cache peuplé avec {len(test_cache._store)} entrées")

    # Simuler une modification du post 1
    post_id_modified = 1
    detail_key = f"post_detail:{post_id_modified}"
    deleted = test_cache.delete(detail_key)
    print(f"  Post #{post_id_modified} modifié → cache supprimé : {deleted}")

    # Accéder au post 1 → MISS (rechargé depuis DB)
    test_cache.misses = 0
    test_cache.hits = 0
    _ = get_post_with_cache(post_id_modified, test_cache)
    print(f"  Accès post #{post_id_modified} après invalidation : {'MISS (rechargé)' if test_cache.misses > 0 else 'HIT (erreur !)'}")

    # Accéder aux autres posts → HIT (toujours en cache)
    for pid in [2, 3, 4, 5]:
        _ = get_post_with_cache(pid, test_cache)
    print(f"  Accès posts #2-5 : {test_cache.hits} HITs, {test_cache.misses - 1} MISS supplémentaires")

    print()
    print("Conclusion :")
    print("  - L'invalidation cible seulement le post modifié")
    print("  - Les autres posts restent en cache (pas de perturbation)")
    print("  - Le prochain accès au post modifié recharge les données fraîches")


if __name__ == "__main__":
    tester()
