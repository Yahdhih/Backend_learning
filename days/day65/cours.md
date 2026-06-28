# Jour 65 — Project Production : Monitoring, Health Checks et Logs (30 août 2026)

## Pourquoi le monitoring ?

En production, sans monitoring :
- Tu apprends que l'app est down... quand un utilisateur se plaint
- Une erreur Python disparaît dans les logs sans trace
- Tu ne sais pas si la DB est surchargée
- Tu ne peux pas diagnostiquer les ralentissements

Avec monitoring :
- Alerte immédiate si l'app est down
- Chaque exception est capturée avec contexte complet
- Métriques en temps réel (requêtes/s, temps de réponse, mémoire)
- Historique pour analyser les tendances

**Ce qu'on va mettre en place :**
1. Health check endpoint (`/health/`)
2. Logs structurés JSON
3. Configuration Django LOGGING
4. Sentry (error tracking)
5. Prometheus + django-prometheus (métriques)

---

## Partie 1 : Health Check Endpoint

Le health check est un endpoint simple qui vérifie que tous les composants critiques sont opérationnels. Il est utilisé par :
- Les load balancers (AWS ELB, Nginx upstream)
- Les orchestrateurs (Kubernetes, Docker Swarm)
- Les services de monitoring (UptimeRobot, Better Uptime)

### blog/views/health.py
```python
"""
Endpoint de health check pour l'API Blog.

Vérifie :
- Base de données PostgreSQL
- Cache Redis
- Espace disque disponible
- Connexions DB actives
"""
import time
import shutil
import logging
from django.http import JsonResponse
from django.views import View
from django.db import connections
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


def check_database() -> dict:
    """
    Vérifier la connexion à la base de données.

    Retourne :
        {'status': 'ok', 'response_time_ms': 2.3}
        {'status': 'error', 'error': 'Connection refused', 'response_time_ms': 5000}
    """
    start = time.perf_counter()
    try:
        connection = connections['default']
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        elapsed_ms = (time.perf_counter() - start) * 1000

        if result != (1,):
            return {
                'status': 'error',
                'error': 'Unexpected query result',
                'response_time_ms': round(elapsed_ms, 2),
            }

        return {
            'status': 'ok',
            'response_time_ms': round(elapsed_ms, 2),
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("Health check DB failed: %s", exc, exc_info=True)
        return {
            'status': 'error',
            'error': str(exc),
            'response_time_ms': round(elapsed_ms, 2),
        }


def check_redis() -> dict:
    """
    Vérifier la connexion au cache Redis.

    Effectue un set/get/delete pour vérifier les opérations de base.
    """
    start = time.perf_counter()
    try:
        test_key = 'health_check_probe'
        test_value = 'ok'

        # Écriture
        cache.set(test_key, test_value, timeout=10)

        # Lecture
        result = cache.get(test_key)

        # Nettoyage
        cache.delete(test_key)

        elapsed_ms = (time.perf_counter() - start) * 1000

        if result != test_value:
            return {
                'status': 'error',
                'error': f'Cache returned {result!r} instead of {test_value!r}',
                'response_time_ms': round(elapsed_ms, 2),
            }

        return {
            'status': 'ok',
            'response_time_ms': round(elapsed_ms, 2),
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("Health check Redis failed: %s", exc, exc_info=True)
        return {
            'status': 'error',
            'error': str(exc),
            'response_time_ms': round(elapsed_ms, 2),
        }


def check_disk() -> dict:
    """
    Vérifier l'espace disque disponible.

    Alerte si moins de 20% de l'espace est libre.
    """
    try:
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100

        status = 'ok'
        if free_percent < 10:
            status = 'critical'
        elif free_percent < 20:
            status = 'warning'

        return {
            'status': status,
            'total_gb': round(total / (1024 ** 3), 2),
            'used_gb': round(used / (1024 ** 3), 2),
            'free_gb': round(free / (1024 ** 3), 2),
            'free_percent': round(free_percent, 1),
        }
    except Exception as exc:
        logger.error("Health check disk failed: %s", exc)
        return {
            'status': 'error',
            'error': str(exc),
        }


def check_db_connections() -> dict:
    """
    Vérifier le nombre de connexions actives à PostgreSQL.
    """
    try:
        connection = connections['default']
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    count(*) as total,
                    count(*) FILTER (WHERE state = 'active') as active,
                    count(*) FILTER (WHERE state = 'idle') as idle,
                    max_conn
                FROM pg_stat_activity,
                     (SELECT setting::int AS max_conn FROM pg_settings WHERE name = 'max_connections') s
                GROUP BY max_conn
            """)
            row = cursor.fetchone()

        if row:
            total, active, idle, max_conn = row
            usage_percent = (total / max_conn) * 100
            return {
                'status': 'warning' if usage_percent > 80 else 'ok',
                'total': total,
                'active': active,
                'idle': idle,
                'max': max_conn,
                'usage_percent': round(usage_percent, 1),
            }
        return {'status': 'ok'}
    except Exception as exc:
        return {'status': 'error', 'error': str(exc)}


class HealthCheckView(View):
    """
    Endpoint de health check complet.

    GET /health/          → vérification complète (pour les dashboards)
    GET /health/?quick=1  → vérification rapide (pour les load balancers)

    Réponses :
    - 200 : tout va bien
    - 503 : au moins un composant critique est en erreur
    """

    def get(self, request):
        quick = request.GET.get('quick', '').lower() in ('1', 'true', 'yes')
        start = time.perf_counter()

        # Vérification rapide (load balancer)
        if quick:
            db_status = check_database()
            http_status = 200 if db_status['status'] == 'ok' else 503
            return JsonResponse(
                {'status': 'ok' if http_status == 200 else 'error', 'db': db_status},
                status=http_status,
            )

        # Vérification complète
        checks = {
            'database': check_database(),
            'cache': check_redis(),
            'disk': check_disk(),
            'db_connections': check_db_connections(),
        }

        # Déterminer le statut global
        has_error = any(c['status'] == 'error' for c in checks.values())
        has_warning = any(c['status'] in ('warning', 'critical') for c in checks.values())

        if has_error:
            overall_status = 'error'
            http_status = 503
        elif has_warning:
            overall_status = 'warning'
            http_status = 200
        else:
            overall_status = 'ok'
            http_status = 200

        elapsed_ms = (time.perf_counter() - start) * 1000

        response_data = {
            'status': overall_status,
            'timestamp': timezone.now().isoformat(),
            'response_time_ms': round(elapsed_ms, 2),
            'checks': checks,
            'version': '1.0.0',
        }

        # Logger les erreurs pour Sentry/alerting
        if has_error:
            logger.error("Health check failed: %s", response_data)

        return JsonResponse(response_data, status=http_status)
```

### Ajouter dans urls.py
```python
# blog_api/urls.py
from django.urls import path
from blog.views.health import HealthCheckView

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    # ... autres URLs
]
```

### Exemple de réponse
```json
{
    "status": "ok",
    "timestamp": "2026-08-30T10:30:00+02:00",
    "response_time_ms": 12.4,
    "checks": {
        "database": {
            "status": "ok",
            "response_time_ms": 2.1
        },
        "cache": {
            "status": "ok",
            "response_time_ms": 0.8
        },
        "disk": {
            "status": "ok",
            "total_gb": 50.0,
            "used_gb": 12.3,
            "free_gb": 37.7,
            "free_percent": 75.4
        },
        "db_connections": {
            "status": "ok",
            "total": 5,
            "active": 2,
            "idle": 3,
            "max": 100,
            "usage_percent": 5.0
        }
    },
    "version": "1.0.0"
}
```

---

## Partie 2 : Logs structurés JSON

Les logs texte bruts sont difficiles à analyser. Les logs JSON permettent de les ingérer dans des outils comme ELK Stack, Datadog, ou Grafana Loki.

### Installation
```bash
pip install python-json-logger
```

### blog/logging.py — Formatter personnalisé
```python
"""
Formatter de logs JSON pour la production.
"""
import json
import logging
import traceback
from datetime import datetime, timezone
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Formatter JSON avec champs supplémentaires.

    Exemple de log généré :
    {
        "timestamp": "2026-08-30T10:30:00.123Z",
        "level": "ERROR",
        "logger": "blog.views",
        "message": "Post not found",
        "request_id": "abc123",
        "user_id": 42,
        "post_id": 999,
        "exception": "KeyError: ...",
        "environment": "production"
    }
    """

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)

        # Timestamp ISO 8601
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()

        # Niveau de log en majuscules
        log_record['level'] = record.levelname

        # Nom du logger
        log_record['logger'] = record.name

        # Environnement (depuis les settings)
        import os
        log_record['environment'] = os.environ.get('DJANGO_ENV', 'unknown')

        # Supprimer les champs redondants
        log_record.pop('levelname', None)
        log_record.pop('name', None)

        # Ajouter la trace d'exception si présente
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
            log_record['exception_type'] = record.exc_info[0].__name__ if record.exc_info[0] else None


def get_logger(name: str) -> logging.Logger:
    """
    Obtenir un logger configuré pour l'application.

    Usage :
        from blog.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Post créé", extra={"post_id": 42, "user_id": 1})
    """
    return logging.getLogger(name)
```

---

## Partie 3 : Configuration LOGGING de Django

### settings/base.py — Ajout de la configuration LOGGING
```python
# settings/base.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    # -------------------------------------------------------
    # Formatters
    # -------------------------------------------------------
    'formatters': {
        # Format JSON pour la production
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(timestamp)s %(level)s %(name)s %(message)s',
            'class': 'blog.logging.CustomJsonFormatter',
        },
        # Format lisible pour le développement
        'verbose': {
            'format': '[{asctime}] {levelname:8} {name} — {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },

    # -------------------------------------------------------
    # Filters
    # -------------------------------------------------------
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },

    # -------------------------------------------------------
    # Handlers — où envoyer les logs
    # -------------------------------------------------------
    'handlers': {
        # Console (stdout) — Docker capture ça
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',  # Remplacer par 'json' en prod
        },
        # Fichier pour les erreurs
        'file_error': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'json',
            'level': 'ERROR',
        },
        # Mail aux admins en cas d'erreur critique (prod seulement)
        'mail_admins': {
            'class': 'django.utils.log.AdminEmailHandler',
            'level': 'CRITICAL',
            'filters': ['require_debug_false'],
            'include_html': True,
        },
        # Null handler (pour silencer certains loggers)
        'null': {
            'class': 'logging.NullHandler',
        },
    },

    # -------------------------------------------------------
    # Loggers — qui log quoi
    # -------------------------------------------------------
    'loggers': {
        # Notre application
        'blog': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Django en général
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Requêtes HTTP Django
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Requêtes SQL (très verbeux, seulement en DEBUG)
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',   # Mettre 'DEBUG' pour voir les SQL
            'propagate': False,
        },
        # Sécurité
        'django.security': {
            'handlers': ['console', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Gunicorn
        'gunicorn.error': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'gunicorn.access': {
            'handlers': ['null'],  # Nginx gère les access logs
            'propagate': False,
        },
    },

    # Root logger (attrapé tout ce qui n'est pas configuré)
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
```

### Surcharger pour la production

```python
# settings/production.py — override du LOGGING

# En prod, utiliser JSON et ajouter le fichier d'erreurs
for handler in LOGGING['handlers'].values():
    if 'formatter' in handler and handler['formatter'] == 'verbose':
        handler['formatter'] = 'json'

# S'assurer que le répertoire de logs existe
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Activer le handler de fichier pour les erreurs
LOGGING['loggers']['blog']['handlers'].append('file_error')
LOGGING['loggers']['django.request']['handlers'].append('file_error')
```

### Utiliser les logs dans les vues
```python
# blog/views.py
import logging
logger = logging.getLogger(__name__)


class PostViewSet(viewsets.ModelViewSet):

    def create(self, request, *args, **kwargs):
        logger.info(
            "Création d'un nouveau post",
            extra={
                'user_id': request.user.id,
                'title': request.data.get('title', '')[:50],
                'ip': request.META.get('REMOTE_ADDR'),
            }
        )
        try:
            response = super().create(request, *args, **kwargs)
            logger.info(
                "Post créé avec succès",
                extra={
                    'post_id': response.data.get('id'),
                    'user_id': request.user.id,
                }
            )
            return response
        except Exception as exc:
            logger.error(
                "Erreur lors de la création du post",
                extra={
                    'user_id': request.user.id,
                    'error': str(exc),
                },
                exc_info=True,
            )
            raise

    def destroy(self, request, *args, **kwargs):
        post_id = kwargs.get('pk')
        logger.warning(
            "Suppression d'un post",
            extra={
                'post_id': post_id,
                'user_id': request.user.id,
                'ip': request.META.get('REMOTE_ADDR'),
            }
        )
        return super().destroy(request, *args, **kwargs)
```

---

## Partie 4 : Sentry — Error Tracking

Sentry capture automatiquement les exceptions et les envoie dans un tableau de bord avec :
- La stack trace complète
- Les variables locales au moment de l'erreur
- La requête HTTP (headers, body, user)
- L'historique des actions de l'utilisateur

### Installation
```bash
pip install sentry-sdk
```

### Configuration dans settings/production.py
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import logging

# Intégration logging : capturer les logs WARNING+ dans Sentry
sentry_logging = LoggingIntegration(
    level=logging.WARNING,        # Capturer à partir de WARNING
    event_level=logging.ERROR,    # Créer un "event" pour ERROR+
)

sentry_sdk.init(
    dsn=config('SENTRY_DSN', default=''),

    integrations=[
        DjangoIntegration(
            transaction_style='url',        # Grouper par URL
            middleware_spans=True,
            signals_spans=False,
        ),
        sentry_logging,
        RedisIntegration(),
    ],

    # Performance monitoring : capturer 10% des transactions
    traces_sample_rate=0.1,

    # Profiling : capturer 5% des transactions profilées
    profiles_sample_rate=0.05,

    # Environnement
    environment='production',

    # Release (pour suivre les déploiements)
    release=config('GIT_COMMIT', default='unknown'),

    # Ne pas envoyer les infos sensibles
    send_default_pii=False,

    # Filtrer certaines erreurs
    before_send=lambda event, hint: filter_sentry_event(event, hint),
)


def filter_sentry_event(event, hint):
    """
    Filtrer les événements avant envoi à Sentry.
    Retourner None pour ne pas envoyer l'événement.
    """
    # Ne pas capturer les 404 (trop nombreux)
    exc_info = hint.get('exc_info')
    if exc_info:
        exc_type = exc_info[0]
        from django.http import Http404
        if exc_type == Http404:
            return None

    # Ne pas capturer les erreurs d'authentification (normales)
    from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
    if exc_type in (AuthenticationFailed, NotAuthenticated):
        return None

    return event
```

### Capturer manuellement des erreurs
```python
import sentry_sdk

# Capturer une exception
try:
    risky_operation()
except Exception as exc:
    sentry_sdk.capture_exception(exc)
    # ou logger.error("...", exc_info=True) qui fait la même chose

# Capturer un message sans exception
sentry_sdk.capture_message(
    "Quota de stockage presque atteint",
    level="warning",
    extras={"used_gb": 48, "max_gb": 50}
)

# Ajouter du contexte utilisateur
with sentry_sdk.push_scope() as scope:
    scope.set_user({"id": user.id, "email": user.email})
    scope.set_tag("feature", "post_creation")
    scope.set_extra("post_data", request.data)
    sentry_sdk.capture_exception(exc)
```

---

## Partie 5 : Prometheus — Métriques

### Installation
```bash
pip install django-prometheus
```

### Configuration
```python
# settings/base.py
INSTALLED_APPS = [
    # ...
    'django_prometheus',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... autres middlewares ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
```

### URLs
```python
# blog_api/urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path('', include('django_prometheus.urls')),  # Expose /metrics
]
```

### Métriques disponibles automatiquement
```
# HELP django_http_requests_total_by_method_total Count of requests by method.
django_http_requests_total_by_method_total{method="GET"} 1234

# HELP django_http_responses_total_by_status_total Count of responses by status.
django_http_responses_total_by_status_total{status="200"} 1100
django_http_responses_total_by_status_total{status="404"} 34
django_http_responses_total_by_status_total{status="500"} 5

# HELP django_http_requests_latency_seconds_by_view_method
django_http_requests_latency_seconds_by_view_method_bucket{...}

# HELP django_db_execute_total Count of DB execute() calls.
django_db_execute_total 5678
```

### Métriques personnalisées
```python
# blog/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Compter les posts créés
posts_created_total = Counter(
    'blog_posts_created_total',
    'Nombre total de posts créés',
    ['status'],  # Labels
)

# Mesurer le temps de traitement
post_processing_duration = Histogram(
    'blog_post_processing_duration_seconds',
    'Temps de traitement des posts',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

# Nombre de posts publiés (jauge)
posts_published_gauge = Gauge(
    'blog_posts_published_count',
    'Nombre de posts publiés',
)

# Usage dans les vues
def create_post_view(request):
    with post_processing_duration.time():
        post = Post.objects.create(...)
    posts_created_total.labels(status=post.status).inc()
    if post.status == 'published':
        posts_published_gauge.inc()
```

---

## Partie 6 : Monitoring simple — UptimeRobot

Pour les petits projets, UptimeRobot (gratuit) surveille ton endpoint `/health/` et t'alerte par email/Slack si l'app est down.

### Configuration UptimeRobot
1. Créer un compte sur https://uptimerobot.com
2. "Add New Monitor" → Type: HTTP(s)
3. URL: `https://votre-domaine.com/health/`
4. Monitoring Interval: 5 minutes
5. Alert Contacts: email + Slack webhook

### Alerting Slack simple
```python
# blog/alerting.py
import requests
from django.conf import settings


def send_slack_alert(message: str, level: str = 'warning') -> bool:
    """
    Envoyer une alerte dans Slack.

    Args:
        message: Le message à envoyer
        level: 'info', 'warning', 'error', 'critical'

    Returns:
        True si envoyé avec succès
    """
    webhook_url = getattr(settings, 'SLACK_WEBHOOK_URL', None)
    if not webhook_url:
        return False

    colors = {
        'info': '#36a64f',
        'warning': '#ffcc00',
        'error': '#ff6600',
        'critical': '#ff0000',
    }

    payload = {
        'attachments': [{
            'color': colors.get(level, '#36a64f'),
            'title': f'[{level.upper()}] Blog API Alert',
            'text': message,
            'footer': 'Blog API Monitoring',
            'ts': int(__import__('time').time()),
        }]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception:
        return False
```

---

## Récapitulatif

| Outil | Usage | Niveau |
|-------|-------|--------|
| `/health/` | Vérifier que l'app tourne | Essentiel |
| Django LOGGING | Tracer ce qui se passe | Essentiel |
| JSON logs | Analyser les logs facilement | Recommandé |
| Sentry | Capturer les exceptions | Recommandé |
| UptimeRobot | Alerte si down | Recommandé |
| Prometheus | Métriques de performance | Avancé |
| Grafana | Dashboard de visualisation | Avancé |
| ELK Stack | Centralisation des logs | Avancé |

---

## Prochain cours

Demain (Jour 66) : **Déploiement final** sur un VPS et **révision complète** du parcours de 66 jours. C'est le dernier jour !
