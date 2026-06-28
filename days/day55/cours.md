# Jour 55 — Stratégies de Cache : Invalidation et Patterns (20 août 2026)

## Introduction

> "There are only two hard things in Computer Science: cache invalidation and naming things."
> — Phil Karlton

L'invalidation du cache est le problème le plus difficile du cache. Un cache périmé peut faire autant de dégâts qu'une absence de cache : données incorrectes affichées aux utilisateurs, incohérences entre pages, bugs difficiles à reproduire.

Ce cours couvre les stratégies fondamentales d'invalidation et les patterns d'utilisation du cache en production.

---

## 1. Les 4 Stratégies de Cache Fondamentales

### 1.1 Cache-Aside (Lazy Loading) — Le Pattern par défaut

**Principe** : L'application gère elle-même le cache. En cas de miss, elle lit la DB et remplit le cache.

```
Requête ──► Cache ──► HIT: retourner donnée
                └──► MISS: lire DB ──► stocker dans cache ──► retourner
```

```python
from django.core.cache import cache
from myapp.models import Article

def get_article_cache_aside(article_id: int) -> dict:
    """
    Pattern Cache-Aside (Lazy Loading).
    Le cache n'est rempli qu'à la demande.
    """
    cache_key = f'article:{article_id}'

    # 1. Chercher dans le cache
    data = cache.get(cache_key)
    if data is not None:
        return data  # Cache HIT

    # 2. Cache MISS — lire depuis la base de données
    try:
        article = Article.objects.select_related('auteur', 'categorie').get(pk=article_id)
        data = {
            'id': article.id,
            'titre': article.titre,
            'contenu': article.contenu,
            'auteur': article.auteur.nom,
            'categorie': article.categorie.nom,
            'created_at': article.created_at.isoformat(),
            'vues': article.vues,
        }
    except Article.DoesNotExist:
        data = None

    # 3. Stocker dans le cache (même None pour éviter les répétitions)
    cache.set(cache_key, data, timeout=300)
    return data

# Invalidation : quand l'article est modifié
def update_article(article_id: int, **fields):
    Article.objects.filter(pk=article_id).update(**fields)
    # INVALIDER le cache
    cache.delete(f'article:{article_id}')
```

**Avantages :**
- Simple à implémenter
- Seules les données demandées sont mises en cache
- Résistant aux pannes de cache (fallback sur la DB)

**Inconvénients :**
- Les 3 premiers appels après un miss font une requête DB (problème de stampede)
- Données légèrement périmées jusqu'à l'expiration du TTL

---

### 1.2 Write-Through — Écriture Synchrone

**Principe** : À chaque écriture en DB, on met aussi à jour le cache immédiatement.

```
Écriture ──► DB + Cache (synchrone)
Lecture  ──► Cache (toujours à jour)
```

```python
from django.core.cache import cache
from django.db import transaction

class ArticleRepository:
    """Repository avec Write-Through."""

    CACHE_TTL = 600

    def save(self, article_id: int, data: dict) -> dict:
        """
        Write-Through : écriture dans DB ET cache en même temps.
        """
        with transaction.atomic():
            article, created = Article.objects.update_or_create(
                pk=article_id,
                defaults={
                    'titre': data['titre'],
                    'contenu': data['contenu'],
                    'statut': data.get('statut', 'brouillon'),
                }
            )

            # Préparer les données pour le cache
            cache_data = {
                'id': article.id,
                'titre': article.titre,
                'contenu': article.contenu,
                'statut': article.statut,
                'updated_at': article.updated_at.isoformat(),
            }

            # Mettre à jour le cache DANS la même transaction logique
            cache.set(f'article:{article_id}', cache_data, timeout=self.CACHE_TTL)

            return cache_data

    def get(self, article_id: int) -> dict | None:
        """Lecture : toujours depuis le cache (toujours à jour)."""
        return cache.get(f'article:{article_id}')

    def delete(self, article_id: int):
        """Suppression : DB et cache."""
        Article.objects.filter(pk=article_id).delete()
        cache.delete(f'article:{article_id}')

# Utilisation
repo = ArticleRepository()
# L'écriture met à jour DB et cache simultanément
data = repo.save(1, {'titre': 'Mon article', 'contenu': 'Contenu...'})
# La lecture est toujours depuis le cache
article = repo.get(1)
```

**Avantages :**
- Cache toujours cohérent avec la DB
- Pas de cache miss sur les données récemment écrites
- Pas de stampede

**Inconvénients :**
- Écriture plus lente (attendre DB + cache)
- Cache peut être plein de données jamais lues

---

### 1.3 Write-Behind (Write-Back) — Écriture Différée

**Principe** : On écrit d'abord dans le cache, et la synchronisation DB se fait en arrière-plan.

```
Écriture ──► Cache (rapide) ──► [Queue] ──► DB (asynchrone)
```

```python
import threading
import queue
import time
from collections import defaultdict

class WriteBehindCache:
    """
    Cache Write-Behind : les écritures vont d'abord dans le cache,
    puis sont propagées vers la DB en arrière-plan.
    """

    FLUSH_INTERVAL = 5  # Secondes entre chaque flush vers la DB
    MAX_BATCH_SIZE = 100

    def __init__(self):
        self._cache: dict = {}
        self._dirty: dict = {}  # Données en attente d'écriture DB
        self._write_queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()

        # Worker de flush en arrière-plan
        self._flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self._flush_thread.start()

    def set(self, key: str, value: dict):
        """
        Écriture rapide : cache + marquer comme dirty.
        La DB sera mise à jour dans FLUSH_INTERVAL secondes.
        """
        with self._lock:
            self._cache[key] = value
            self._dirty[key] = {
                'value': value,
                'timestamp': time.time()
            }
        # Notifier le worker
        self._write_queue.put(key)

    def get(self, key: str):
        """Lecture depuis le cache (peut être plus récent que la DB)."""
        with self._lock:
            return self._cache.get(key)

    def _flush_to_db(self, key: str, value: dict):
        """Écriture réelle vers la DB (simulée ici)."""
        print(f"  [WriteBehind] DB flush: {key} = {value}")
        # Article.objects.update_or_create(pk=..., defaults=value)

    def _flush_worker(self):
        """Thread de fond qui vide la queue dirty vers la DB."""
        while True:
            time.sleep(self.FLUSH_INTERVAL)
            with self._lock:
                dirty_copy = dict(self._dirty)
                self._dirty.clear()

            if dirty_copy:
                print(f"  [WriteBehind] Flush de {len(dirty_copy)} entrées vers DB")
                for key, entry in dirty_copy.items():
                    self._flush_to_db(key, entry['value'])

    def force_flush(self):
        """Forcer un flush immédiat (avant shutdown)."""
        with self._lock:
            dirty_copy = dict(self._dirty)
            self._dirty.clear()

        for key, entry in dirty_copy.items():
            self._flush_to_db(key, entry['value'])

# Démonstration
wb_cache = WriteBehindCache()

# Écriture très rapide (pas d'attente DB)
for i in range(5):
    wb_cache.set(f'article:{i}', {'titre': f'Article {i}', 'vues': i * 100})

# Lecture immédiate depuis le cache
article = wb_cache.get('article:2')
print(f"Lecture immédiate: {article}")

# Le flush DB se fait dans 5 secondes...
time.sleep(0.1)
wb_cache.force_flush()  # Forcer pour la démo
```

**Avantages :**
- Écriture ultra-rapide (ne bloque pas sur la DB)
- Excellent pour les compteurs (vues, likes) et mises à jour fréquentes
- Réduction de la charge DB (batch writes)

**Inconvénients :**
- Risque de perte de données si le cache tombe avant le flush
- Complexité de mise en œuvre
- Cohérence éventuelle (eventual consistency)

---

### 1.4 Read-Through — Cache comme Proxy

**Principe** : Le cache gère lui-même le chargement depuis la DB. L'application ne parle qu'au cache.

```python
from typing import Callable, Any
import time

class ReadThroughCache:
    """
    Cache Read-Through : le cache se charge lui-même de récupérer
    les données si elles ne sont pas présentes.
    """

    def __init__(self, loader: Callable[[str], Any], default_ttl: int = 300):
        """
        loader : fonction(key) -> valeur qui lit depuis la DB.
        """
        self._store: dict = {}
        self._expires: dict = {}
        self._loader = loader
        self.default_ttl = default_ttl

    def get(self, key: str, ttl: int = None) -> Any:
        """
        L'application appelle uniquement get().
        Le cache gère le chargement automatiquement.
        """
        ttl = ttl or self.default_ttl

        # Vérifier le cache
        if key in self._store:
            if time.time() < self._expires.get(key, float('inf')):
                return self._store[key]

        # MISS : charger depuis la DB via le loader
        print(f"  [ReadThrough] Chargement depuis DB: {key}")
        value = self._loader(key)

        # Stocker dans le cache
        if value is not None:
            self._store[key] = value
            self._expires[key] = time.time() + ttl

        return value

# Simuler une DB
fake_db = {
    'article:1': {'titre': 'Article 1', 'contenu': 'Contenu 1'},
    'article:2': {'titre': 'Article 2', 'contenu': 'Contenu 2'},
}

def db_loader(key: str) -> dict | None:
    """Charge une donnée depuis la DB."""
    time.sleep(0.05)  # Simuler latence
    return fake_db.get(key)

rt_cache = ReadThroughCache(loader=db_loader, default_ttl=60)

# L'application ne sait pas si ça vient du cache ou de la DB
article1 = rt_cache.get('article:1')  # MISS → charge de la DB
article1_again = rt_cache.get('article:1')  # HIT
```

---

## 2. Le Cache Stampede (Thundering Herd Problem)

### Le problème

```
T=0: TTL expire pour "articles:featured"
T=0: 100 requêtes arrivent simultanément
T=0: 100 requêtes trouvent MISS dans le cache
T=0: 100 requêtes font 100 requêtes SQL simultanées
T=0: La DB s'effondre sous la charge
```

### Solution 1 : Mutex Lock (Verrou par clé)

```python
import threading
import time
from django.core.cache import cache

_key_locks: dict[str, threading.Lock] = {}
_key_locks_lock = threading.Lock()

def get_key_lock(key: str) -> threading.Lock:
    with _key_locks_lock:
        if key not in _key_locks:
            _key_locks[key] = threading.Lock()
        return _key_locks[key]

def get_with_mutex(key: str, loader_func, timeout: int = 300):
    """
    Récupère depuis le cache avec protection contre le stampede.
    Un seul thread recalcule la valeur, les autres attendent.
    """
    # Tentative rapide (sans verrou)
    value = cache.get(key)
    if value is not None:
        return value

    # Acquérir le verrou pour cette clé
    lock = get_key_lock(key)
    with lock:
        # Double-check après acquisition (un autre thread a peut-être déjà calculé)
        value = cache.get(key)
        if value is not None:
            print(f"  Double-check HIT pour '{key}'")
            return value

        # On est le premier — calculer et stocker
        print(f"  Recalcul unique pour '{key}'")
        value = loader_func()
        cache.set(key, value, timeout=timeout)
        return value

# --- Démonstration ---
import threading

compute_count = [0]

def expensive_loader():
    compute_count[0] += 1
    time.sleep(0.1)  # Simuler requête DB lente
    return {'articles': ['A1', 'A2', 'A3'], 'generated_at': time.time()}

cache_local = {}  # Simuler le cache
results = []

def simulated_request(thread_id: int):
    result = get_with_mutex('articles:featured', expensive_loader)
    results.append(result)

# 10 requêtes simultanées
threads = [threading.Thread(target=simulated_request, args=(i,)) for i in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"expensive_loader appelé: {compute_count[0]} fois (1 attendu)")
print(f"Tous résultats identiques: {all(r == results[0] for r in results)}")
```

### Solution 2 : Probabilistic Early Expiration (XFetch)

```python
import math
import random
import time

def xfetch_get(cache_store: dict, expires_store: dict,
               key: str, loader_func, beta: float = 1.0) -> dict:
    """
    XFetch : renouvellement probabiliste du cache avant expiration.
    Évite le stampede en recalculant proactivement.

    beta : contrôle l'agressivité du renouvellement (default=1.0)
           Plus beta est grand, plus tôt le renouvellement commence.
    """
    now = time.time()
    cached = cache_store.get(key)
    expiry = expires_store.get(key, 0)

    if cached is None:
        # Cache miss — recalculer
        start = time.time()
        value = loader_func()
        delta = time.time() - start  # Temps de calcul

        # Stocker avec TTL de 60s
        ttl = 60
        cache_store[key] = value
        expires_store[key] = now + ttl
        cache_store[f'{key}:delta'] = delta
        return value

    # Récupérer le temps de calcul précédent
    delta = cache_store.get(f'{key}:delta', 0.01)

    # XFetch : probabilité de renouvellement basée sur :
    # - delta : temps de calcul (plus c'est lent, plus on renouvelle tôt)
    # - beta : aggressivité
    # - temps restant avant expiration
    time_remaining = expiry - now
    score = -delta * beta * math.log(random.random())

    if score > time_remaining:
        # Renouveler proactivement (même si pas encore expiré)
        print(f"  [XFetch] Renouvellement proactif de '{key}' ({time_remaining:.2f}s restant)")
        value = loader_func()
        cache_store[key] = value
        expires_store[key] = now + 60
        cache_store[f'{key}:delta'] = delta
        return value

    return cached
```

### Solution 3 : Stale-While-Revalidate

```python
import threading
import time

class StaleWhileRevalidateCache:
    """
    Retourne des données périmées pendant la revalidation en arrière-plan.
    Aucun thread ne doit attendre la mise à jour.
    """

    def __init__(self):
        self._store: dict = {}
        self._revalidating: set = set()
        self._lock = threading.Lock()

    def get(self, key: str, loader_func, max_age: int = 60, stale_ttl: int = 120) -> dict | None:
        """
        max_age  : TTL "frais" — données directement retournées
        stale_ttl: TTL "périmé" — données retournées + revalidation en arrière-plan
        """
        now = time.time()
        entry = self._store.get(key)

        if entry is None:
            # Pas de données — attendre le premier chargement
            print(f"  [SWR] Premier chargement de '{key}'")
            value = loader_func()
            self._store[key] = {'value': value, 'created_at': now}
            return value

        age = now - entry['created_at']

        if age < max_age:
            # Données fraîches — retourner directement
            return entry['value']
        elif age < stale_ttl:
            # Données périmées — retourner + revalider en arrière-plan
            print(f"  [SWR] Données périmées ({age:.1f}s), revalidation en fond...")
            self._revalidate_background(key, loader_func)
            return entry['value']  # Retourner immédiatement les données périmées
        else:
            # Données trop vieilles — bloquer et recharger
            print(f"  [SWR] Données trop vieilles, rechargement bloquant...")
            value = loader_func()
            self._store[key] = {'value': value, 'created_at': now}
            return value

    def _revalidate_background(self, key: str, loader_func):
        with self._lock:
            if key in self._revalidating:
                return  # Revalidation déjà en cours
            self._revalidating.add(key)

        def _do_revalidate():
            try:
                value = loader_func()
                self._store[key] = {'value': value, 'created_at': time.time()}
                print(f"  [SWR] Revalidation terminée pour '{key}'")
            finally:
                with self._lock:
                    self._revalidating.discard(key)

        thread = threading.Thread(target=_do_revalidate, daemon=True)
        thread.start()
```

---

## 3. Invalidation par TTL vs Invalidation par Événement

### TTL (Time-to-Live)

```python
# Simple mais pas précis
cache.set('user:42', user_data, timeout=300)  # Périmé dans 5 min maximum

# Avantages : simple, auto-nettoyage, pas de logique d'invalidation
# Inconvénients : données potentiellement incorrectes pendant le TTL
```

### Invalidation par Événement (Event-Based)

```python
# signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Article, Categorie

@receiver(post_save, sender=Article)
def invalider_cache_article(sender, instance, **kwargs):
    """Invalide le cache à chaque modification d'un article."""
    # Invalider l'article spécifique
    cache.delete(f'article:{instance.pk}')

    # Invalider les listes qui contiennent cet article
    cache.delete(f'articles:categorie:{instance.categorie_id}:page:1')
    cache.delete('articles:featured')
    cache.delete('articles:recent')

    # Si le statut change (brouillon → publié), invalider plus
    if instance.tracker.has_changed('statut'):
        cache.delete_many([
            'articles:published:count',
            'sitemap:articles',
        ])

@receiver(post_delete, sender=Article)
def invalider_cache_apres_suppression(sender, instance, **kwargs):
    cache.delete(f'article:{instance.pk}')
    cache.delete('articles:featured')
    cache.delete('articles:recent')
    cache.delete(f'articles:categorie:{instance.categorie_id}:page:1')

@receiver(post_save, sender=Categorie)
def invalider_cache_categorie(sender, instance, **kwargs):
    cache.delete(f'categorie:{instance.pk}')
    cache.delete('categories:all')
```

---

## 4. Cache Tags — Invalidation par Groupe

```python
"""
Les cache tags permettent d'invalider un groupe de clés en une seule opération.
Très utile pour invalider toutes les pages contenant un certain objet.
"""

from django.core.cache import cache
import json

class TaggedCache:
    """
    Cache avec support de tags pour invalidation groupée.
    """

    def set_with_tags(self, key: str, value, tags: list[str], timeout: int = 300):
        """Stocke une valeur associée à des tags."""
        # Stocker la valeur
        cache.set(key, value, timeout=timeout)

        # Pour chaque tag, enregistrer la clé
        for tag in tags:
            tag_key = f'cache_tag:{tag}'
            tag_keys = cache.get(tag_key, set())
            tag_keys.add(key)
            cache.set(tag_key, tag_keys, timeout=timeout + 60)  # TTL légèrement plus long

    def invalidate_tag(self, tag: str):
        """Invalide toutes les clés associées à un tag."""
        tag_key = f'cache_tag:{tag}'
        keys_to_delete = cache.get(tag_key, set())

        if keys_to_delete:
            cache.delete_many(list(keys_to_delete))
            cache.delete(tag_key)
            print(f"Invalidé {len(keys_to_delete)} clés pour le tag '{tag}'")

# Utilisation
tagged_cache = TaggedCache()

# Mettre en cache des pages associées à l'article 42
tagged_cache.set_with_tags('page:/articles/', articles_data,
                            tags=['article:42', 'articles:list'])
tagged_cache.set_with_tags('page:/articles/42/', article_detail,
                            tags=['article:42'])
tagged_cache.set_with_tags('page:/sitemap/', sitemap_data,
                            tags=['articles:list', 'sitemap'])

# Quand l'article 42 est modifié : invalider tout ce qui le concerne
tagged_cache.invalidate_tag('article:42')
# Invalide: page:/articles/ ET page:/articles/42/
# Garde: page:/sitemap/ (pas lié à article:42 directement)
```

---

## 5. Cache Warming — Pré-chargement

```python
"""
Cache Warming : pré-remplir le cache avant qu'il y ait du trafic.
Évite les miss en masse après un démarrage ou un déploiement.
"""

import threading
from django.core.cache import cache

class CacheWarmer:
    """Pré-charge le cache de manière ordonnée."""

    def __init__(self, workers: int = 4):
        self.workers = workers
        self._errors = []

    def warm_articles(self, article_ids: list[int]):
        """Pré-charge une liste d'articles dans le cache."""
        import queue
        work_queue = queue.Queue()

        for article_id in article_ids:
            work_queue.put(article_id)

        def worker():
            while True:
                try:
                    article_id = work_queue.get_nowait()
                    self._warm_article(article_id)
                    work_queue.task_done()
                except queue.Empty:
                    break
                except Exception as e:
                    self._errors.append((article_id, str(e)))

        threads = [threading.Thread(target=worker) for _ in range(self.workers)]
        for t in threads:
            t.start()
        work_queue.join()
        for t in threads:
            t.join()

        print(f"Warm-up terminé: {len(article_ids)} articles, {len(self._errors)} erreurs")

    def _warm_article(self, article_id: int):
        """Charge un article en cache."""
        cache_key = f'article:{article_id}'
        if cache.get(cache_key) is not None:
            return  # Déjà en cache

        # article = Article.objects.select_related('auteur').get(pk=article_id)
        # cache.set(cache_key, serialize(article), timeout=600)
        print(f"  Warm: article:{article_id}")

# Commande Django pour le warm-up
# management/commands/warm_cache.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Pré-charge le cache Redis'

    def handle(self, *args, **options):
        from myapp.models import Article
        from myapp.cache import CacheWarmer

        # Charger les articles les plus populaires
        article_ids = list(
            Article.objects.filter(statut='publié')
            .order_by('-vues')[:1000]
            .values_list('id', flat=True)
        )

        warmer = CacheWarmer(workers=8)
        warmer.warm_articles(article_ids)
        self.stdout.write("Cache pré-chargé avec succès")
```

---

## 6. Cache Versioning — Invalidation sans Downtime

```python
"""
Cache Versioning : changer la version dans la clé invalide tout le cache
sans avoir à supprimer explicitement chaque clé.
Technique très utilisée lors des déploiements.
"""

import os

# settings.py
CACHE_VERSION = os.environ.get('CACHE_VERSION', '1')  # Changer à chaque déploiement

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
        'VERSION': int(CACHE_VERSION),  # Toutes les clés incluront cette version
        'KEY_PREFIX': 'myapp',
    }
}
```

```python
# cache_utils.py
from django.core.cache import cache
from django.conf import settings

# Avec VERSION=1, les clés sont : myapp:1:article:42
# Avec VERSION=2, les clés sont : myapp:2:article:42
# → Toutes les données v1 sont automatiquement ignorées

def get_versioned_key(base_key: str) -> str:
    """Clé avec version applicative intégrée."""
    return f"v{settings.CACHE_VERSION}:{base_key}"

# Alternative : version dans les données
def get_article_with_schema_version(article_id: int) -> dict | None:
    """Vérifie que les données en cache sont du bon schéma."""
    SCHEMA_VERSION = 3  # Incrémenter quand le format change

    data = cache.get(f'article:{article_id}')
    if data is None:
        return None

    # Vérifier la version du schéma
    if data.get('_schema_version') != SCHEMA_VERSION:
        cache.delete(f'article:{article_id}')
        return None

    return data

def store_article_with_version(article_id: int, data: dict):
    SCHEMA_VERSION = 3
    data['_schema_version'] = SCHEMA_VERSION
    cache.set(f'article:{article_id}', data, timeout=300)
```

---

## 7. Stratégies Avancées en Production

### 7.1 Cache à deux niveaux (L1/L2)

```python
"""
L1 : Cache local en mémoire (très rapide, limité, par processus)
L2 : Redis (partagé entre tous les workers, plus lent)
"""

from django.core.cache import caches
from django.core.cache.backends.locmem import LocMemCache

_local_cache = LocMemCache('local', {})  # Cache L1 in-process

def get_two_level(key: str, loader_func, l1_ttl=30, l2_ttl=300):
    """
    Cache à deux niveaux :
    1. Chercher dans le cache local (L1)
    2. Chercher dans Redis (L2)
    3. Recalculer si absent partout
    """
    # L1 : cache local
    value = _local_cache.get(key)
    if value is not None:
        return value

    # L2 : Redis
    redis_cache = caches['default']
    value = redis_cache.get(key)
    if value is not None:
        # Propager en L1
        _local_cache.set(key, value, l1_ttl)
        return value

    # DB
    value = loader_func()
    redis_cache.set(key, value, l2_ttl)
    _local_cache.set(key, value, l1_ttl)
    return value
```

### 7.2 Circuit Breaker pour le Cache

```python
"""
Si Redis est indisponible, ne pas faire crasher l'application.
Fallback gracieux vers la DB.
"""

import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = 'closed'    # Normal
    OPEN = 'open'        # Redis down — bypass
    HALF_OPEN = 'half_open'  # Test de récupération

class CacheCircuitBreaker:
    """
    Évite de saturer Redis si il est en erreur.
    """

    FAILURE_THRESHOLD = 5    # Erreurs avant ouverture
    RECOVERY_TIMEOUT = 30    # Secondes avant test de récupération

    def __init__(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0

    def get(self, key: str, loader_func, timeout: int = 300):
        if self.state == CircuitState.OPEN:
            # Vérifier si on peut tenter une récupération
            if time.time() - self.last_failure_time > self.RECOVERY_TIMEOUT:
                self.state = CircuitState.HALF_OPEN
                print("[CircuitBreaker] Tentative de récupération...")
            else:
                # Circuit ouvert — bypass direct vers DB
                print(f"[CircuitBreaker] OPEN — bypass DB pour '{key}'")
                return loader_func()

        try:
            from django.core.cache import cache
            value = cache.get(key)
            if value is None:
                value = loader_func()
                cache.set(key, value, timeout)

            # Succès — fermer le circuit
            if self.state == CircuitState.HALF_OPEN:
                print("[CircuitBreaker] Récupération réussie — CLOSED")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            return value

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            print(f"[CircuitBreaker] Erreur Redis: {e} (échec {self.failure_count})")

            if self.failure_count >= self.FAILURE_THRESHOLD:
                self.state = CircuitState.OPEN
                print(f"[CircuitBreaker] OPEN — trop d'échecs Redis")

            # Fallback vers DB
            return loader_func()
```

---

## Résumé — Choisir la bonne stratégie

| Stratégie | Cohérence | Performance Lecture | Performance Écriture | Complexité |
|-----------|-----------|--------------------|--------------------|------------|
| Cache-Aside | Éventuelle | Bonne | Normale | Faible |
| Write-Through | Forte | Excellente | Lente | Moyenne |
| Write-Behind | Éventuelle | Excellente | Excellente | Haute |
| Read-Through | Éventuelle | Bonne | N/A | Moyenne |

### Règles de Décision

1. **Données lues souvent, écrites rarement** → Cache-Aside ou Read-Through
2. **Données lues ET écrites souvent** → Write-Through
3. **Compteurs, mises à jour haute fréquence** → Write-Behind
4. **Pages publiques statiques** → @cache_page + CDN
5. **Données personnalisées** → Low-level API avec clés user-spécifiques

### Les 5 règles d'or de l'invalidation

1. **Invalider précisément** : uniquement ce qui a changé
2. **Invalider immédiatement** : utiliser des signals Django
3. **TTL de sécurité** : toujours avoir un TTL même avec invalidation événementielle
4. **Versionner** : changer le numéro de version lors des déploiements
5. **Monitorer** : mesurer le hit rate et détecter les invalidations excessives
