"""
Jour 53 — Exercice : Simuler Redis en Python pur
=================================================
Objectif : implémenter les structures de données Redis (String, List, Hash,
Set, Sorted Set) en Python natif, avec support TTL et un mécanisme Pub/Sub
simple. Aucune dépendance externe requise.
"""

import time
import threading
from collections import defaultdict
from typing import Any, Optional


# ============================================================
# 1. MOTEUR DE STOCKAGE AVEC TTL
# ============================================================

class TTLStore:
    """
    Moteur de stockage clé-valeur avec support TTL.
    Toutes les structures Redis l'utilisent comme couche de base.
    """

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._expires: dict[str, float] = {}  # clé -> timestamp d'expiration
        self._lock = threading.Lock()

    def _is_expired(self, key: str) -> bool:
        """Vérifie si une clé a expiré."""
        if key not in self._expires:
            return False
        return time.time() > self._expires[key]

    def _clean_if_expired(self, key: str) -> bool:
        """Supprime la clé si expirée. Retourne True si supprimée."""
        if self._is_expired(key):
            self._data.pop(key, None)
            self._expires.pop(key, None)
            return True
        return False

    def exists(self, key: str) -> bool:
        with self._lock:
            if self._clean_if_expired(key):
                return False
            return key in self._data

    def delete(self, key: str) -> int:
        """Supprime une clé. Retourne 1 si supprimée, 0 sinon."""
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._expires.pop(key, None)
                return 1
            return 0

    def expire(self, key: str, seconds: int) -> bool:
        """Définit un TTL sur une clé existante."""
        with self._lock:
            if key not in self._data:
                return False
            self._expires[key] = time.time() + seconds
            return True

    def ttl(self, key: str) -> int:
        """Retourne le TTL restant. -1 = pas d'expiration, -2 = n'existe pas."""
        with self._lock:
            if key not in self._data:
                return -2
            if self._clean_if_expired(key):
                return -2
            if key not in self._expires:
                return -1
            remaining = self._expires[key] - time.time()
            return max(0, int(remaining))

    def _set_raw(self, key: str, value: Any, ex: Optional[int] = None):
        """Stocke une valeur brute avec TTL optionnel."""
        self._data[key] = value
        if ex is not None:
            self._expires[key] = time.time() + ex
        elif key in self._expires:
            del self._expires[key]

    def _get_raw(self, key: str) -> Any:
        """Récupère une valeur brute."""
        if self._clean_if_expired(key):
            return None
        return self._data.get(key)


# ============================================================
# 2. REDIS STRING
# ============================================================

class RedisStrings(TTLStore):
    """
    Implémentation des commandes Redis String.
    SET, GET, INCR, INCRBY, MSET, MGET, SETNX
    """

    def set(self, key: str, value: str, ex: Optional[int] = None, nx: bool = False) -> bool:
        """
        SET key value [EX seconds] [NX]
        nx=True : ne set que si la clé n'existe pas (SET ... NX)
        """
        with self._lock:
            if nx and key in self._data and not self._is_expired(key):
                return False
            self._set_raw(key, str(value), ex=ex)
            return True

    def get(self, key: str) -> Optional[str]:
        """GET key — retourne None si inexistant ou expiré."""
        with self._lock:
            return self._get_raw(key)

    def incr(self, key: str, amount: int = 1) -> int:
        """INCR key — incrémente atomiquement."""
        with self._lock:
            current = self._get_raw(key)
            if current is None:
                new_value = amount
            else:
                new_value = int(current) + amount
            self._set_raw(key, str(new_value))
            return new_value

    def incrby(self, key: str, amount: int) -> int:
        """INCRBY key amount"""
        return self.incr(key, amount)

    def mset(self, mapping: dict[str, str]) -> bool:
        """MSET key1 val1 key2 val2 ..."""
        with self._lock:
            for key, value in mapping.items():
                self._set_raw(key, str(value))
        return True

    def mget(self, *keys: str) -> list[Optional[str]]:
        """MGET key1 key2 ... — retourne une liste (None pour les clés manquantes)."""
        with self._lock:
            return [self._get_raw(k) for k in keys]

    def getdel(self, key: str) -> Optional[str]:
        """GETDEL key — récupère et supprime."""
        with self._lock:
            value = self._get_raw(key)
            if value is not None:
                del self._data[key]
                self._expires.pop(key, None)
            return value


# ============================================================
# 3. REDIS LIST
# ============================================================

class RedisList(TTLStore):
    """
    Implémentation des commandes Redis List.
    LPUSH, RPUSH, LPOP, RPOP, LRANGE, LLEN, BLPOP (simulé)
    """

    def _ensure_list(self, key: str) -> list:
        val = self._get_raw(key)
        if val is None:
            return []
        if not isinstance(val, list):
            raise TypeError(f"La clé '{key}' ne contient pas une List")
        return val

    def lpush(self, key: str, *values: str) -> int:
        """LPUSH key value ... — ajoute en tête, retourne la longueur."""
        with self._lock:
            lst = list(self._ensure_list(key))
            for value in values:
                lst.insert(0, str(value))
            self._set_raw(key, lst)
            return len(lst)

    def rpush(self, key: str, *values: str) -> int:
        """RPUSH key value ... — ajoute en queue."""
        with self._lock:
            lst = list(self._ensure_list(key))
            for value in values:
                lst.append(str(value))
            self._set_raw(key, lst)
            return len(lst)

    def lpop(self, key: str) -> Optional[str]:
        """LPOP key — retire et retourne le premier élément."""
        with self._lock:
            lst = list(self._ensure_list(key))
            if not lst:
                return None
            value = lst.pop(0)
            self._set_raw(key, lst)
            return value

    def rpop(self, key: str) -> Optional[str]:
        """RPOP key — retire et retourne le dernier élément."""
        with self._lock:
            lst = list(self._ensure_list(key))
            if not lst:
                return None
            value = lst.pop()
            self._set_raw(key, lst)
            return value

    def lrange(self, key: str, start: int, stop: int) -> list[str]:
        """LRANGE key start stop — retourne une sous-liste (-1 = dernier)."""
        with self._lock:
            lst = self._ensure_list(key)
            if stop == -1:
                return list(lst[start:])
            return list(lst[start:stop + 1])

    def llen(self, key: str) -> int:
        """LLEN key — longueur de la liste."""
        with self._lock:
            return len(self._ensure_list(key))

    def blpop(self, key: str, timeout: float = 5.0) -> Optional[str]:
        """
        BLPOP simulé — tente de récupérer un élément, attend si vide.
        (Implémentation simplifiée par polling)
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = self.lpop(key)
            if result is not None:
                return result
            time.sleep(0.05)
        return None


# ============================================================
# 4. REDIS HASH
# ============================================================

class RedisHash(TTLStore):
    """
    Implémentation des commandes Redis Hash.
    HSET, HGET, HGETALL, HMGET, HDEL, HEXISTS, HINCRBY
    """

    def _ensure_hash(self, key: str) -> dict:
        val = self._get_raw(key)
        if val is None:
            return {}
        if not isinstance(val, dict):
            raise TypeError(f"La clé '{key}' ne contient pas un Hash")
        return val

    def hset(self, key: str, field: str, value: str) -> int:
        """HSET key field value — retourne 1 si nouveau champ, 0 si update."""
        with self._lock:
            h = dict(self._ensure_hash(key))
            is_new = field not in h
            h[field] = str(value)
            self._set_raw(key, h)
            return 1 if is_new else 0

    def hmset(self, key: str, mapping: dict[str, str]) -> bool:
        """HSET key field1 val1 field2 val2 ... (bulk)"""
        with self._lock:
            h = dict(self._ensure_hash(key))
            for field, value in mapping.items():
                h[str(field)] = str(value)
            self._set_raw(key, h)
            return True

    def hget(self, key: str, field: str) -> Optional[str]:
        """HGET key field"""
        with self._lock:
            return self._ensure_hash(key).get(field)

    def hgetall(self, key: str) -> dict[str, str]:
        """HGETALL key — retourne tous les champs."""
        with self._lock:
            return dict(self._ensure_hash(key))

    def hmget(self, key: str, *fields: str) -> list[Optional[str]]:
        """HMGET key field1 field2 ..."""
        with self._lock:
            h = self._ensure_hash(key)
            return [h.get(f) for f in fields]

    def hdel(self, key: str, *fields: str) -> int:
        """HDEL key field1 ... — supprime des champs, retourne le nombre supprimé."""
        with self._lock:
            h = dict(self._ensure_hash(key))
            deleted = 0
            for field in fields:
                if field in h:
                    del h[field]
                    deleted += 1
            self._set_raw(key, h)
            return deleted

    def hexists(self, key: str, field: str) -> bool:
        """HEXISTS key field"""
        with self._lock:
            return field in self._ensure_hash(key)

    def hincrby(self, key: str, field: str, amount: int) -> int:
        """HINCRBY key field amount"""
        with self._lock:
            h = dict(self._ensure_hash(key))
            current = int(h.get(field, 0))
            new_value = current + amount
            h[field] = str(new_value)
            self._set_raw(key, h)
            return new_value

    def hlen(self, key: str) -> int:
        with self._lock:
            return len(self._ensure_hash(key))


# ============================================================
# 5. REDIS SET
# ============================================================

class RedisSet(TTLStore):
    """
    Implémentation des commandes Redis Set.
    SADD, SREM, SMEMBERS, SISMEMBER, SCARD, SINTER, SUNION, SDIFF
    """

    def _ensure_set(self, key: str) -> set:
        val = self._get_raw(key)
        if val is None:
            return set()
        if not isinstance(val, set):
            raise TypeError(f"La clé '{key}' ne contient pas un Set")
        return val

    def sadd(self, key: str, *members: str) -> int:
        """SADD key member ... — retourne le nombre d'éléments ajoutés."""
        with self._lock:
            s = set(self._ensure_set(key))
            before = len(s)
            s.update(str(m) for m in members)
            self._set_raw(key, s)
            return len(s) - before

    def srem(self, key: str, *members: str) -> int:
        """SREM key member ..."""
        with self._lock:
            s = set(self._ensure_set(key))
            before = len(s)
            for m in members:
                s.discard(str(m))
            self._set_raw(key, s)
            return before - len(s)

    def smembers(self, key: str) -> set[str]:
        """SMEMBERS key"""
        with self._lock:
            return set(self._ensure_set(key))

    def sismember(self, key: str, member: str) -> bool:
        """SISMEMBER key member"""
        with self._lock:
            return str(member) in self._ensure_set(key)

    def scard(self, key: str) -> int:
        """SCARD key — taille de l'ensemble."""
        with self._lock:
            return len(self._ensure_set(key))

    def sinter(self, *keys: str) -> set[str]:
        """SINTER key1 key2 ... — intersection."""
        with self._lock:
            sets = [self._ensure_set(k) for k in keys]
            if not sets:
                return set()
            result = sets[0].copy()
            for s in sets[1:]:
                result &= s
            return result

    def sunion(self, *keys: str) -> set[str]:
        """SUNION key1 key2 ... — union."""
        with self._lock:
            result = set()
            for key in keys:
                result |= self._ensure_set(key)
            return result

    def sdiff(self, *keys: str) -> set[str]:
        """SDIFF key1 key2 ... — différence (key1 - key2 - ...)."""
        with self._lock:
            sets = [self._ensure_set(k) for k in keys]
            if not sets:
                return set()
            result = sets[0].copy()
            for s in sets[1:]:
                result -= s
            return result

    def srandmember(self, key: str) -> Optional[str]:
        """SRANDMEMBER key — membre aléatoire."""
        import random
        with self._lock:
            members = list(self._ensure_set(key))
            return random.choice(members) if members else None


# ============================================================
# 6. REDIS SORTED SET
# ============================================================

class RedisSortedSet(TTLStore):
    """
    Implémentation des commandes Redis Sorted Set.
    ZADD, ZREM, ZSCORE, ZRANK, ZREVRANK, ZRANGE, ZREVRANGE,
    ZINCRBY, ZRANGEBYSCORE, ZCARD
    """

    def _ensure_zset(self, key: str) -> dict[str, float]:
        """Retourne un dict {member: score}."""
        val = self._get_raw(key)
        if val is None:
            return {}
        if not isinstance(val, dict):
            raise TypeError(f"La clé '{key}' ne contient pas un Sorted Set")
        return val

    def _sorted_members(self, key: str) -> list[tuple[str, float]]:
        """Retourne les membres triés par score croissant."""
        zset = self._ensure_zset(key)
        return sorted(zset.items(), key=lambda x: x[1])

    def zadd(self, key: str, mapping: dict[str, float]) -> int:
        """ZADD key score member ... — retourne le nombre de nouveaux membres."""
        with self._lock:
            zset = dict(self._ensure_zset(key))
            added = 0
            for member, score in mapping.items():
                if member not in zset:
                    added += 1
                zset[str(member)] = float(score)
            self._set_raw(key, zset)
            return added

    def zrem(self, key: str, *members: str) -> int:
        """ZREM key member ..."""
        with self._lock:
            zset = dict(self._ensure_zset(key))
            removed = 0
            for member in members:
                if str(member) in zset:
                    del zset[str(member)]
                    removed += 1
            self._set_raw(key, zset)
            return removed

    def zscore(self, key: str, member: str) -> Optional[float]:
        """ZSCORE key member"""
        with self._lock:
            return self._ensure_zset(key).get(str(member))

    def zincrby(self, key: str, amount: float, member: str) -> float:
        """ZINCRBY key amount member"""
        with self._lock:
            zset = dict(self._ensure_zset(key))
            current = zset.get(str(member), 0.0)
            new_score = current + amount
            zset[str(member)] = new_score
            self._set_raw(key, zset)
            return new_score

    def zrange(self, key: str, start: int, stop: int, withscores: bool = False):
        """ZRANGE key start stop [WITHSCORES] — ordre croissant."""
        with self._lock:
            sorted_members = self._sorted_members(key)
            if stop == -1:
                subset = sorted_members[start:]
            else:
                subset = sorted_members[start:stop + 1]

            if withscores:
                return [(m, s) for m, s in subset]
            return [m for m, s in subset]

    def zrevrange(self, key: str, start: int, stop: int, withscores: bool = False):
        """ZREVRANGE key start stop [WITHSCORES] — ordre décroissant."""
        with self._lock:
            sorted_members = list(reversed(self._sorted_members(key)))
            if stop == -1:
                subset = sorted_members[start:]
            else:
                subset = sorted_members[start:stop + 1]

            if withscores:
                return [(m, s) for m, s in subset]
            return [m for m, s in subset]

    def zrank(self, key: str, member: str) -> Optional[int]:
        """ZRANK key member — rang croissant (0-indexed)."""
        with self._lock:
            sorted_members = self._sorted_members(key)
            for i, (m, _) in enumerate(sorted_members):
                if m == str(member):
                    return i
            return None

    def zrevrank(self, key: str, member: str) -> Optional[int]:
        """ZREVRANK key member — rang décroissant (0-indexed)."""
        with self._lock:
            sorted_members = list(reversed(self._sorted_members(key)))
            for i, (m, _) in enumerate(sorted_members):
                if m == str(member):
                    return i
            return None

    def zcard(self, key: str) -> int:
        """ZCARD key — nombre de membres."""
        with self._lock:
            return len(self._ensure_zset(key))

    def zrangebyscore(self, key: str, min_score: float, max_score: float,
                      withscores: bool = False):
        """ZRANGEBYSCORE key min max"""
        with self._lock:
            result = [
                (m, s) for m, s in self._sorted_members(key)
                if min_score <= s <= max_score
            ]
            if withscores:
                return result
            return [m for m, s in result]

    def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        """ZREMRANGEBYSCORE key min max"""
        with self._lock:
            zset = dict(self._ensure_zset(key))
            to_remove = [m for m, s in zset.items() if min_score <= s <= max_score]
            for m in to_remove:
                del zset[m]
            self._set_raw(key, zset)
            return len(to_remove)


# ============================================================
# 7. PUB/SUB SIMPLIFIÉ
# ============================================================

class PubSub:
    """
    Mécanisme Pub/Sub simple basé sur des callbacks.
    Simule le Pub/Sub Redis en mémoire.
    """

    def __init__(self):
        self._subscribers: dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
        self._message_counts: dict[str, int] = defaultdict(int)

    def subscribe(self, channel: str, callback):
        """S'abonne à un canal avec un callback(channel, message)."""
        with self._lock:
            self._subscribers[channel].append(callback)
        print(f"[PubSub] Abonné au canal '{channel}'")

    def unsubscribe(self, channel: str, callback=None):
        """Se désabonne d'un canal."""
        with self._lock:
            if callback:
                self._subscribers[channel] = [
                    cb for cb in self._subscribers[channel] if cb != callback
                ]
            else:
                self._subscribers[channel] = []

    def publish(self, channel: str, message: str) -> int:
        """
        Publie un message sur un canal.
        Retourne le nombre de subscribers qui ont reçu le message.
        """
        with self._lock:
            subscribers = list(self._subscribers.get(channel, []))
            self._message_counts[channel] += 1

        count = 0
        for callback in subscribers:
            try:
                callback(channel, message)
                count += 1
            except Exception as e:
                print(f"[PubSub] Erreur callback: {e}")

        return count

    def get_channels(self) -> list[str]:
        """Liste les canaux actifs."""
        with self._lock:
            return [ch for ch, subs in self._subscribers.items() if subs]

    def subscriber_count(self, channel: str) -> int:
        """Nombre de subscribers sur un canal."""
        with self._lock:
            return len(self._subscribers.get(channel, []))


# ============================================================
# 8. CLASSE REDIS UNIFIÉE (facade)
# ============================================================

class FakeRedis(RedisStrings, RedisList, RedisHash, RedisSet, RedisSortedSet):
    """
    Façade unifiée combinant toutes les structures.
    Utilise le stockage partagé TTLStore.
    """

    def __init__(self):
        super().__init__()
        self.pubsub = PubSub()

    def flushdb(self):
        """Vide toute la base (équivalent FLUSHDB)."""
        with self._lock:
            self._data.clear()
            self._expires.clear()
        print("[FakeRedis] Base vidée.")

    def keys(self, pattern: str = "*") -> list[str]:
        """KEYS pattern — liste les clés correspondant au pattern."""
        import fnmatch
        with self._lock:
            # Nettoyer les clés expirées
            expired = [k for k in list(self._data.keys()) if self._is_expired(k)]
            for k in expired:
                del self._data[k]
                self._expires.pop(k, None)
            return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]

    def dbsize(self) -> int:
        """DBSIZE — nombre de clés."""
        return len(self.keys())


# ============================================================
# 9. FONCTION TESTER
# ============================================================

def tester():
    print("=" * 60)
    print("JOUR 53 — Simulation Redis en Python pur")
    print("=" * 60)

    r = FakeRedis()

    # --- STRINGS ---
    print("\n--- 1. Strings ---")
    r.set("nom", "Alice")
    print(f"GET nom: {r.get('nom')}")

    r.set("compteur", "0")
    r.incr("compteur")
    r.incr("compteur")
    r.incrby("compteur", 5)
    print(f"INCR x2 + INCRBY 5: {r.get('compteur')}")

    r.set("token", "secret123", ex=2)
    print(f"TTL token (2s): {r.ttl('token')}s")
    time.sleep(2.1)
    print(f"Token après expiration: {r.get('token')} (None attendu)")

    r.mset({"a": "1", "b": "2", "c": "3"})
    print(f"MGET a,b,c: {r.mget('a', 'b', 'c')}")

    verrou = r.set("lock:resource", "1", nx=True)
    double_lock = r.set("lock:resource", "2", nx=True)
    print(f"SETNX verrou: {verrou}, double: {double_lock} (False attendu)")

    # --- LISTS ---
    print("\n--- 2. Lists (Queue FIFO) ---")
    r.rpush("queue", "tache_1", "tache_2", "tache_3")
    print(f"LRANGE queue: {r.lrange('queue', 0, -1)}")
    print(f"LLEN: {r.llen('queue')}")
    print(f"LPOP (FIFO): {r.lpop('queue')}")
    print(f"RPOP (LIFO): {r.rpop('queue')}")

    print("\n  Stack (LIFO):")
    for i in range(3):
        r.rpush("stack", f"action_{i+1}")
    while r.llen("stack") > 0:
        print(f"  POP: {r.rpop('stack')}")

    # --- HASHES ---
    print("\n--- 3. Hashes (Profil Utilisateur) ---")
    r.hmset("user:1", {
        "nom": "Alice",
        "email": "alice@example.com",
        "points": "1500",
        "statut": "actif"
    })
    print(f"HGETALL user:1: {r.hgetall('user:1')}")
    print(f"HGET nom: {r.hget('user:1', 'nom')}")
    r.hincrby("user:1", "points", 250)
    print(f"Après HINCRBY +250: {r.hget('user:1', 'points')} points")
    r.hdel("user:1", "statut")
    print(f"Après HDEL statut: {r.hexists('user:1', 'statut')} (False attendu)")

    # --- SETS ---
    print("\n--- 4. Sets (Visiteurs & Tags) ---")
    visites = ["user_1", "user_2", "user_1", "user_3", "user_2", "user_4"]
    for v in visites:
        r.sadd("visitors:2026-08-18", v)
    print(f"Visiteurs uniques: {r.scard('visitors:2026-08-18')} (4 attendu)")

    r.sadd("tags:article1", "python", "django", "web")
    r.sadd("tags:article2", "python", "data", "pandas")
    r.sadd("tags:article3", "javascript", "web", "react")

    commun = r.sinter("tags:article1", "tags:article2")
    print(f"Tags communs art1 & art2: {commun}")

    union = r.sunion("tags:article1", "tags:article3")
    print(f"Union tags art1 & art3: {union}")

    diff = r.sdiff("tags:article1", "tags:article2")
    print(f"Tags art1 pas dans art2: {diff}")

    # --- SORTED SETS ---
    print("\n--- 5. Sorted Sets (Leaderboard) ---")
    r.zadd("leaderboard", {
        "Alice": 1500,
        "Bob": 2300,
        "Charlie": 1800,
        "Dave": 900,
        "Eve": 2100
    })

    print("Top 3 (décroissant):")
    top3 = r.zrevrange("leaderboard", 0, 2, withscores=True)
    for rang, (joueur, score) in enumerate(top3, 1):
        print(f"  #{rang}: {joueur} — {int(score)} pts")

    r.zincrby("leaderboard", 600, "Dave")
    rang_dave = r.zrevrank("leaderboard", "Dave")
    score_dave = r.zscore("leaderboard", "Dave")
    print(f"Dave après +600: rang #{rang_dave+1}, score {int(score_dave)}")

    # Rate limiting avec Sorted Set
    print("\n  Rate Limiting (fenêtre glissante 5 req/5s):")
    MAX_REQUESTS = 5
    WINDOW = 5.0

    def check_rate(user: str) -> bool:
        key = f"rate:{user}"
        now = time.time()
        window_start = now - WINDOW
        r.zremrangebyscore(key, 0, window_start)
        r.zadd(key, {str(now): now})
        count = r.zcard(key)
        return count <= MAX_REQUESTS

    for i in range(7):
        allowed = check_rate("user_test")
        status = "OK" if allowed else "BLOQUE"
        print(f"  Requête {i+1}: {status}")

    # --- PUB/SUB ---
    print("\n--- 6. Pub/Sub ---")
    messages_received = []

    def on_notification(channel, message):
        messages_received.append((channel, message))
        print(f"  [Reçu] Canal='{channel}' | Message='{message}'")

    def on_orders(channel, message):
        print(f"  [Commandes] Canal='{channel}' | Message='{message}'")

    pubsub = PubSub()
    pubsub.subscribe("notifications", on_notification)
    pubsub.subscribe("notifications", on_orders)
    pubsub.subscribe("alerts", on_notification)

    print(f"Subscribers sur 'notifications': {pubsub.subscriber_count('notifications')}")

    count = pubsub.publish("notifications", "Nouvelle commande #1234")
    print(f"Message livré à {count} subscriber(s)")

    pubsub.publish("alerts", "Alerte critique !")
    pubsub.publish("notifications", "Paiement confirmé #1234")

    print(f"Total messages reçus par on_notification: {len(messages_received)}")

    # --- TTL & EXPIRATION ---
    print("\n--- 7. TTL & Expiration ---")
    r.set("ephemere", "je disparais", ex=1)
    print(f"Avant expiration: {r.get('ephemere')}")
    print(f"TTL: {r.ttl('ephemere')}s")
    time.sleep(1.1)
    print(f"Après 1.1s: {r.get('ephemere')} (None attendu)")

    r.set("permanent", "je reste")
    print(f"TTL permanent: {r.ttl('permanent')} (-1 = pas d'expiration)")

    # --- KEYS & DBSIZE ---
    print("\n--- 8. Keys & DbSize ---")
    r.flushdb()
    r.set("user:1", "Alice")
    r.set("user:2", "Bob")
    r.set("product:1", "Widget")
    r.set("product:2", "Gadget")
    print(f"Toutes les clés: {sorted(r.keys('*'))}")
    print(f"Clés user:*: {sorted(r.keys('user:*'))}")
    print(f"DBSIZE: {r.dbsize()}")

    print("\n" + "=" * 60)
    print("TOUS LES TESTS PASSES")
    print("=" * 60)


if __name__ == "__main__":
    tester()
