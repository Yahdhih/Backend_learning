# Jour 54 — Django Cache Framework (19 août 2026)

## Introduction

Le cache est l'une des optimisations les plus impactantes que vous puissiez apporter à une application web. Django intègre un framework de cache complet et flexible qui supporte de nombreux backends. Une vue qui prend 200ms à générer peut revenir en 1ms depuis le cache.

**Principe fondamental :**
```
Requête → Chercher dans le cache → Trouvé ? Retourner → Sinon : calculer, stocker, retourner
```

---

## 1. Les Backends de Cache Django

### 1.1 LocMemCache (In-Memory, par processus)

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

- **Avantages** : Zéro configuration, ultra-rapide
- **Inconvénients** : Non partagé entre processus, vidé au redémarrage
- **Usage** : Développement, tests

### 1.2 FileBasedCache

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/var/tmp/django_cache',
    }
}
```

- **Avantages** : Persiste entre les redémarrages, simple
- **Inconvénients** : Lent (I/O disque), difficile à partager entre serveurs
- **Usage** : Petit site avec un seul serveur

### 1.3 DatabaseCache

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
    }
}
```

```bash
# Créer la table
python manage.py createcachetable
```

- **Avantages** : Partagé entre serveurs, transactionnel
- **Inconvénients** : Plus lent qu'un cache dédié (charge la DB)
- **Usage** : Si vous n'avez pas Redis/Memcached mais avez plusieurs serveurs

### 1.4 RedisCache (django-redis — Recommandé en production)

```bash
pip install django-redis
```

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': True,  # Ne pas crasher si Redis est down
        },
        'KEY_PREFIX': 'myapp',
        'TIMEOUT': 300,  # TTL par défaut : 5 minutes
    },
    # Cache secondaire pour les sessions
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 86400,  # 24 heures
    }
}
```

### 1.5 MemcachedCache

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': '127.0.0.1:11211',
    }
}
```

### 1.6 DummyCache (pour les tests)

```python
# settings_test.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
```

Ne stocke rien — utile pour désactiver le cache en tests sans changer le code.

---

## 2. L'API de Cache de Bas Niveau

### 2.1 Opérations de base

```python
from django.core.cache import cache

# --- SET ---
# Stocker avec TTL (en secondes)
cache.set('ma_cle', 'ma_valeur', timeout=300)  # 5 minutes

# Stocker sans expiration (None = infini)
cache.set('config_site', {'titre': 'Mon Site'}, timeout=None)

# Stocker avec le timeout par défaut (TIMEOUT dans settings.py)
cache.set('ma_cle', 'valeur')

# --- GET ---
valeur = cache.get('ma_cle')
print(valeur)  # 'ma_valeur' ou None si expiré/absent

# Avec valeur par défaut
valeur = cache.get('ma_cle', default='valeur_par_défaut')

# --- DELETE ---
cache.delete('ma_cle')

# --- EXISTS ---
existe = cache.has_key('ma_cle')  # Déprécié
# Méthode préférée :
existe = cache.get('ma_cle') is not None
```

### 2.2 get_or_set — Pattern le plus courant

```python
from django.core.cache import cache
from myapp.models import Article

def get_article(article_id: int) -> dict:
    """
    Récupère un article depuis le cache ou la base de données.
    """
    cache_key = f'article:{article_id}'

    # get_or_set : si la clé n'existe pas, appelle la fonction et stocke le résultat
    def fetch_from_db():
        article = Article.objects.get(pk=article_id)
        return {
            'id': article.id,
            'titre': article.titre,
            'contenu': article.contenu,
            'auteur': article.auteur.nom,
        }

    return cache.get_or_set(cache_key, fetch_from_db, timeout=600)

# Exemple complet dans une view
from django.http import JsonResponse

def article_detail(request, article_id):
    article_data = cache.get_or_set(
        f'article:{article_id}',
        lambda: Article.objects.filter(pk=article_id).values(
            'id', 'titre', 'contenu', 'created_at'
        ).first(),
        timeout=600
    )
    return JsonResponse(article_data)
```

### 2.3 Opérations sur plusieurs clés

```python
from django.core.cache import cache

# Stocker plusieurs valeurs en une seule opération
cache.set_many({
    'user:1': {'nom': 'Alice', 'role': 'admin'},
    'user:2': {'nom': 'Bob', 'role': 'editor'},
    'user:3': {'nom': 'Charlie', 'role': 'viewer'},
}, timeout=900)

# Récupérer plusieurs valeurs
users = cache.get_many(['user:1', 'user:2', 'user:3', 'user:99'])
# {'user:1': {...}, 'user:2': {...}, 'user:3': {...}}  — user:99 absent

# Supprimer plusieurs clés
cache.delete_many(['user:1', 'user:2'])

# Vider tout le cache (à utiliser avec précaution !)
cache.clear()
```

### 2.4 add — Stocker seulement si absent

```python
# add() ne fait rien si la clé existe déjà (utile pour les verrous)
result = cache.add('verrou:ressource_critique', True, timeout=30)
if result:
    print("Verrou acquis")
    # ... traitement exclusif ...
    cache.delete('verrou:ressource_critique')
else:
    print("Verrou déjà pris, réessayer plus tard")
```

### 2.5 incr et decr

```python
# Compteurs atomiques
cache.set('visites:article:42', 0, timeout=86400)

# Incrémenter
cache.incr('visites:article:42')
cache.incr('visites:article:42', delta=5)

# Décrémenter
cache.decr('credits:user:1')

# Valeur actuelle
visites = cache.get('visites:article:42')
```

### 2.6 Utiliser un cache non-défaut

```python
from django.core.cache import caches

# Accéder à un cache spécifique
sessions_cache = caches['sessions']
sessions_cache.set('session:abc123', user_data, timeout=86400)

# Ou avec le gestionnaire de contexte
from django.core.cache import caches

def store_session(token, data):
    caches['sessions'].set(f'session:{token}', data, timeout=3600)
```

---

## 3. Cache par Vue — @cache_page

```python
# views.py
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.http import HttpResponse

# Vue basée sur une fonction
@cache_page(60 * 15)  # Cache pendant 15 minutes
def ma_vue(request):
    # Cette vue ne sera calculée qu'une fois toutes les 15 minutes
    articles = Article.objects.all().select_related('auteur')
    return render(request, 'articles/liste.html', {'articles': articles})

# Vue basée sur une classe
@method_decorator(cache_page(60 * 10), name='dispatch')
class ArticleListView(ListView):
    model = Article
    template_name = 'articles/liste.html'

    def get_queryset(self):
        return Article.objects.filter(statut='publié').select_related('auteur')

# Dans urls.py directement
from django.views.decorators.cache import cache_page

urlpatterns = [
    path('articles/', cache_page(60 * 15)(ArticleListView.as_view()), name='articles'),
    path('accueil/', cache_page(60 * 60)(AccueilView.as_view()), name='accueil'),
]
```

### Vary en-têtes — Cache par langue, utilisateur

```python
from django.views.decorators.vary import vary_on_cookie, vary_on_headers

@cache_page(60 * 15)
@vary_on_headers('Accept-Language')  # Cache différent par langue
def vue_multilingue(request):
    ...

@cache_page(60 * 5)
@vary_on_cookie  # Cache différent par session cookie
def vue_personnalisee(request):
    # Cache spécifique à l'utilisateur
    ...
```

---

## 4. Cache de Fragments de Template

```django
{% load cache %}

{# Cache ce bloc pendant 600 secondes #}
{% cache 600 "sidebar_populaire" %}
    <aside>
        <h3>Articles Populaires</h3>
        {% for article in articles_populaires %}
            <a href="{{ article.get_absolute_url }}">{{ article.titre }}</a>
        {% endfor %}
    </aside>
{% endcache %}

{# Cache par utilisateur — ajouter une variable au nom #}
{% cache 300 "profil_header" request.user.pk %}
    <header>
        <span>Bonjour, {{ request.user.first_name }}</span>
        <span>{{ request.user.credits }} crédits</span>
    </header>
{% endcache %}

{# Cache par langue #}
{% cache 3600 "footer_liens" LANGUAGE_CODE %}
    <footer>
        <!-- Liens traduits -->
    </footer>
{% endcache %}

{# Invalider un fragment dans une vue #}
```

```python
# Invalider un fragment de template
from django.core.cache import cache
from django.utils.cache import make_template_fragment_key

# Invalider le cache du profil pour un utilisateur
key = make_template_fragment_key('profil_header', [user.pk])
cache.delete(key)
```

---

## 5. Middleware de Cache (Site-wide)

```python
# settings.py — Cache de toutes les pages pour les utilisateurs anonymes
MIDDLEWARE = [
    'django.middleware.cache.UpdateCacheMiddleware',  # DOIT être en premier
    # ... autres middlewares ...
    'django.middleware.cache.FetchFromCacheMiddleware',  # DOIT être en dernier
]

CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 600
CACHE_MIDDLEWARE_KEY_PREFIX = 'mysite'
```

**Attention** : le site-wide cache ne fonctionne que pour les pages accessibles sans authentification.

---

## 6. Cache avec Redis — Fonctionnalités Avancées

### 6.1 Accès au client Redis natif

```python
from django_redis import get_redis_connection

# Accès direct au client redis-py
redis_client = get_redis_connection('default')

# Utiliser des commandes Redis natives
redis_client.incr('compteur_global')
redis_client.lpush('file_emails', 'email:user@example.com')
redis_client.zadd('leaderboard', {'Alice': 1500})
```

### 6.2 Cache versioning

```python
from django.core.cache import cache

# Stocker avec version
cache.set('config', {'couleur': 'bleu'}, version=1)

# Récupérer une version spécifique
data = cache.get('config', version=1)

# Récupérer la prochaine version (invalide la version actuelle)
cache.incr_version('config')

# La version 1 est maintenant inaccessible
data = cache.get('config', version=1)  # None
```

### 6.3 Scan de clés avec django-redis

```python
from django_redis import get_redis_connection

redis_client = get_redis_connection('default')

# Trouver toutes les clés correspondant à un pattern
# Le préfixe est ajouté automatiquement par Django
prefix = ':1:myapp:'  # format: :{version}:{prefix}:{key}

# Scanner sans bloquer
cursor = 0
keys = []
while True:
    cursor, batch = redis_client.scan(cursor, match=f'*article:*', count=100)
    keys.extend(batch)
    if cursor == 0:
        break

print(f"Clés trouvées: {len(keys)}")
```

---

## 7. Stratégie de Nommage des Clés

```python
# Conventions de nommage — IMPORTANT pour la maintenabilité
# Format: {version}:{module}:{entité}:{id}:{champ_optionnel}

# Mauvais
cache.set('user1', data)
cache.set('articles', articles)

# Bon
CACHE_KEY_PREFIXES = {
    'user_profile': 'v1:users:profile:{user_id}',
    'article_detail': 'v1:articles:detail:{article_id}',
    'article_list': 'v1:articles:list:page:{page}',
    'category_articles': 'v1:articles:category:{category_id}:page:{page}',
    'user_feed': 'v1:feeds:user:{user_id}',
}

def build_cache_key(template: str, **kwargs) -> str:
    """Construit une clé de cache standardisée."""
    return template.format(**kwargs)

# Utilisation
user_key = build_cache_key(
    CACHE_KEY_PREFIXES['user_profile'],
    user_id=42
)
# "v1:users:profile:42"

cache.set(user_key, user_data, timeout=300)
```

---

## 8. Configuration Complète en Production

```python
# settings/production.py

import os

REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{REDIS_URL}/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',  # Parsing C (plus rapide)
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 20,
            },
            'MAX_CONNECTIONS': 50,
            'IGNORE_EXCEPTIONS': True,  # Graceful degradation
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',  # Compression auto
        },
        'KEY_PREFIX': 'prod',
        'VERSION': 1,
        'TIMEOUT': 300,
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{REDIS_URL}/2',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,
        },
        'TIMEOUT': 86400,  # 24h
    },
    'rate_limit': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{REDIS_URL}/3',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 60,
    },
}

# Sessions dans Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 86400

# Cache par défaut pour les pages non-auth (middleware)
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'mysite'
```

---

## 9. Cache Patterns avec Django ORM

```python
# cache_utils.py
from django.core.cache import cache
from typing import Callable, Any
import hashlib
import json


def cached_queryset(cache_key: str, queryset_func: Callable, timeout: int = 300) -> Any:
    """
    Pattern générique pour cacher un QuerySet.
    """
    result = cache.get(cache_key)
    if result is None:
        result = list(queryset_func())  # Évaluer le QuerySet
        cache.set(cache_key, result, timeout=timeout)
    return result


# models.py
from django.db import models
from django.core.cache import cache


class ArticleManager(models.Manager):
    """Manager avec cache intégré."""

    def get_published(self, page: int = 1, per_page: int = 10):
        cache_key = f'articles:published:page:{page}:per_page:{per_page}'
        result = cache.get(cache_key)
        if result is None:
            offset = (page - 1) * per_page
            result = list(
                self.filter(statut='publié')
                .select_related('auteur', 'categorie')
                .order_by('-created_at')[offset:offset + per_page]
            )
            cache.set(cache_key, result, timeout=600)
        return result

    def get_or_cache(self, pk: int):
        cache_key = f'article:{pk}'
        result = cache.get(cache_key)
        if result is None:
            result = self.select_related('auteur', 'categorie').get(pk=pk)
            cache.set(cache_key, result, timeout=300)
        return result


class Article(models.Model):
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    statut = models.CharField(max_length=20, default='brouillon')
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ArticleManager()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalider le cache à chaque sauvegarde
        cache.delete(f'article:{self.pk}')
        # Invalider les listes paginées
        cache.delete_many([
            f'articles:published:page:1:per_page:10',
            f'articles:published:page:1:per_page:20',
        ])

    def delete(self, *args, **kwargs):
        cache.delete(f'article:{self.pk}')
        super().delete(*args, **kwargs)
```

---

## 10. Monitoring et Débogage

### 10.1 Cache logging

```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.core.cache': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### 10.2 Cache stats avec django-redis

```python
from django_redis import get_redis_connection

def get_cache_stats():
    """Récupère les statistiques du cache Redis."""
    r = get_redis_connection('default')
    info = r.info()
    return {
        'hits': info.get('keyspace_hits', 0),
        'misses': info.get('keyspace_misses', 0),
        'hit_rate': (
            info.get('keyspace_hits', 0) /
            max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1)
        ) * 100,
        'used_memory_mb': info.get('used_memory', 0) / 1024 / 1024,
        'connected_clients': info.get('connected_clients', 0),
        'total_keys': sum(
            v.get('keys', 0) for v in info.get('keyspace', {}).values()
        ),
    }
```

### 10.3 Django Debug Toolbar

```python
# settings.py (développement uniquement)
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
INTERNAL_IPS = ['127.0.0.1']

# Voir les hits/misses de cache dans la toolbar
```

---

## 11. Tests avec le Cache

```python
# tests.py
from django.test import TestCase, override_settings
from django.core.cache import cache


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
})
class ArticleCacheTest(TestCase):
    def setUp(self):
        cache.clear()

    def test_article_est_cache(self):
        # Premier appel — DB hit
        article = Article.objects.get_or_cache(1)
        self.assertIsNotNone(cache.get('article:1'))

        # Deuxième appel — cache hit (pas de DB query)
        with self.assertNumQueries(0):
            article_cached = Article.objects.get_or_cache(1)
        self.assertEqual(article.pk, article_cached.pk)

    def test_cache_invalide_apres_modification(self):
        article = Article.objects.create(titre='Test', statut='publié')
        cache.set(f'article:{article.pk}', article)

        # Modifier l'article
        article.titre = 'Modifié'
        article.save()

        # Le cache doit être vidé
        self.assertIsNone(cache.get(f'article:{article.pk}'))
```

---

## Résumé — Quand utiliser quel mécanisme ?

| Mécanisme | Granularité | Usage idéal |
|-----------|-------------|-------------|
| `@cache_page` | Vue entière | Pages statiques pour anonymes |
| `{% cache %}` | Fragment HTML | Sidebar, navigation, footer |
| `cache.get/set` | Donnée spécifique | Objets DB, résultats d'API |
| `cache.get_or_set` | Donnée avec fallback | Pattern standard |
| `cache.get_many` | Lot de données | Récupérer N objets |
| Site-wide middleware | Site entier | CDN-like pour pages publiques |

## Règles d'Or

1. **Commencer sans cache**, mesurer les performances, cacher ce qui est lent
2. **Toujours invalider** le cache quand les données changent
3. **Utiliser des TTL courts** pour les données volatiles, longs pour les données stables
4. **Nommer les clés** de manière cohérente et versionnée
5. **Tester avec DummyCache** pour ne pas avoir de side effects dans les tests
6. **Monitorer le hit rate** — un taux < 80% indique un problème de stratégie
