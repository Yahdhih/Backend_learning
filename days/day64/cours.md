# Jour 64 — Project Production : Caching et Performance (29 août 2026)

## Pourquoi le caching ?

Sans cache, chaque requête `GET /api/posts/` :
1. Reçoit la requête HTTP dans Nginx
2. Passe à Gunicorn
3. Django exécute la vue
4. La vue fait une requête SQL à PostgreSQL
5. Django sérialise les résultats en JSON
6. Nginx renvoie la réponse

Avec cache (Redis), les étapes 3-5 sont sautées pour les requêtes identiques. Le gain typique : **50-100ms → 2-5ms** par requête.

---

## Partie 1 : Configuration de Django Redis

### Installation
```bash
pip install redis django-redis
```

### settings/production.py
```python
# Cache Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/0',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        },
        'KEY_PREFIX': 'blog_api',
        'TIMEOUT': 300,    # 5 minutes par défaut
    }
}

# Utiliser Redis pour les sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

---

## Partie 2 : Mettre en cache la liste des posts

### Approche 1 : `cache_page` decorator (simple)

```python
# blog/views.py
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from .models import Post
from .serializers import PostSerializer

@method_decorator(cache_page(60 * 5), name='list')   # 5 minutes
@method_decorator(cache_page(60 * 5), name='retrieve')
class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related('author').prefetch_related('tags')
    serializer_class = PostSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtres
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('-created_at')
```

**Problème** : `cache_page` cache toute la réponse HTTP, y compris pour les utilisateurs authentifiés. La clé de cache ne prend pas en compte l'utilisateur.

### Approche 2 : Cache manuel (recommandé pour l'API)

```python
# blog/views.py
import hashlib
import json
from django.core.cache import cache
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Post
from .serializers import PostSerializer


def make_cache_key(prefix: str, **kwargs) -> str:
    """
    Générer une clé de cache déterministe à partir des paramètres.

    >>> make_cache_key('posts_list', page=1, status='published')
    'posts_list:a1b2c3d4...'
    """
    params_str = json.dumps(kwargs, sort_keys=True)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
    return f"{prefix}:{params_hash}"


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer

    def get_queryset(self):
        return Post.objects.select_related('author').prefetch_related('tags')

    def list(self, request, *args, **kwargs):
        """
        Lister les posts avec cache.
        La clé de cache intègre les paramètres de requête.
        """
        # Construire une clé unique pour cette combinaison de paramètres
        cache_key = make_cache_key(
            'posts_list',
            page=request.query_params.get('page', 1),
            page_size=request.query_params.get('page_size', 10),
            status=request.query_params.get('status', 'published'),
            search=request.query_params.get('search', ''),
            ordering=request.query_params.get('ordering', '-created_at'),
        )

        # Tenter de récupérer depuis le cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = Response(cached_data)
            response['X-Cache'] = 'HIT'
            return response

        # Cache miss : calculer la réponse normalement
        response = super().list(request, *args, **kwargs)

        # Stocker en cache (5 minutes)
        cache.set(cache_key, response.data, timeout=60 * 5)

        response['X-Cache'] = 'MISS'
        return response

    def retrieve(self, request, *args, **kwargs):
        """
        Récupérer un post par ID avec cache.
        """
        post_id = kwargs.get('pk')
        cache_key = f'post_detail:{post_id}'

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            response = Response(cached_data)
            response['X-Cache'] = 'HIT'
            return response

        response = super().retrieve(request, *args, **kwargs)

        # Stocker 10 minutes pour les posts individuels
        cache.set(cache_key, response.data, timeout=60 * 10)

        response['X-Cache'] = 'MISS'
        return response
```

---

## Partie 3 : Invalidation du cache avec les signaux Django

L'invalidation est la partie la plus difficile du caching. Quand un post est modifié, les caches correspondants doivent être supprimés.

```python
# blog/signals.py
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Post

logger = logging.getLogger(__name__)


def invalidate_post_cache(post_id: int) -> None:
    """
    Invalider le cache pour un post spécifique et les listes.

    On invalide :
    1. Le cache du post individuel
    2. Tous les caches de liste (toutes les pages/filtres)
    """
    # 1. Invalider le post individuel
    detail_key = f'post_detail:{post_id}'
    cache.delete(detail_key)
    logger.info(f"Cache invalidé : {detail_key}")

    # 2. Invalider tous les caches de liste
    # Utiliser le pattern matching de Redis
    # ATTENTION : cache.delete_pattern() nécessite django-redis
    deleted_count = cache.delete_pattern('*posts_list:*')
    logger.info(f"Caches de liste invalidés : {deleted_count} entrées")


@receiver(post_save, sender=Post)
def invalidate_cache_on_post_save(sender, instance, created, **kwargs):
    """
    Signal déclenché quand un Post est créé ou modifié.
    """
    if created:
        # Nouveau post : invalider seulement les listes
        # (pas de cache à supprimer pour le post, il est nouveau)
        cache.delete_pattern('*posts_list:*')
        logger.info(f"Nouveau post #{instance.id} créé : caches de liste invalidés")
    else:
        # Post modifié : invalider le cache du post ET les listes
        invalidate_post_cache(instance.id)
        logger.info(f"Post #{instance.id} modifié : cache invalidé")


@receiver(post_delete, sender=Post)
def invalidate_cache_on_post_delete(sender, instance, **kwargs):
    """
    Signal déclenché quand un Post est supprimé.
    """
    invalidate_post_cache(instance.id)
    logger.info(f"Post #{instance.id} supprimé : cache invalidé")
```

### Enregistrer les signaux

```python
# blog/apps.py
from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'

    def ready(self):
        """Importer les signaux quand l'app est prête."""
        import blog.signals  # noqa: F401
```

```python
# blog/__init__.py
default_app_config = 'blog.apps.BlogConfig'
```

---

## Partie 4 : Optimisation des requêtes SQL

### Problème N+1

```python
# MAL : N+1 requêtes
posts = Post.objects.all()
for post in posts:
    print(post.author.username)  # 1 requête par post !
    for tag in post.tags.all():   # 1 requête par post par tag !
        print(tag.name)
```

### Solution : `select_related` et `prefetch_related`

```python
# blog/views.py
from django.db import models


class PostViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        return (
            Post.objects
            # select_related : JOIN SQL pour les FK et OneToOne
            .select_related('author', 'author__profile', 'category')
            # prefetch_related : requêtes séparées pour les M2M et reverse FK
            .prefetch_related('tags', 'comments')
            # Annoter avec le nombre de likes (evite une sous-requête par post)
            .annotate(
                likes_count=models.Count('likes', distinct=True),
                comments_count=models.Count('comments', distinct=True),
            )
            # Seulement les champs nécessaires
            .only(
                'id', 'title', 'excerpt', 'status',
                'created_at', 'updated_at',
                'author__id', 'author__username', 'author__email',
            )
            .order_by('-created_at')
        )
```

### Utiliser `defer()` et `only()`

```python
# only() : charger seulement ces champs
Post.objects.only('id', 'title', 'created_at')

# defer() : charger tout SAUF ces champs (bon pour les gros champs texte)
Post.objects.defer('content', 'raw_html')
```

### Mesurer les requêtes avec Django Debug Toolbar

```python
# En développement, vérifier le nombre de requêtes
from django.db import connection, reset_queries
from django.conf import settings

settings.DEBUG = True
reset_queries()

# Ton code ici
posts = list(Post.objects.select_related('author').all())

print(f"Nombre de requêtes SQL : {len(connection.queries)}")
for q in connection.queries:
    print(f"  {q['time']}s : {q['sql'][:100]}")
```

---

## Partie 5 : Pagination optimisée

La pagination standard de DRF fait un COUNT(*) sur toute la table à chaque requête. Sur des millions de lignes, c'est lent.

```python
# blog/pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class OptimizedPagination(PageNumberPagination):
    """
    Pagination sans COUNT(*) pour les grandes tables.
    Utilise un cursor-based approach pour indiquer "has_next".
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,  # Peut être None
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'count': {'type': 'integer', 'nullable': True},
                'next': {'type': 'string', 'nullable': True, 'format': 'uri'},
                'previous': {'type': 'string', 'nullable': True, 'format': 'uri'},
                'results': schema,
            },
        }
```

### Cursor pagination (le plus efficace)

```python
# Pour les flux chronologiques (posts triés par date)
from rest_framework.pagination import CursorPagination


class PostCursorPagination(CursorPagination):
    """
    Pagination par curseur : O(1) peu importe la taille de la table.
    Idéale pour les APIs de type "infinite scroll".
    """
    page_size = 20
    ordering = '-created_at'   # Doit être un champ avec index
    cursor_query_param = 'cursor'
```

---

## Partie 6 : pgBouncer — Connection Pooling

### Le problème

Django ouvre une connexion PostgreSQL par worker Gunicorn. Avec 9 workers sur 10 serveurs = 90 connexions PostgreSQL permanentes. PostgreSQL a du mal au-delà de 100-200 connexions simultanées.

### La solution : pgBouncer

pgBouncer est un pool de connexions qui se place entre Django et PostgreSQL.

```
Django (90 connexions) → pgBouncer (5-10 connexions réelles) → PostgreSQL
```

### pgbouncer.ini
```ini
[databases]
blog_db = host=db port=5432 dbname=blog_db

[pgbouncer]
listen_port = 6432
listen_addr = 0.0.0.0
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

; Mode de pooling
; session : 1 connexion par session client (le plus compatible)
; transaction : 1 connexion par transaction (recommandé)
; statement : 1 connexion par statement (éviter avec Django)
pool_mode = transaction

; Taille du pool
max_client_conn = 200     ; Max connexions clients Django
default_pool_size = 20    ; Connexions réelles vers PostgreSQL
min_pool_size = 5
reserve_pool_size = 5

; Timeouts
server_idle_timeout = 600
client_idle_timeout = 0

; Logging
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
stats_period = 60
```

### Ajouter pgBouncer dans docker-compose.prod.yml
```yaml
pgbouncer:
  image: edoburu/pgbouncer:1.22.1
  volumes:
    - ./pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini:ro
    - ./pgbouncer_userlist.txt:/etc/pgbouncer/userlist.txt:ro
  environment:
    - DATABASE_URL=postgres://blog_user:${DB_PASSWORD}@db:5432/blog_db
  depends_on:
    db:
      condition: service_healthy
  restart: always
```

### Django settings avec pgBouncer
```python
# settings/production.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': 'pgbouncer',   # Pointer vers pgBouncer, pas db !
        'PORT': '6432',
        # Important avec transaction mode :
        # Désactiver les features incompatibles
        'CONN_MAX_AGE': 0,  # pgBouncer gère le pooling
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

---

## Partie 7 : Load Testing avec Locust

### Installation
```bash
pip install locust
```

### locustfile.py
```python
"""
Locust load test pour le Blog API.

Usage :
    locust -f locustfile.py --headless -u 50 -r 5 -t 60s \
        --host http://localhost:8000

Arguments :
    -u 50  : 50 utilisateurs simultanés
    -r 5   : ajouter 5 utilisateurs par seconde
    -t 60s : durée du test : 60 secondes
"""
import random
from locust import HttpUser, TaskSet, task, between, events


class BlogAPITasks(TaskSet):
    """Ensemble de tâches simulant un utilisateur de l'API."""

    token = None
    post_ids = []

    def on_start(self):
        """Appelé une fois au démarrage de chaque utilisateur."""
        self._login()
        self._load_post_ids()

    def _login(self):
        """S'authentifier et stocker le token JWT."""
        response = self.client.post(
            "/api/auth/token/",
            json={
                "username": "testuser",
                "password": "testpassword123"
            },
            name="/api/auth/token/ [login]"
        )
        if response.status_code == 200:
            self.token = response.json().get('access')
        else:
            self.token = None

    def _load_post_ids(self):
        """Charger les IDs des posts pour les tests de détail."""
        response = self.client.get("/api/posts/?page_size=50")
        if response.status_code == 200:
            posts = response.json().get('results', [])
            self.post_ids = [p['id'] for p in posts]

    def _auth_headers(self):
        """Retourner les headers d'authentification."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(5)  # Poids 5 : 5x plus souvent que les tâches poids 1
    def list_posts(self):
        """Lister les posts — endpoint le plus fréquent."""
        page = random.randint(1, 5)
        self.client.get(
            f"/api/posts/?page={page}",
            name="/api/posts/ [list]"
        )

    @task(3)
    def get_post_detail(self):
        """Voir un post individuel."""
        if self.post_ids:
            post_id = random.choice(self.post_ids)
            self.client.get(
                f"/api/posts/{post_id}/",
                name="/api/posts/{id}/ [detail]"
            )

    @task(2)
    def search_posts(self):
        """Rechercher des posts."""
        keywords = ['python', 'django', 'rest', 'api', 'docker']
        keyword = random.choice(keywords)
        self.client.get(
            f"/api/posts/?search={keyword}",
            name="/api/posts/ [search]"
        )

    @task(1)
    def create_post(self):
        """Créer un nouveau post (authentifié)."""
        self.client.post(
            "/api/posts/",
            json={
                "title": f"Post de test {random.randint(1, 10000)}",
                "content": "Contenu de test généré par Locust pour le load testing.",
                "status": "draft",
            },
            headers=self._auth_headers(),
            name="/api/posts/ [create]"
        )

    @task(1)
    def health_check(self):
        """Vérifier le health check."""
        self.client.get("/health/", name="/health/")


class BlogAPIUser(HttpUser):
    """
    Utilisateur type de l'API Blog.
    Attend entre 1 et 3 secondes entre chaque action.
    """
    tasks = [BlogAPITasks]
    wait_time = between(1, 3)

    # Headers par défaut
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


class HeavyUser(HttpUser):
    """
    Utilisateur intensif — simule un bot ou un client agressif.
    Utile pour tester le rate limiting.
    """
    tasks = [BlogAPITasks]
    wait_time = between(0.1, 0.5)  # Très peu d'attente
    weight = 1  # Ratio : 1 HeavyUser pour 10 BlogAPIUser


# -------------------------------------------------------
# Événements Locust pour les statistiques personnalisées
# -------------------------------------------------------
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=== Début du test de charge ===")
    print(f"Hôte : {environment.host}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("=== Fin du test de charge ===")
    stats = environment.stats.total
    print(f"Total requêtes : {stats.num_requests}")
    print(f"Erreurs : {stats.num_failures}")
    print(f"RPS moyen : {stats.current_rps:.1f}")
    print(f"Temps de réponse médian : {stats.median_response_time}ms")
    print(f"Temps de réponse 95e percentile : {stats.get_response_time_percentile(0.95)}ms")
```

### Lancer Locust

```bash
# Interface web (port 8089)
locust -f locustfile.py --host http://localhost:8000
# Ouvrir http://localhost:8089

# Mode headless (CI/CD)
locust -f locustfile.py \
    --headless \
    --host http://localhost:8000 \
    --users 50 \
    --spawn-rate 5 \
    --run-time 60s \
    --csv=results/load_test \
    --html=results/load_test_report.html
```

---

## Partie 8 : Mesurer l'impact du cache

### Script de mesure

```python
# measure_cache_impact.py
"""
Mesurer l'impact du cache Redis sur les performances.

Usage : python measure_cache_impact.py
"""
import time
import statistics
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blog_api.settings.development')
django.setup()


def measure_response_time(func, n=100):
    """Mesurer le temps d'exécution d'une fonction n fois."""
    times = []
    for _ in range(n):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000)  # En ms
    return times


def get_posts_from_db():
    """Requête directe à la base de données."""
    from blog.models import Post
    from blog.serializers import PostSerializer
    posts = Post.objects.select_related('author').all()[:10]
    return PostSerializer(posts, many=True).data


def get_posts_from_cache():
    """Requête via le cache Redis."""
    from django.core.cache import cache
    from blog.models import Post
    from blog.serializers import PostSerializer

    cache_key = 'benchmark_posts'
    data = cache.get(cache_key)
    if data is None:
        posts = Post.objects.select_related('author').all()[:10]
        data = PostSerializer(posts, many=True).data
        cache.set(cache_key, data, timeout=300)
    return data


def main():
    from django.core.cache import cache

    print("=== Benchmark Cache vs Base de données ===\n")

    # Warmup
    print("Warmup...")
    get_posts_from_db()
    get_posts_from_cache()

    # Mesure sans cache
    print("Test sans cache (100 requêtes)...")
    db_times = measure_response_time(get_posts_from_db, n=100)

    # Vider le cache
    cache.clear()

    # Mesure avec cache (première requête popule le cache)
    print("Test avec cache (100 requêtes)...")
    cache_times = measure_response_time(get_posts_from_cache, n=100)

    # Résultats
    print("\n=== Résultats ===")
    print(f"\nSans cache (DB directe) :")
    print(f"  Moyenne : {statistics.mean(db_times):.2f}ms")
    print(f"  Médiane : {statistics.median(db_times):.2f}ms")
    print(f"  Min : {min(db_times):.2f}ms")
    print(f"  Max : {max(db_times):.2f}ms")
    print(f"  P95 : {sorted(db_times)[94]:.2f}ms")

    print(f"\nAvec cache (Redis) :")
    print(f"  Moyenne : {statistics.mean(cache_times):.2f}ms")
    print(f"  Médiane : {statistics.median(cache_times):.2f}ms")
    print(f"  Min : {min(cache_times):.2f}ms")
    print(f"  Max : {max(cache_times):.2f}ms")
    print(f"  P95 : {sorted(cache_times)[94]:.2f}ms")

    speedup = statistics.mean(db_times) / statistics.mean(cache_times)
    print(f"\nAccélération : {speedup:.1f}x plus rapide avec le cache")


if __name__ == '__main__':
    main()
```

---

## Résumé des techniques de performance

| Technique | Gain typique | Complexité |
|-----------|-------------|------------|
| `select_related` | 2-10x | Faible |
| `prefetch_related` | 2-10x | Faible |
| Cache Redis (list) | 10-50x | Moyenne |
| Cache Redis (detail) | 10-50x | Moyenne |
| Cursor pagination | 5-20x (grandes tables) | Moyenne |
| pgBouncer | Réduit la charge DB | Moyenne |
| Nginx cache | 100x+ (statiques) | Faible |
| Index SQL | 10-1000x | Faible |

---

## Prochain cours

Demain (Jour 65), on met en place le **monitoring** : health checks, logs structurés JSON, et intégration Sentry pour le tracking des erreurs en production.
