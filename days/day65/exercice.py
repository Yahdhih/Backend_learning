"""
Exercice Jour 65 — Monitoring, Health Checks et Logs

Objectifs :
1. Implémenter une fonction de health check complète
2. Implémenter un logger JSON structuré
3. Démontrer l'utilisation avec tester()

Pour exécuter :
    python exercice.py
"""
import time
import json
import logging
import shutil
import socket
import sys
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ===========================================================
# PARTIE 1 : Types de données pour le health check
# ===========================================================

class CheckStatus(str, Enum):
    """Statuts possibles d'un check de santé."""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def is_healthy(self) -> bool:
        return self == CheckStatus.OK

    @property
    def http_status(self) -> int:
        """Code HTTP correspondant."""
        if self == CheckStatus.OK:
            return 200
        elif self == CheckStatus.WARNING:
            return 200    # Warning = toujours opérationnel
        else:
            return 503    # Error/Critical = service indisponible


@dataclass
class CheckResult:
    """Résultat d'un check individuel."""
    name: str
    status: CheckStatus
    response_time_ms: float = 0.0
    details: dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            'status': self.status.value,
            'response_time_ms': round(self.response_time_ms, 2),
        }
        if self.details:
            result.update(self.details)
        if self.error:
            result['error'] = self.error
        return result


@dataclass
class HealthReport:
    """Rapport de santé complet de l'application."""
    checks: list[CheckResult]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0.0"

    @property
    def overall_status(self) -> CheckStatus:
        """Statut global basé sur tous les checks."""
        statuses = [c.status for c in self.checks]
        if CheckStatus.ERROR in statuses or CheckStatus.CRITICAL in statuses:
            return CheckStatus.ERROR
        if CheckStatus.WARNING in statuses:
            return CheckStatus.WARNING
        return CheckStatus.OK

    @property
    def total_response_time_ms(self) -> float:
        return sum(c.response_time_ms for c in self.checks)

    def to_dict(self) -> dict:
        return {
            'status': self.overall_status.value,
            'timestamp': self.timestamp,
            'version': self.version,
            'total_response_time_ms': round(self.total_response_time_ms, 2),
            'checks': {
                check.name: check.to_dict()
                for check in self.checks
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ===========================================================
# PARTIE 2 : Fonctions de check
# ===========================================================

def check_database_simulation() -> CheckResult:
    """
    Simuler un check de base de données.
    En production, ceci exécuterait SELECT 1 via psycopg2.
    """
    start = time.perf_counter()

    try:
        # Simuler une connexion TCP à PostgreSQL
        # En production : psycopg2.connect(...) et cursor.execute("SELECT 1")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)

        # Essayer de se connecter à localhost:5432
        # (peut échouer si PostgreSQL n'est pas installé — c'est normal en demo)
        result = sock.connect_ex(('localhost', 5432))
        sock.close()

        elapsed_ms = (time.perf_counter() - start) * 1000

        if result == 0:
            return CheckResult(
                name='database',
                status=CheckStatus.OK,
                response_time_ms=elapsed_ms,
                details={'host': 'localhost', 'port': 5432, 'database': 'blog_db'},
            )
        else:
            # En demo, on simule un OK même si Postgres n'est pas là
            return CheckResult(
                name='database',
                status=CheckStatus.OK,
                response_time_ms=elapsed_ms,
                details={
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'blog_db',
                    'note': 'Simulation — PostgreSQL non disponible localement',
                },
            )

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            name='database',
            status=CheckStatus.ERROR,
            response_time_ms=elapsed_ms,
            error=str(exc),
        )


def check_redis_simulation() -> CheckResult:
    """
    Simuler un check Redis.
    En production : redis.Redis(...).ping()
    """
    start = time.perf_counter()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex(('localhost', 6379))
        sock.close()

        elapsed_ms = (time.perf_counter() - start) * 1000

        return CheckResult(
            name='cache',
            status=CheckStatus.OK,
            response_time_ms=elapsed_ms,
            details={
                'backend': 'Redis',
                'host': 'localhost',
                'port': 6379,
                'note': 'Simulation — Redis non disponible localement',
            },
        )

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            name='cache',
            status=CheckStatus.ERROR,
            response_time_ms=elapsed_ms,
            error=str(exc),
        )


def check_disk() -> CheckResult:
    """Vérifier l'espace disque disponible."""
    start = time.perf_counter()

    try:
        total, used, free = shutil.disk_usage("/")
        elapsed_ms = (time.perf_counter() - start) * 1000

        free_percent = (free / total) * 100

        if free_percent < 10:
            status = CheckStatus.CRITICAL
        elif free_percent < 20:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.OK

        return CheckResult(
            name='disk',
            status=status,
            response_time_ms=elapsed_ms,
            details={
                'total_gb': round(total / (1024 ** 3), 2),
                'used_gb': round(used / (1024 ** 3), 2),
                'free_gb': round(free / (1024 ** 3), 2),
                'free_percent': round(free_percent, 1),
            },
        )

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return CheckResult(
            name='disk',
            status=CheckStatus.ERROR,
            response_time_ms=elapsed_ms,
            error=str(exc),
        )


def check_memory() -> CheckResult:
    """Vérifier la mémoire disponible."""
    start = time.perf_counter()

    try:
        # Utiliser /proc/meminfo sur Linux, psutil si disponible
        try:
            import psutil
            mem = psutil.virtual_memory()
            used_percent = mem.percent
            available_gb = mem.available / (1024 ** 3)
            total_gb = mem.total / (1024 ** 3)
        except ImportError:
            # Fallback : lire /proc/meminfo (Linux seulement)
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            info = {}
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].rstrip(':')
                    value = int(parts[1])
                    info[key] = value
            total_kb = info.get('MemTotal', 0)
            available_kb = info.get('MemAvailable', 0)
            total_gb = total_kb / (1024 ** 2)
            available_gb = available_kb / (1024 ** 2)
            used_percent = ((total_kb - available_kb) / total_kb * 100) if total_kb > 0 else 0

        elapsed_ms = (time.perf_counter() - start) * 1000

        if used_percent > 90:
            status = CheckStatus.CRITICAL
        elif used_percent > 80:
            status = CheckStatus.WARNING
        else:
            status = CheckStatus.OK

        return CheckResult(
            name='memory',
            status=status,
            response_time_ms=elapsed_ms,
            details={
                'total_gb': round(total_gb, 2),
                'available_gb': round(available_gb, 2),
                'used_percent': round(used_percent, 1),
            },
        )

    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        # Memory check non critique — retourner OK si on ne peut pas mesurer
        return CheckResult(
            name='memory',
            status=CheckStatus.OK,
            response_time_ms=elapsed_ms,
            details={'note': f'Impossible de mesurer: {exc}'},
        )


def perform_health_check(quick: bool = False) -> HealthReport:
    """
    Effectuer un health check complet ou rapide.

    Args:
        quick: Si True, ne vérifie que la DB (pour les load balancers)

    Returns:
        HealthReport avec tous les résultats
    """
    if quick:
        checks = [check_database_simulation()]
    else:
        checks = [
            check_database_simulation(),
            check_redis_simulation(),
            check_disk(),
            check_memory(),
        ]

    return HealthReport(checks=checks)


# ===========================================================
# PARTIE 3 : Logger JSON structuré
# ===========================================================

class JsonFormatter(logging.Formatter):
    """
    Formateur de logs JSON structuré.

    Chaque log est un objet JSON avec des champs standardisés :
    - timestamp : ISO 8601
    - level : DEBUG, INFO, WARNING, ERROR, CRITICAL
    - logger : nom du logger
    - message : le message
    - + tous les champs extra passés dans extra={}
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Ajouter les champs extra
        # (tout ce qui est passé dans extra={} et n'est pas un champ standard)
        standard_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno',
            'pathname', 'filename', 'module', 'exc_info',
            'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread',
            'threadName', 'processName', 'process', 'taskName',
            'message',
        }

        for key, value in record.__dict__.items():
            if key not in standard_fields:
                try:
                    json.dumps(value)  # Vérifier que la valeur est sérialisable
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)

        # Ajouter l'exception si présente
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            if record.exc_info[0]:
                log_entry['exception_type'] = record.exc_info[0].__name__

        # Localisation dans le code (pour DEBUG)
        if record.levelno == logging.DEBUG:
            log_entry['location'] = f"{record.filename}:{record.lineno}"

        return json.dumps(log_entry, ensure_ascii=False)


def setup_json_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Configurer et retourner un logger JSON.

    Args:
        name: Nom du logger (typiquement __name__)
        level: Niveau de log minimum

    Returns:
        Logger configuré avec le formatter JSON
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


# ===========================================================
# PARTIE 4 : tester()
# ===========================================================

def tester():
    """
    Démonstration du health check et des logs JSON structurés.
    """
    print("=" * 60)
    print("DÉMONSTRATION : Health Check et Logs JSON")
    print("=" * 60)
    print()

    # -------------------------------------------------------
    # 1. Démonstration du health check
    # -------------------------------------------------------
    print("1. HEALTH CHECK COMPLET")
    print("-" * 40)

    report = perform_health_check(quick=False)
    print(f"   Statut global : {report.overall_status.value.upper()}")
    print(f"   Code HTTP     : {report.overall_status.http_status}")
    print(f"   Durée totale  : {report.total_response_time_ms:.1f}ms")
    print()
    print("   Checks individuels :")
    for check in report.checks:
        icon = "OK" if check.status == CheckStatus.OK else "WARN" if check.status == CheckStatus.WARNING else "ERR"
        print(f"   [{icon:4}] {check.name:<15} {check.response_time_ms:.1f}ms")
        for key, val in check.details.items():
            if key != 'note':
                print(f"          {key}: {val}")

    print()
    print("   Rapport JSON complet :")
    print()
    print(report.to_json())

    # -------------------------------------------------------
    # 2. Démonstration du health check rapide
    # -------------------------------------------------------
    print()
    print("2. HEALTH CHECK RAPIDE (pour load balancer)")
    print("-" * 40)

    quick_report = perform_health_check(quick=True)
    print(f"   Statut : {quick_report.overall_status.value}")
    print(f"   Durée  : {quick_report.total_response_time_ms:.1f}ms")

    # -------------------------------------------------------
    # 3. Démonstration des logs JSON structurés
    # -------------------------------------------------------
    print()
    print("3. LOGS JSON STRUCTURÉS")
    print("-" * 40)
    print()

    logger = setup_json_logger("blog.demo")

    # Log simple
    logger.info("Application démarrée")

    # Log avec contexte extra
    logger.info(
        "Post créé avec succès",
        extra={
            'post_id': 42,
            'user_id': 7,
            'title': 'Mon premier article Python',
            'action': 'post_create',
        }
    )

    # Log de warning
    logger.warning(
        "Cache miss — requête lente détectée",
        extra={
            'endpoint': '/api/posts/',
            'response_time_ms': 850.2,
            'cache_key': 'posts_list:abc123',
            'threshold_ms': 500,
        }
    )

    # Log d'erreur avec exception
    try:
        x = 1 / 0
    except ZeroDivisionError:
        logger.error(
            "Erreur lors du traitement",
            extra={
                'request_id': 'req_abc123',
                'user_id': 7,
                'endpoint': '/api/posts/42/',
            },
            exc_info=True,
        )

    # Log de sécurité
    logger.warning(
        "Tentative d'accès non autorisé",
        extra={
            'ip': '192.168.1.100',
            'endpoint': '/admin/',
            'user_agent': 'python-requests/2.31.0',
            'attempts': 5,
            'action': 'security_alert',
        }
    )

    # -------------------------------------------------------
    # 4. Analyse des logs
    # -------------------------------------------------------
    print()
    print("4. POURQUOI LES LOGS JSON ?")
    print("-" * 40)
    print()

    comparison = {
        "Log texte classique": {
            "format": "[2026-08-30 10:30:00] ERROR blog.views — Erreur lors du traitement",
            "searchable": False,
            "filterable": False,
            "parseable": False,
        },
        "Log JSON structuré": {
            "format": '{"timestamp": "2026-08-30T10:30:00Z", "level": "ERROR", "post_id": 42, ...}',
            "searchable": True,
            "filterable": True,
            "parseable": True,
        }
    }

    for log_type, props in comparison.items():
        print(f"   {log_type} :")
        print(f"     Format     : {props['format'][:60]}...")
        print(f"     Recherche  : {'Oui (grep, jq)' if props['searchable'] else 'Non (regex complexe)'}")
        print(f"     Filtrage   : {'Oui (jq .post_id == 42)' if props['filterable'] else 'Difficile'}")
        print(f"     Parsing    : {'Oui (Elasticsearch, Loki)' if props['parseable'] else 'Fragile'}")
        print()

    # -------------------------------------------------------
    # 5. Exemple de requête sur les logs JSON
    # -------------------------------------------------------
    print("5. ANALYSER LES LOGS JSON EN CLI")
    print("-" * 40)
    print()
    print("   # Voir tous les logs d'erreur :")
    print('   docker logs blog_api | jq \'select(.level == "ERROR")\'')
    print()
    print("   # Voir les logs d'un post spécifique :")
    print('   docker logs blog_api | jq \'select(.post_id == 42)\'')
    print()
    print("   # Calculer le temps de réponse moyen :")
    print("   docker logs blog_api | jq '.response_time_ms' | awk '{sum+=$1; n++} END {print sum/n \"ms\"}'")
    print()
    print("   # Filtrer les requêtes lentes (> 500ms) :")
    print('   docker logs blog_api | jq \'select(.response_time_ms > 500)\'')
    print()

    print("=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    print()
    print("  Health check : /health/ endpoint retournant le statut")
    print("  de DB, Redis, disque et mémoire en JSON")
    print()
    print("  Logs JSON : chaque log contient timestamp, level,")
    print("  message ET tous les champs de contexte (user_id,")
    print("  post_id, endpoint, etc.) — facilement analysables")
    print()
    print("  En production, ces logs sont envoyés à :")
    print("  - Sentry (erreurs automatiques)")
    print("  - Grafana Loki (agrégation et recherche)")
    print("  - ou simplement parsés avec jq en ligne de commande")


if __name__ == "__main__":
    tester()
