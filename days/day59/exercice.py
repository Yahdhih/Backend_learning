"""
Exercice Jour 59 — Variables d'environnement et configuration 12-factor

Objectif : implémenter un chargeur de configuration simple qui :
  1. Lit les variables d'environnement
  2. Lit un fichier .env si présent
  3. Supporte les valeurs par défaut
  4. Supporte le casting de types (int, bool, list, float)
  5. Lève des erreurs claires pour les variables manquantes

Cet exercice simule ce que font python-decouple et django-environ.
Comprendre leur fonctionnement interne vous aidera à les utiliser
et les déboguer efficacement.
"""

import os
import re
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Union

# ─────────────────────────────────────────────────────────────────────────────
# PARTIE 1 : Parseur de fichier .env
# ─────────────────────────────────────────────────────────────────────────────

def parse_env_file(filepath: Union[str, Path]) -> dict[str, str]:
    """
    Lit un fichier .env et retourne un dictionnaire clé → valeur.

    Format supporté :
        KEY=value
        KEY="value with spaces"
        KEY='value with spaces'
        # Commentaires ignorés
        EXPORT KEY=value  (le mot 'export' est ignoré)
        KEY=              (valeur vide)

    Args:
        filepath: chemin vers le fichier .env

    Returns:
        Dictionnaire des variables parsées

    Raises:
        FileNotFoundError: si le fichier n'existe pas
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Fichier .env non trouvé : {filepath}")

    result = {}
    with open(filepath, encoding='utf-8') as f:
        for line_number, line in enumerate(f, start=1):
            # Supprimer les espaces en début/fin
            line = line.strip()

            # Ignorer les lignes vides et les commentaires
            if not line or line.startswith('#'):
                continue

            # Ignorer le mot-clé 'export' (utilisé dans certains shells)
            if line.startswith('export '):
                line = line[7:].strip()

            # Parser KEY=VALUE
            if '=' not in line:
                # Ligne invalide, ignorer
                continue

            key, _, value = line.partition('=')
            key = key.strip()

            # Supprimer les guillemets entourant la valeur
            value = value.strip()
            if len(value) >= 2:
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

            # Ignorer les clés invalides (doivent être des identifiants valides)
            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
                result[key] = value

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PARTIE 2 : Fonctions de casting (conversion de types)
# ─────────────────────────────────────────────────────────────────────────────

class ConfigError(Exception):
    """Exception levée pour les erreurs de configuration."""
    pass


def cast_bool(value: str) -> bool:
    """
    Convertit une chaîne en booléen.

    Valeurs considérées comme True  : '1', 'true', 'yes', 'on'
    Valeurs considérées comme False : '0', 'false', 'no', 'off', ''

    Raises:
        ConfigError: si la valeur n'est pas reconnaissable comme booléen
    """
    value = value.strip().lower()
    if value in ('1', 'true', 'yes', 'on'):
        return True
    elif value in ('0', 'false', 'no', 'off', ''):
        return False
    else:
        raise ConfigError(
            f"Impossible de convertir '{value}' en booléen. "
            f"Valeurs acceptées : 1/0, true/false, yes/no, on/off"
        )


def cast_int(value: str) -> int:
    """
    Convertit une chaîne en entier.

    Raises:
        ConfigError: si la valeur n'est pas un entier valide
    """
    try:
        return int(value.strip())
    except ValueError:
        raise ConfigError(f"Impossible de convertir '{value}' en entier")


def cast_float(value: str) -> float:
    """
    Convertit une chaîne en float.

    Raises:
        ConfigError: si la valeur n'est pas un float valide
    """
    try:
        return float(value.strip())
    except ValueError:
        raise ConfigError(f"Impossible de convertir '{value}' en float")


def cast_list(value: str, separator: str = ',') -> list[str]:
    """
    Convertit une chaîne séparée par des virgules (ou autre séparateur)
    en liste de chaînes. Les espaces en début/fin de chaque élément
    sont supprimés. Les éléments vides sont ignorés.

    Exemples :
        "localhost,127.0.0.1"         → ['localhost', '127.0.0.1']
        "localhost, 127.0.0.1, ::1"   → ['localhost', '127.0.0.1', '::1']
        ""                            → []
    """
    if not value.strip():
        return []
    return [item.strip() for item in value.split(separator) if item.strip()]


def cast_path(value: str) -> Path:
    """Convertit une chaîne en objet Path."""
    return Path(value.strip())


# ─────────────────────────────────────────────────────────────────────────────
# PARTIE 3 : La classe Config principale
# ─────────────────────────────────────────────────────────────────────────────

_MISSING = object()  # Sentinel pour distinguer "pas de défaut" de None

T = TypeVar('T')


class Config:
    """
    Chargeur de configuration 12-factor.

    Ordre de priorité (du plus prioritaire au moins prioritaire) :
    1. Variables d'environnement (os.environ)
    2. Fichier .env
    3. Valeur par défaut fournie

    Usage :
        config = Config('.env')

        SECRET_KEY = config('SECRET_KEY')                          # requis
        DEBUG = config('DEBUG', default=False, cast=bool)          # avec défaut
        PORT = config('PORT', default=8000, cast=int)              # entier
        ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=list)         # liste
        SENTRY_DSN = config('SENTRY_DSN', default=None)            # optionnel
    """

    # Mapping des types Python vers les fonctions de cast
    _CAST_MAP: dict[type, Callable] = {
        bool: cast_bool,
        int: cast_int,
        float: cast_float,
        list: cast_list,
        Path: cast_path,
    }

    def __init__(self, env_file: Optional[Union[str, Path]] = None):
        """
        Initialise le chargeur de config.

        Args:
            env_file: chemin vers le fichier .env. Si None, cherche
                      automatiquement .env dans le répertoire courant.
                      Si le fichier n'existe pas, c'est ignoré silencieusement.
        """
        self._env_vars: dict[str, str] = {}

        # Chercher le fichier .env
        if env_file is None:
            env_file = Path('.env')
        else:
            env_file = Path(env_file)

        # Charger le fichier .env s'il existe
        if env_file.exists():
            try:
                self._env_vars = parse_env_file(env_file)
            except Exception as e:
                # Erreur non fatale : on log mais on continue
                import warnings
                warnings.warn(f"Impossible de lire {env_file}: {e}", stacklevel=2)

    def __call__(
        self,
        key: str,
        default: Any = _MISSING,
        cast: Optional[Union[type, Callable]] = None,
    ) -> Any:
        """
        Récupère une variable de configuration.

        Args:
            key: nom de la variable (ex: 'SECRET_KEY')
            default: valeur par défaut si la variable est absente.
                     Si non fourni et variable absente, lève ConfigError.
            cast: type ou fonction de conversion.
                  Peut être bool, int, float, list, Path, ou toute callable.

        Returns:
            La valeur de la variable, castée si cast est fourni.

        Raises:
            ConfigError: si la variable est requise et absente.
            ConfigError: si le cast échoue.
        """
        # 1. Chercher dans os.environ (priorité maximale)
        raw_value = os.environ.get(key, _MISSING)

        # 2. Chercher dans le fichier .env
        if raw_value is _MISSING:
            raw_value = self._env_vars.get(key, _MISSING)

        # 3. Variable absente
        if raw_value is _MISSING:
            if default is _MISSING:
                raise ConfigError(
                    f"Variable de configuration requise mais absente : '{key}'\n"
                    f"Définissez '{key}' dans votre fichier .env ou "
                    f"comme variable d'environnement."
                )
            # Appliquer le cast sur la valeur par défaut si c'est une chaîne
            if default is not None and cast is not None and isinstance(default, str):
                return self._apply_cast(default, cast, key)
            return default

        # 4. Appliquer le cast si demandé
        if cast is not None:
            return self._apply_cast(raw_value, cast, key)

        return raw_value

    def _apply_cast(self, value: str, cast: Union[type, Callable], key: str) -> Any:
        """Applique la fonction de conversion sur la valeur."""
        # Résoudre le cast (type Python → fonction)
        cast_fn = self._CAST_MAP.get(cast, cast)

        try:
            return cast_fn(value)
        except ConfigError:
            raise  # Re-raise avec le message déjà formaté
        except Exception as e:
            raise ConfigError(
                f"Erreur de conversion pour '{key}': "
                f"impossible de convertir '{value}' avec {cast}: {e}"
            ) from e

    def get_all(self) -> dict[str, str]:
        """
        Retourne toutes les variables disponibles (env vars + .env).
        Les variables d'environnement ont la priorité.
        """
        merged = dict(self._env_vars)  # .env en base
        merged.update(os.environ)      # os.environ écrase le .env
        return merged

    def keys_from_env_file(self) -> list[str]:
        """Retourne la liste des clés définies dans le fichier .env."""
        return list(self._env_vars.keys())

    def __repr__(self) -> str:
        n = len(self._env_vars)
        return f"Config(env_vars_from_file={n})"


# ─────────────────────────────────────────────────────────────────────────────
# PARTIE 4 : Validation de la configuration
# ─────────────────────────────────────────────────────────────────────────────

def validate_django_config(config: Config) -> list[str]:
    """
    Valide qu'une configuration Django minimale est présente.

    Returns:
        Liste de messages d'erreur (vide si tout est OK)
    """
    errors = []

    # Vérifier SECRET_KEY
    try:
        secret_key = config('SECRET_KEY')
        if len(secret_key) < 32:
            errors.append(
                f"SECRET_KEY trop courte ({len(secret_key)} chars). "
                f"Minimum recommandé : 50 caractères."
            )
        if 'insecure' in secret_key.lower() or 'changeme' in secret_key.lower():
            errors.append("SECRET_KEY semble être une valeur de développement non sécurisée.")
    except ConfigError as e:
        errors.append(str(e))

    # Vérifier DEBUG
    try:
        debug = config('DEBUG', default='False', cast=bool)
        if debug:
            errors.append(
                "ATTENTION : DEBUG=True. Ne jamais activer en production !"
            )
    except ConfigError as e:
        errors.append(str(e))

    # Vérifier ALLOWED_HOSTS si DEBUG=False
    try:
        debug = config('DEBUG', default='False', cast=bool)
        if not debug:
            hosts = config('ALLOWED_HOSTS', default='', cast=list)
            if not hosts:
                errors.append(
                    "ALLOWED_HOSTS est vide mais DEBUG=False. "
                    "Django refusera toutes les requêtes !"
                )
    except ConfigError:
        pass  # Déjà signalé ci-dessus

    # Vérifier DATABASE_URL
    try:
        db_url = config('DATABASE_URL')
        if not db_url.startswith(('postgresql://', 'postgres://', 'sqlite://', 'mysql://')):
            errors.append(f"DATABASE_URL ne semble pas être une URL de base de données valide.")
    except ConfigError as e:
        errors.append(str(e))

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# PARTIE 5 : Générateur de settings Django
# ─────────────────────────────────────────────────────────────────────────────

def generate_settings_snippet(env_file: Optional[Path] = None) -> str:
    """
    Génère un snippet de settings.py basé sur les variables trouvées
    dans le fichier .env. Utile pour bootstrapper un nouveau projet.

    Returns:
        Chaîne de caractères avec le code Python du snippet
    """
    config = Config(env_file)
    keys = config.keys_from_env_file()

    lines = [
        "# settings.py — généré automatiquement depuis .env",
        "from pathlib import Path",
        "from decouple import config, Csv",
        "",
        "BASE_DIR = Path(__file__).resolve().parent.parent",
        "",
    ]

    # Inférer le type de chaque variable et générer la ligne correspondante
    for key in sorted(keys):
        try:
            value = config(key)
        except ConfigError:
            continue

        # Inférer le type
        if key in ('DEBUG', 'USE_I18N', 'USE_TZ', 'USE_L10N'):
            line = f"{key} = config('{key}', default=False, cast=bool)"
        elif key in ('PORT', 'EMAIL_PORT'):
            line = f"{key} = config('{key}', default=8000, cast=int)"
        elif key in ('ALLOWED_HOSTS', 'CORS_ALLOWED_ORIGINS'):
            line = f"{key} = config('{key}', default='localhost', cast=Csv())"
        elif key == 'DATABASE_URL':
            lines.extend([
                "import dj_database_url",
                f"DATABASES = {{'default': dj_database_url.parse(config('DATABASE_URL'))}}",
            ])
            continue
        else:
            line = f"{key} = config('{key}')"

        lines.append(line)

    return '\n'.join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# FONCTION DE TEST
# ─────────────────────────────────────────────────────────────────────────────

def tester():
    """
    Teste toutes les fonctionnalités du chargeur de configuration.
    """
    import tempfile
    import os as _os

    print("=" * 60)
    print("TEST DU CHARGEUR DE CONFIGURATION 12-FACTOR")
    print("=" * 60)

    # ── Test 1 : parse_env_file ──────────────────────────────────────────────
    print("\n[1] Test parse_env_file")

    env_content = """\
# Commentaire
SECRET_KEY=ma-cle-tres-secrete-de-50-caracteres-minimum-ok
DEBUG=True
PORT=8000
ALLOWED_HOSTS=localhost,127.0.0.1,mondomaine.com
DATABASE_URL=postgresql://user:pass@localhost:5432/mondb
EMPTY_VALUE=
QUOTED_VALUE="valeur avec des espaces"
SINGLE_QUOTED='autre valeur'
export EXPORTED=valeur-exportee
# Une autre ligne de commentaire
INVALID LINE WITHOUT EQUALS SIGN
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(env_content)
        env_path = Path(f.name)

    parsed = parse_env_file(env_path)
    assert parsed['SECRET_KEY'] == 'ma-cle-tres-secrete-de-50-caracteres-minimum-ok', \
        f"SECRET_KEY incorrect: {parsed['SECRET_KEY']}"
    assert parsed['DEBUG'] == 'True', f"DEBUG incorrect: {parsed['DEBUG']}"
    assert parsed['PORT'] == '8000', f"PORT incorrect: {parsed['PORT']}"
    assert parsed['EMPTY_VALUE'] == '', f"EMPTY_VALUE doit être vide: {parsed['EMPTY_VALUE']}"
    assert parsed['QUOTED_VALUE'] == 'valeur avec des espaces', \
        f"QUOTED_VALUE incorrect: {parsed['QUOTED_VALUE']}"
    assert parsed['SINGLE_QUOTED'] == 'autre valeur', \
        f"SINGLE_QUOTED incorrect: {parsed['SINGLE_QUOTED']}"
    assert parsed['EXPORTED'] == 'valeur-exportee', \
        f"EXPORTED incorrect: {parsed['EXPORTED']}"
    assert 'INVALID' not in parsed or 'INVALID' not in str(parsed), \
        "La ligne invalide ne devrait pas être parsée"
    print(f"  parse_env_file : {len(parsed)} variables parsées avec succès")

    # ── Test 2 : cast_bool ───────────────────────────────────────────────────
    print("\n[2] Test cast_bool")
    true_values = ['1', 'true', 'True', 'TRUE', 'yes', 'YES', 'on', 'ON']
    false_values = ['0', 'false', 'False', 'FALSE', 'no', 'NO', 'off', 'OFF', '']

    for v in true_values:
        assert cast_bool(v) is True, f"'{v}' devrait être True"
    for v in false_values:
        assert cast_bool(v) is False, f"'{v}' devrait être False"

    try:
        cast_bool('maybe')
        assert False, "cast_bool('maybe') devrait lever ConfigError"
    except ConfigError:
        pass  # Attendu

    print("  cast_bool : toutes les valeurs reconnues correctement")

    # ── Test 3 : cast_int ────────────────────────────────────────────────────
    print("\n[3] Test cast_int")
    assert cast_int('8000') == 8000
    assert cast_int('  42  ') == 42
    assert cast_int('-1') == -1

    try:
        cast_int('pas-un-entier')
        assert False, "cast_int('pas-un-entier') devrait lever ConfigError"
    except ConfigError:
        pass

    print("  cast_int : OK")

    # ── Test 4 : cast_list ───────────────────────────────────────────────────
    print("\n[4] Test cast_list")
    assert cast_list('localhost,127.0.0.1') == ['localhost', '127.0.0.1']
    assert cast_list('  a , b , c  ') == ['a', 'b', 'c']
    assert cast_list('') == []
    assert cast_list('un-seul-element') == ['un-seul-element']
    assert cast_list('a::b::c', separator='::') == ['a', 'b', 'c']

    print("  cast_list : OK")

    # ── Test 5 : Config depuis fichier .env ──────────────────────────────────
    print("\n[5] Test Config depuis fichier .env")
    config = Config(env_path)

    secret = config('SECRET_KEY')
    assert secret == 'ma-cle-tres-secrete-de-50-caracteres-minimum-ok'

    debug = config('DEBUG', cast=bool)
    assert debug is True, f"DEBUG devrait être True: {debug}"

    port = config('PORT', cast=int)
    assert port == 8000, f"PORT devrait être 8000: {port}"

    hosts = config('ALLOWED_HOSTS', cast=list)
    assert hosts == ['localhost', '127.0.0.1', 'mondomaine.com'], f"Hosts: {hosts}"

    print("  Config depuis .env : OK")

    # ── Test 6 : Valeurs par défaut ──────────────────────────────────────────
    print("\n[6] Test valeurs par défaut")
    config2 = Config(env_path)

    # Variable absente avec défaut
    timeout = config2('TIMEOUT', default=30, cast=int)
    assert timeout == 30, f"TIMEOUT devrait être 30: {timeout}"

    sentry = config2('SENTRY_DSN', default=None)
    assert sentry is None, f"SENTRY_DSN devrait être None: {sentry}"

    print("  Valeurs par défaut : OK")

    # ── Test 7 : Variable requise absente ────────────────────────────────────
    print("\n[7] Test variable requise absente")
    config3 = Config(env_path)

    try:
        config3('VARIABLE_QUI_NEXISTE_PAS')
        assert False, "Devrait lever ConfigError"
    except ConfigError as e:
        assert 'VARIABLE_QUI_NEXISTE_PAS' in str(e)
        print(f"  ConfigError levée correctement : {e}")

    # ── Test 8 : Priorité os.environ > .env ─────────────────────────────────
    print("\n[8] Test priorité os.environ > .env")
    _os.environ['PORT'] = '9999'
    config4 = Config(env_path)
    port_from_env = config4('PORT', cast=int)
    assert port_from_env == 9999, \
        f"os.environ devrait avoir priorité: {port_from_env}"
    del _os.environ['PORT']

    print("  Priorité os.environ > .env : OK")

    # ── Test 9 : Validation de config Django ─────────────────────────────────
    print("\n[9] Test validate_django_config")

    # Config valide (DEBUG=True → avertissement, mais pas bloquant)
    errors = validate_django_config(config)
    # On s'attend à un avertissement pour DEBUG=True
    debug_warnings = [e for e in errors if 'DEBUG' in e]
    print(f"  Avertissements DEBUG : {len(debug_warnings)}")

    # Config avec SECRET_KEY manquante
    _os.environ.pop('SECRET_KEY', None)
    config_bad = Config(env_path)
    # Sauvegarder et supprimer SECRET_KEY du .env parsé
    config_bad._env_vars.pop('SECRET_KEY', None)
    errors_bad = validate_django_config(config_bad)
    assert any('SECRET_KEY' in e for e in errors_bad), \
        f"Devrait signaler SECRET_KEY manquante: {errors_bad}"
    print(f"  Validation : erreur SECRET_KEY détectée")

    # ── Test 10 : generate_settings_snippet ──────────────────────────────────
    print("\n[10] Test generate_settings_snippet")
    snippet = generate_settings_snippet(env_path)
    assert 'from decouple import' in snippet
    assert 'DATABASE_URL' in snippet or 'SECRET_KEY' in snippet
    print(f"  Snippet généré ({len(snippet)} caractères)")

    # Nettoyage
    env_path.unlink()

    print("\n" + "=" * 60)
    print("TOUS LES TESTS SONT PASSÉS")
    print("=" * 60)

    # ── Démonstration complète ───────────────────────────────────────────────
    print("\n--- DÉMONSTRATION ---")
    print("Création d'une configuration type projet Django :\n")

    demo_env = """\
SECRET_KEY=w*7v2$pk(z9!j1mxn8qvb3yl6eros4fuita0hdcg-5wphk_2js
DEBUG=False
ALLOWED_HOSTS=mondomaine.com,www.mondomaine.com
DATABASE_URL=postgresql://user:password@db.mondomaine.com:5432/prod_db
REDIS_URL=redis://redis.mondomaine.com:6379/0
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
WORKERS=9
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(demo_env)
        demo_path = Path(f.name)

    demo_config = Config(demo_path)

    print(f"  SECRET_KEY    : {'*' * 20}...  ({len(demo_config('SECRET_KEY'))} chars)")
    print(f"  DEBUG         : {demo_config('DEBUG', cast=bool)}")
    print(f"  ALLOWED_HOSTS : {demo_config('ALLOWED_HOSTS', cast=list)}")
    print(f"  DATABASE_URL  : {demo_config('DATABASE_URL')[:40]}...")
    print(f"  WORKERS       : {demo_config('WORKERS', default=4, cast=int)}")
    print(f"  SENTRY_DSN    : {demo_config('SENTRY_DSN', default=None)}")

    print("\n  Settings snippet généré :")
    print("  " + "-" * 40)
    for line in generate_settings_snippet(demo_path).split('\n')[:10]:
        print(f"  {line}")
    print("  ...")

    demo_path.unlink()


# ─────────────────────────────────────────────────────────────────────────────
# EXERCICE — À COMPLÉTER
# ─────────────────────────────────────────────────────────────────────────────

"""
EXERCICE 1 : Ajouter le support des commentaires inline

Actuellement, une ligne comme :
    PORT=8000  # port d'écoute

est parsée comme value = "8000  # port d'écoute"
Modifiez parse_env_file pour supprimer les commentaires inline.
(Attention : ne pas supprimer le # dans les valeurs quotées comme "pass#word")


EXERCICE 2 : Ajouter cast_json

Implémentez cast_json(value: str) -> Any qui convertit une chaîne JSON
en objet Python.

Exemple :
    DATABASE_REPLICA_HOSTS=["db1.example.com", "db2.example.com"]
    config('DATABASE_REPLICA_HOSTS', cast=cast_json)
    → ['db1.example.com', 'db2.example.com']


EXERCICE 3 : Méthode Config.require_all()

Ajoutez une méthode Config.require_all(*keys) qui vérifie que toutes
les variables listées sont présentes, et lève une ConfigError avec
TOUTES les variables manquantes en une seule fois (pas une par une).

Usage :
    config.require_all('SECRET_KEY', 'DATABASE_URL', 'REDIS_URL')
    # Lève ConfigError: "Variables manquantes: REDIS_URL, DATABASE_URL"


EXERCICE 4 : Cache des valeurs

Ajoutez un mécanisme de cache dans Config.__call__ pour ne pas relire
os.environ à chaque appel pour la même clé. Attention : le cache doit
pouvoir être invalidé.


EXERCICE 5 : Support du chiffrement

Implémentez Config.decrypt(key, encryption_key) qui suppose que la valeur
dans .env est chiffrée avec Fernet (bibliothèque cryptography) et la
déchiffre à la volée.

pip install cryptography

from cryptography.fernet import Fernet
"""


if __name__ == '__main__':
    tester()
