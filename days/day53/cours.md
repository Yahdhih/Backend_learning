# Jour 53 — Redis : Structures de données et Use Cases (18 août 2026)

## Introduction

Redis (Remote Dictionary Server) est un magasin de données en mémoire, open source, utilisé comme base de données, cache, courtier de messages et file d'attente. Contrairement aux bases de données relationnelles qui stockent les données sur disque, Redis garde tout en RAM, ce qui lui confère des performances exceptionnelles : des latences de l'ordre de la microseconde et un débit de millions d'opérations par seconde.

**Pourquoi Redis ?**
- Vitesse : lecture/écriture en O(1) pour la plupart des opérations
- Polyvalence : 8+ structures de données natives
- Persistance optionnelle : on peut sauvegarder sur disque
- Pub/Sub intégré : communication en temps réel
- Transactions atomiques : MULTI/EXEC
- Clustering et réplication natifs

```bash
# Installation (Ubuntu/Debian)
sudo apt-get install redis-server

# Démarrer le serveur
redis-server

# Client en ligne de commande
redis-cli

# Tester la connexion
redis-cli ping
# PONG
```

---

## 1. Strings — La structure de base

Les strings Redis sont des chaînes binaires sécurisées. Elles peuvent contenir n'importe quelle donnée : texte, JSON, entiers, même des images (jusqu'à 512 MB).

### Commandes essentielles

```redis
# Stocker une valeur
SET nom "Alice"

# Récupérer une valeur
GET nom
# "Alice"

# Stocker avec expiration (TTL en secondes)
SET session_token "abc123" EX 3600

# Vérifier le TTL restant
TTL session_token
# 3598

# Incrémenter un compteur atomiquement
SET visites 0
INCR visites
# (integer) 1
INCR visites
# (integer) 2
INCRBY visites 5
# (integer) 7

# Stocker uniquement si la clé n'existe pas
SET verrou "locked" NX EX 30
# OK (si la clé n'existait pas)
# (nil) (si la clé existait déjà)

# Récupérer et supprimer
GETDEL nom
# "Alice"
```

### En Python avec redis-py

```python
import redis

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Opérations de base
r.set('nom', 'Alice')
print(r.get('nom'))  # Alice

# Avec TTL
r.set('session', 'token_abc123', ex=3600)
print(r.ttl('session'))  # ~3600

# Compteurs atomiques
r.set('visites', 0)
r.incr('visites')
r.incr('visites')
r.incrby('visites', 5)
print(r.get('visites'))  # 7

# Stocker du JSON
import json
utilisateur = {'id': 1, 'nom': 'Alice', 'email': 'alice@example.com'}
r.set('user:1', json.dumps(utilisateur))
data = json.loads(r.get('user:1'))
print(data['nom'])  # Alice

# Opérations multiples
r.mset({'cle1': 'val1', 'cle2': 'val2', 'cle3': 'val3'})
valeurs = r.mget('cle1', 'cle2', 'cle3')
print(valeurs)  # ['val1', 'val2', 'val3']
```

### Use cases des Strings
- **Sessions utilisateur** : `SET session:{token} {user_id} EX 3600`
- **Compteurs** : visites de page, limites d'API (rate limiting)
- **Verrous distribués** : `SET lock:{resource} 1 NX EX 30`
- **Cache de données simples** : mise en cache de réponses API
- **Tokens temporaires** : réinitialisation de mot de passe, confirmation email

---

## 2. Lists — Files et Piles

Les listes Redis sont des listes doublement chaînées. Elles permettent d'ajouter/supprimer des éléments en tête ou en queue en O(1).

### Commandes essentielles

```redis
# Ajouter à gauche (head)
LPUSH taches "tache3"
LPUSH taches "tache2"
LPUSH taches "tache1"

# Ajouter à droite (tail)
RPUSH taches "tache4"

# Voir le contenu (index 0 à -1 = tout)
LRANGE taches 0 -1
# 1) "tache1"
# 2) "tache2"
# 3) "tache3"
# 4) "tache4"

# Longueur
LLEN taches
# (integer) 4

# Supprimer et retourner depuis la gauche (FIFO Queue head)
LPOP taches
# "tache1"

# Supprimer et retourner depuis la droite (Stack pop)
RPOP taches
# "tache4"

# Opération bloquante : attendre qu'un élément arrive
BLPOP queue 30
# Bloque jusqu'à 30 secondes
```

### En Python

```python
import redis

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Simuler une file de traitement (Queue FIFO)
print("=== File de Traitement (Queue) ===")

# Producteur : ajouter des tâches
r.rpush('email_queue', 'email:user_1@example.com')
r.rpush('email_queue', 'email:user_2@example.com')
r.rpush('email_queue', 'email:user_3@example.com')

# Consommateur : traiter dans l'ordre
while r.llen('email_queue') > 0:
    tache = r.lpop('email_queue')
    print(f"Traitement: {tache}")

# Simuler une pile (Stack LIFO)
print("\n=== Pile d'Annulation (Stack) ===")

r.rpush('historique', 'action:créer_fichier')
r.rpush('historique', 'action:modifier_texte')
r.rpush('historique', 'action:supprimer_ligne')

# Annuler dans l'ordre inverse
while r.llen('historique') > 0:
    action = r.rpop('historique')
    print(f"Annulation: {action}")

# File de traitement temps réel avec BLPOP
import threading
import time

def worker(worker_id):
    r_worker = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    print(f"Worker {worker_id} en attente...")
    result = r_worker.blpop('jobs', timeout=10)
    if result:
        queue_name, job = result
        print(f"Worker {worker_id} traite: {job}")

# Lancer des workers en parallèle
threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
for t in threads:
    t.start()

time.sleep(0.1)
r.rpush('jobs', 'job_A')
r.rpush('jobs', 'job_B')
r.rpush('jobs', 'job_C')

for t in threads:
    t.join()
```

### Use cases des Lists
- **File de tâches asynchrones** : worker queues (alternative légère à Celery)
- **Feed d'activité** : garder les N dernières activités d'un utilisateur
- **Chat en temps réel** : historique des messages
- **Log buffer** : accumuler des logs avant de les écrire en batch

---

## 3. Hashes — Stockage d'Objets

Les Hashes sont des maps de champ-valeur, parfaits pour représenter des objets. Au lieu de sérialiser en JSON, on peut accéder à des champs individuels.

### Commandes essentielles

```redis
# Créer un hash (objet utilisateur)
HSET user:1 nom "Alice" email "alice@example.com" age 30 points 1500

# Récupérer un champ
HGET user:1 nom
# "Alice"

# Récupérer tous les champs
HGETALL user:1
# 1) "nom"
# 2) "Alice"
# 3) "email"
# 4) "alice@example.com"
# 5) "age"
# 6) "30"
# 7) "points"
# 8) "1500"

# Vérifier si un champ existe
HEXISTS user:1 email
# (integer) 1

# Incrémenter un champ numérique
HINCRBY user:1 points 100
# (integer) 1600

# Supprimer un champ
HDEL user:1 age

# Récupérer plusieurs champs spécifiques
HMGET user:1 nom email
# 1) "Alice"
# 2) "alice@example.com"
```

### En Python

```python
import redis

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Créer des profils utilisateurs
print("=== Gestion de Profils Utilisateurs ===")

# Stocker un utilisateur
r.hset('user:1', mapping={
    'nom': 'Alice',
    'email': 'alice@example.com',
    'age': '30',
    'points': '1500',
    'statut': 'actif'
})

r.hset('user:2', mapping={
    'nom': 'Bob',
    'email': 'bob@example.com',
    'age': '25',
    'points': '800',
    'statut': 'actif'
})

# Récupérer tout le profil
alice = r.hgetall('user:1')
print(f"Profil Alice: {alice}")

# Modifier un seul champ (efficace — pas besoin de tout re-sérialiser)
r.hset('user:1', 'statut', 'premium')
print(f"Statut Alice: {r.hget('user:1', 'statut')}")

# Incrémenter les points
r.hincrby('user:1', 'points', 200)
print(f"Points Alice: {r.hget('user:1', 'points')}")

# Panier d'achat
print("\n=== Panier d'Achat ===")

r.hset('cart:user_1', mapping={
    'produit:101': '2',  # 2 unités
    'produit:205': '1',
    'produit:307': '3'
})

panier = r.hgetall('cart:user_1')
for produit, quantite in panier.items():
    print(f"  {produit}: {quantite} unité(s)")

# Mettre à jour la quantité d'un article
r.hincrby('cart:user_1', 'produit:101', 1)  # +1 unité
print(f"Quantité produit:101: {r.hget('cart:user_1', 'produit:101')}")

# Session de jeu
print("\n=== Session de Jeu ===")
r.hset('game_session:xyz789', mapping={
    'user_id': '42',
    'niveau': '5',
    'score': '3450',
    'vie': '3',
    'checkpoint': 'zone_3_boss'
})
r.expire('game_session:xyz789', 1800)  # Expire dans 30 minutes
```

### Use cases des Hashes
- **Profils utilisateurs** : modifier un champ sans re-sérialiser tout l'objet
- **Sessions** : données de session structurées
- **Produits e-commerce** : attributs d'un produit
- **Compteurs multidimensionnels** : statistiques par catégorie

---

## 4. Sets — Ensembles sans Doublons

Les Sets sont des collections non ordonnées d'éléments uniques. Ils supportent les opérations ensemblistes (union, intersection, différence) en O(N).

### Commandes essentielles

```redis
# Ajouter des membres
SADD amis:alice "bob" "charlie" "dave"
SADD amis:bob "alice" "charlie" "eve"

# Lister les membres
SMEMBERS amis:alice
# 1) "bob"
# 2) "charlie"
# 3) "dave"

# Vérifier l'appartenance
SISMEMBER amis:alice "charlie"
# (integer) 1

# Taille de l'ensemble
SCARD amis:alice
# (integer) 3

# Amis en commun (intersection)
SINTER amis:alice amis:bob
# 1) "charlie"

# Union des amis
SUNION amis:alice amis:bob
# 1) "alice"
# 2) "bob"
# 3) "charlie"
# 4) "dave"
# 5) "eve"

# Amis d'Alice mais pas de Bob
SDIFF amis:alice amis:bob
# 1) "dave"

# Supprimer un membre
SREM amis:alice "dave"

# Membre aléatoire (pour tirage au sort)
SRANDMEMBER amis:alice
```

### En Python

```python
import redis

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Système de tags/étiquettes
print("=== Système de Tags ===")

r.sadd('article:1:tags', 'python', 'django', 'web', 'backend')
r.sadd('article:2:tags', 'python', 'data-science', 'pandas')
r.sadd('article:3:tags', 'javascript', 'react', 'web', 'frontend')

# Articles avec le tag "python"
print(f"Tags article 1: {r.smembers('article:1:tags')}")

# Articles qui partagent des tags avec l'article 1
common = r.sinter('article:1:tags', 'article:2:tags')
print(f"Tags communs entre article 1 et 2: {common}")

# Tous les tags existants
all_tags = r.sunion('article:1:tags', 'article:2:tags', 'article:3:tags')
print(f"Tous les tags: {all_tags}")

# Suivi des visites uniques (Unique Visitors)
print("\n=== Visites Uniques par Jour ===")

import datetime

today = datetime.date.today().strftime('%Y-%m-%d')
key = f'visitors:{today}'

# Simuler des visites (user_id)
visiteurs = ['user_1', 'user_2', 'user_1', 'user_3', 'user_2', 'user_4']
for visiteur in visiteurs:
    r.sadd(key, visiteur)

print(f"Visiteurs uniques aujourd'hui: {r.scard(key)}")
print(f"Liste: {r.smembers(key)}")

# Gérer les permissions
print("\n=== Permissions par Rôle ===")

r.sadd('role:admin', 'read', 'write', 'delete', 'manage_users')
r.sadd('role:editor', 'read', 'write')
r.sadd('role:viewer', 'read')

# Permissions d'un utilisateur (union de ses rôles)
def get_permissions(roles):
    if not roles:
        return set()
    return r.sunion(*[f'role:{role}' for role in roles])

alice_perms = get_permissions(['editor', 'viewer'])
print(f"Permissions Alice (éditeur): {alice_perms}")

admin_perms = get_permissions(['admin'])
print(f"Permissions Admin: {admin_perms}")

# Vérifie si peut supprimer
can_delete = r.sismember('role:editor', 'delete')
print(f"L'éditeur peut supprimer: {bool(can_delete)}")
```

### Use cases des Sets
- **Amis/followers** : qui suit qui, amis en commun
- **Visiteurs uniques** : comptage sans doublons
- **Tags et catégories** : articles par tag
- **Permissions** : ensembles de droits par rôle
- **Blacklist/whitelist** : IPs bloquées, tokens révoqués

---

## 5. Sorted Sets — Classements et Scores

Les Sorted Sets (ZSets) sont comme les Sets, mais chaque membre a un score numérique. Les membres sont toujours triés par score. C'est la structure parfaite pour les leaderboards.

### Commandes essentielles

```redis
# Ajouter avec un score
ZADD leaderboard 1500 "Alice"
ZADD leaderboard 2300 "Bob"
ZADD leaderboard 1800 "Charlie"
ZADD leaderboard 900 "Dave"

# Top 3 (ordre croissant)
ZRANGE leaderboard 0 2 WITHSCORES
# 1) "Dave"
# 2) "900"
# 3) "Alice"
# 4) "1500"
# 5) "Charlie"
# 6) "1800"

# Top 3 (ordre décroissant = classement)
ZREVRANGE leaderboard 0 2 WITHSCORES
# 1) "Bob"
# 2) "2300"
# 3) "Charlie"
# 4) "1800"
# 5) "Alice"
# 6) "1500"

# Score d'un membre spécifique
ZSCORE leaderboard "Alice"
# "1500"

# Rang d'un membre (0-indexed, croissant)
ZRANK leaderboard "Alice"
# (integer) 1

# Rang décroissant (position dans le classement)
ZREVRANK leaderboard "Alice"
# (integer) 2

# Incrémenter le score
ZINCRBY leaderboard 300 "Dave"
# "1200"

# Membres dans une plage de scores
ZRANGEBYSCORE leaderboard 1000 2000 WITHSCORES
```

### En Python

```python
import redis
import time

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Leaderboard de jeu
print("=== Leaderboard de Jeu ===")

# Initialiser les scores
joueurs = {
    'Alice': 1500,
    'Bob': 2300,
    'Charlie': 1800,
    'Dave': 900,
    'Eve': 2100
}

r.zadd('game:leaderboard', joueurs)

# Afficher le top 5
print("Top 5 (du meilleur au moins bon):")
top5 = r.zrevrange('game:leaderboard', 0, 4, withscores=True)
for rang, (joueur, score) in enumerate(top5, 1):
    print(f"  #{rang}: {joueur} — {int(score)} pts")

# Rang d'un joueur spécifique
rang_alice = r.zrevrank('game:leaderboard', 'Alice')
score_alice = r.zscore('game:leaderboard', 'Alice')
print(f"\nAlice: rang #{rang_alice + 1}, score {int(score_alice)}")

# Incrémenter le score
r.zincrby('game:leaderboard', 500, 'Alice')
print(f"Après bonus: Alice {int(r.zscore('game:leaderboard', 'Alice'))} pts")

# Rate Limiting avec Sorted Sets (sliding window)
print("\n=== Rate Limiting (Fenêtre Glissante) ===")

def is_rate_limited(user_id: str, max_requests: int = 5, window_seconds: int = 60) -> bool:
    """Vérifie si l'utilisateur a dépassé sa limite de requêtes."""
    key = f'rate_limit:{user_id}'
    now = time.time()
    window_start = now - window_seconds

    pipe = r.pipeline()
    # Supprimer les requêtes hors de la fenêtre
    pipe.zremrangebyscore(key, 0, window_start)
    # Ajouter la requête actuelle
    pipe.zadd(key, {str(now): now})
    # Compter les requêtes dans la fenêtre
    pipe.zcard(key)
    # Expirer la clé pour le nettoyage automatique
    pipe.expire(key, window_seconds)
    results = pipe.execute()

    request_count = results[2]
    return request_count > max_requests

# Simuler des requêtes
user = 'user_42'
for i in range(7):
    limited = is_rate_limited(user, max_requests=5)
    status = "BLOQUÉ" if limited else "OK"
    print(f"  Requête {i+1}: {status}")

# Trending topics (score = timestamp de mise à jour)
print("\n=== Trending Topics ===")

import time

def boost_topic(topic: str, boost: float = 1.0):
    """Augmente le score d'un topic."""
    r.zincrby('trending', boost, topic)

def decay_topics():
    """Diminue progressivement tous les scores (decay)."""
    topics = r.zrange('trending', 0, -1, withscores=True)
    for topic, score in topics:
        new_score = score * 0.9  # 10% de decay
        if new_score < 0.1:
            r.zrem('trending', topic)
        else:
            r.zadd('trending', {topic: new_score})

# Simuler de l'activité
boost_topic('python', 10)
boost_topic('django', 7)
boost_topic('redis', 15)
boost_topic('docker', 4)
boost_topic('kubernetes', 3)

print("Trending topics:")
trending = r.zrevrange('trending', 0, 4, withscores=True)
for topic, score in trending:
    print(f"  {topic}: {score:.1f}")
```

### Use cases des Sorted Sets
- **Leaderboards** : classements de jeux, scores
- **Rate limiting** : fenêtre glissante de requêtes
- **Trending topics** : popularité avec decay temporel
- **File de priorité** : tâches triées par priorité
- **Scheduled tasks** : tâches avec timestamp d'exécution

---

## 6. Pub/Sub — Messagerie en Temps Réel

Redis Pub/Sub permet la communication asynchrone entre publishers (producteurs) et subscribers (consommateurs).

```python
import redis
import threading
import time

# --- Subscriber (dans un thread séparé) ---
def subscriber():
    r_sub = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    pubsub = r_sub.pubsub()

    # S'abonner à un canal
    pubsub.subscribe('notifications')

    print("Subscriber en écoute sur 'notifications'...")
    for message in pubsub.listen():
        if message['type'] == 'message':
            print(f"[Reçu] Canal: {message['channel']}, Data: {message['data']}")

# --- Publisher ---
def publisher():
    r_pub = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    time.sleep(0.5)  # Laisser le subscriber démarrer

    messages = [
        "Nouvelle commande #1234",
        "Paiement confirmé #1234",
        "Commande expédiée #1234"
    ]

    for msg in messages:
        r_pub.publish('notifications', msg)
        time.sleep(0.1)

# Pattern matching : s'abonner à plusieurs canaux
def subscriber_pattern():
    r_sub = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    pubsub = r_sub.pubsub()

    # S'abonner à tous les canaux commençant par "order:"
    pubsub.psubscribe('order:*')

    for message in pubsub.listen():
        if message['type'] == 'pmessage':
            print(f"[Pattern] Canal: {message['channel']}, Data: {message['data']}")

# Lancer en parallèle
sub_thread = threading.Thread(target=subscriber, daemon=True)
pub_thread = threading.Thread(target=publisher)

sub_thread.start()
pub_thread.start()
pub_thread.join()
time.sleep(0.5)
```

### Use cases du Pub/Sub
- **Notifications temps réel** : alertes utilisateur
- **Cache invalidation distribuée** : signaler aux workers de vider leur cache local
- **Chat applications** : salons de discussion
- **Event streaming léger** : événements applicatifs simples

---

## 7. Persistance Redis : RDB vs AOF

Redis propose deux mécanismes de persistance optionnels.

### RDB (Redis Database — Snapshot)

```bash
# redis.conf
save 900 1      # Snapshot si au moins 1 changement en 15 min
save 300 10     # Snapshot si au moins 10 changements en 5 min
save 60 10000   # Snapshot si au moins 10000 changements en 1 min

dbfilename dump.rdb
dir /var/lib/redis
```

- **Avantages** : compact, rapide au redémarrage, parfait pour les backups
- **Inconvénients** : risque de perte des données depuis le dernier snapshot

### AOF (Append Only File)

```bash
# redis.conf
appendonly yes
appendfilename "appendonly.aof"

# Synchronisation disque
appendfsync always    # Sécurisé mais lent
appendfsync everysec  # Bon équilibre (recommandé)
appendfsync no        # Rapide mais risqué
```

- **Avantages** : durabilité maximale, perte max de 1 seconde
- **Inconvénients** : fichier plus grand, redémarrage plus lent

### Mode hybride (recommandé en production)

```bash
aof-use-rdb-preamble yes  # AOF commence par un snapshot RDB
```

---

## 8. Redis comme Cache

```python
import redis
import json
import functools
import time

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Décorateur de cache générique
def redis_cache(ttl=300):
    """Décorateur qui met en cache le résultat d'une fonction."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Générer une clé unique
            cache_key = f"cache:{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

            # Vérifier le cache
            cached = r.get(cache_key)
            if cached:
                print(f"[CACHE HIT] {cache_key}")
                return json.loads(cached)

            # Calculer le résultat
            print(f"[CACHE MISS] {cache_key}")
            result = func(*args, **kwargs)

            # Stocker en cache
            r.set(cache_key, json.dumps(result), ex=ttl)
            return result
        return wrapper
    return decorator

@redis_cache(ttl=60)
def get_user_profile(user_id: int) -> dict:
    """Simule une requête base de données lente."""
    time.sleep(0.1)  # Simuler la latence DB
    return {'id': user_id, 'nom': 'Alice', 'email': 'alice@example.com'}

# Premier appel : CACHE MISS (requête DB)
user = get_user_profile(1)
print(f"Résultat: {user}")

# Deuxième appel : CACHE HIT (depuis Redis)
user = get_user_profile(1)
print(f"Résultat: {user}")
```

---

## 9. Redis comme Session Store

```python
import redis
import json
import uuid
import time

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class RedisSessionStore:
    """Gestionnaire de sessions avec Redis."""

    SESSION_TTL = 3600  # 1 heure

    def create_session(self, user_data: dict) -> str:
        """Crée une nouvelle session et retourne le token."""
        token = str(uuid.uuid4())
        session_key = f"session:{token}"

        session_data = {
            **user_data,
            'created_at': time.time(),
            'last_activity': time.time()
        }

        r.hset(session_key, mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                                      for k, v in session_data.items()})
        r.expire(session_key, self.SESSION_TTL)

        return token

    def get_session(self, token: str) -> dict | None:
        """Récupère les données de session."""
        session_key = f"session:{token}"
        data = r.hgetall(session_key)

        if not data:
            return None

        # Renouveler le TTL à chaque accès
        r.expire(session_key, self.SESSION_TTL)
        r.hset(session_key, 'last_activity', str(time.time()))

        return data

    def destroy_session(self, token: str):
        """Détruit une session (logout)."""
        r.delete(f"session:{token}")

# Utilisation
store = RedisSessionStore()

# Connexion
token = store.create_session({'user_id': '42', 'nom': 'Alice', 'role': 'admin'})
print(f"Token de session: {token}")

# Accès à une ressource protégée
session = store.get_session(token)
print(f"Session: {session}")

# Déconnexion
store.destroy_session(token)
print(f"Session après déconnexion: {store.get_session(token)}")
```

---

## 10. Redis comme Message Broker (Queues)

```python
import redis
import json
import time
import threading

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

class SimpleQueue:
    """File de tâches simple avec Redis Lists."""

    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self.processing_key = f"{queue_name}:processing"

    def enqueue(self, task: dict) -> str:
        """Ajoute une tâche à la file."""
        task_id = str(time.time_ns())
        task['id'] = task_id
        task['enqueued_at'] = time.time()

        r.rpush(self.queue_name, json.dumps(task))
        print(f"[Queue] Tâche ajoutée: {task['type']} (id={task_id})")
        return task_id

    def dequeue(self, timeout: int = 5) -> dict | None:
        """Retire et retourne une tâche (bloquant)."""
        result = r.blpop(self.queue_name, timeout=timeout)
        if result:
            _, task_json = result
            return json.loads(task_json)
        return None

    def size(self) -> int:
        return r.llen(self.queue_name)

# Worker
def email_worker(worker_id: int, queue: SimpleQueue):
    print(f"Worker {worker_id} démarré")
    while True:
        task = queue.dequeue(timeout=2)
        if task is None:
            break
        print(f"[Worker {worker_id}] Envoi email à {task['to']}: {task['subject']}")
        time.sleep(0.05)  # Simuler le traitement

# Démonstration
email_queue = SimpleQueue('emails')

# Ajouter des tâches
tasks = [
    {'type': 'email', 'to': 'alice@example.com', 'subject': 'Bienvenue !'},
    {'type': 'email', 'to': 'bob@example.com', 'subject': 'Votre commande'},
    {'type': 'email', 'to': 'charlie@example.com', 'subject': 'Alerte sécurité'},
]

for task in tasks:
    email_queue.enqueue(task)

print(f"Tâches en attente: {email_queue.size()}")

# Lancer 2 workers en parallèle
workers = [threading.Thread(target=email_worker, args=(i, email_queue)) for i in range(2)]
for w in workers:
    w.start()
for w in workers:
    w.join()

print("Toutes les tâches traitées")
```

---

## 11. Redis comme Rate Limiter

```python
import redis
import time

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def rate_limit_fixed_window(user_id: str, max_requests: int = 100, window_seconds: int = 60) -> dict:
    """
    Rate limiting par fenêtre fixe.
    Simple mais avec effet de bord en fin/début de fenêtre.
    """
    window_start = int(time.time() / window_seconds)
    key = f"rate:{user_id}:{window_start}"

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = pipe.execute()

    count = results[0]
    allowed = count <= max_requests

    return {
        'allowed': allowed,
        'count': count,
        'remaining': max(0, max_requests - count),
        'reset_in': window_seconds - (int(time.time()) % window_seconds)
    }

def rate_limit_sliding_window(user_id: str, max_requests: int = 10, window_seconds: int = 60) -> dict:
    """
    Rate limiting par fenêtre glissante.
    Plus précis, utilise un Sorted Set.
    """
    key = f"rate_sliding:{user_id}"
    now = time.time()
    window_start = now - window_seconds

    pipe = r.pipeline()
    # Nettoyer les anciennes entrées
    pipe.zremrangebyscore(key, 0, window_start)
    # Ajouter la requête actuelle
    pipe.zadd(key, {str(now): now})
    # Compter
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 1)
    results = pipe.execute()

    count = results[2]
    allowed = count <= max_requests

    return {
        'allowed': allowed,
        'count': count,
        'remaining': max(0, max_requests - count),
    }

# Test
print("=== Rate Limiting ===")
for i in range(13):
    result = rate_limit_sliding_window('api_user_1', max_requests=10, window_seconds=60)
    status = "OK" if result['allowed'] else "RATE LIMITED"
    print(f"  Requête {i+1:2d}: {status} ({result['count']}/10, reste: {result['remaining']})")
```

---

## 12. Configuration Redis avec Django (django-redis)

```python
# settings.py

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
            "PASSWORD": "votre_mot_de_passe",  # si auth activée
        },
        "KEY_PREFIX": "myapp",
        "TIMEOUT": 300,  # TTL par défaut en secondes
    }
}

# Pour les sessions Django
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Installation
# pip install django-redis redis
```

---

## Résumé — Choisir la bonne structure

| Structure    | Use Case Principal                        | Complexité    |
|-------------|-------------------------------------------|---------------|
| String      | Cache, compteur, verrou, session          | O(1)          |
| List        | Queue, stack, feed d'activité             | O(1) head/tail|
| Hash        | Objet structuré, profil, panier           | O(1) par champ|
| Set         | Tags, visiteurs uniques, permissions      | O(1) SADD     |
| Sorted Set  | Leaderboard, rate limit, scheduling       | O(log N)      |
| Pub/Sub     | Notifications, invalidation cache         | O(N) subscribers|

## Commandes de diagnostic utiles

```bash
# Voir toutes les clés (à éviter en prod !)
redis-cli KEYS "*"

# Scanner sans bloquer (préférable)
redis-cli SCAN 0 MATCH "user:*" COUNT 100

# Infos sur une clé
redis-cli TYPE session:abc123
redis-cli TTL session:abc123
redis-cli MEMORY USAGE session:abc123

# Statistiques du serveur
redis-cli INFO stats
redis-cli INFO memory

# Monitor toutes les commandes en temps réel
redis-cli MONITOR

# Slow log
redis-cli SLOWLOG GET 10
```

---

## Points clés à retenir

1. **Redis est in-memory** : ultra-rapide, mais la RAM est limitée — utiliser des TTL
2. **Choisir la bonne structure** : ne pas tout mettre en String/JSON
3. **Les pipelines** réduisent le nombre de round-trips réseau
4. **Les transactions (MULTI/EXEC)** garantissent l'atomicité
5. **La persistance est optionnelle** mais recommandée en production
6. **Redis n'est pas une base de données principale** : l'utiliser en complément de PostgreSQL/MySQL
7. **Le monitoring** est crucial : SLOWLOG, INFO, MONITOR
