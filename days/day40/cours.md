# Day 40 — Hachage de mots de passe

## Pourquoi ne jamais stocker les mots de passe en clair

Si votre base de données est compromise (injection SQL, dump de backup, accès non autorisé), l'attaquant obtient directement tous les mots de passe. Ces mots de passe sont souvent réutilisés sur d'autres sites : l'impact devient immédiat et massif.

**Règle absolue** : un mot de passe ne doit **jamais** être stockable en clair, ni récupérable en clair. Seul le propriétaire le connaît.

---

## Hash vs Chiffrement

| Critère | Hash (one-way) | Chiffrement (two-way) |
|---|---|---|
| Réversible ? | Non | Oui (avec la clé) |
| Usage mots de passe | Oui | Non |
| Risque | Si la BD fuite, l'attaquant attaque hors-ligne | Si la clé fuite, tout est déchiffré |
| Exemples | SHA-256, bcrypt, Argon2 | AES, RSA |

Pour les mots de passe, on veut une fonction **one-way** : on ne peut pas "décoder" le hash. Pour vérifier, on refait le hash et on compare.

---

## MD5 et SHA-1 sont cassés pour les mots de passe

### Pourquoi MD5/SHA-1 sont insuffisants

1. **Vitesse** : un GPU moderne calcule **10 milliards** de MD5/seconde. Un attaquant peut tester tout le dictionnaire en millisecondes.

2. **Rainbow tables** : des tables précalculées associent hash → mot de passe pour des millions de mots courants. Trouver `5f4dcc3b5aa765d61d8327deb882cf99` → `password` est instantané.

3. **Pas de sel** : le même mot de passe donne toujours le même hash. Si deux utilisateurs ont le même mot de passe, le hash est identique → l'attaquant le sait.

```
MD5("password") = 5f4dcc3b5aa765d61d8327deb882cf99
# Ce hash apparaît des millions de fois dans les rainbow tables.
```

---

## La solution : fonctions de hachage lentes + sel

### Le sel (salt)

Un sel est une valeur **aléatoire unique par utilisateur**, ajoutée au mot de passe avant le hash.

```
hash = H(password + salt)
```

- Deux utilisateurs avec le même mot de passe auront des hashes différents.
- Les rainbow tables deviennent inutiles (elles devraient être recalculées pour chaque sel).
- Le sel est **stocké en clair** à côté du hash — ce n'est pas un secret, c'est une protection structurelle.

### Le facteur de coût (cost factor)

On veut que le calcul soit **délibérément lent**. Si chaque vérification prend 100ms, un attaquant qui teste 10 000 mots de passe hors ligne prendra 1000 secondes. Sans facteur de coût, la même attaque prendrait 1ms.

---

## Les algorithmes modernes

### bcrypt (1999, toujours valide)

- Inventé par Niels Provos et David Mazières
- Sel intégré (128 bits, aléatoire)
- Facteur de coût : `cost` (de 4 à 31) — chaque incrément **double** le temps
- Recommandation : `cost=12` (environ 250ms sur un serveur moderne)

```
$2b$12$LXHm6...........salt..........hash.............
 |  |  |                |
 |  |  coût             sel (22 chars base64)
 |  version
 algo
```

Limite : max 72 caractères de mot de passe.

### Argon2 (2015, gagnant de la Password Hashing Competition)

C'est l'algorithme **recommandé** aujourd'hui. Il a trois variantes :
- **Argon2i** : résistant aux side-channel attacks (recommandé pour les mots de passe)
- **Argon2d** : résistant aux GPU (plus rapide, pour les cryptomonnaies)
- **Argon2id** : hybride, meilleur compromis

Paramètres :
- `time_cost` : nombre d'itérations
- `memory_cost` : mémoire RAM utilisée (en KB) — rend les attaques GPU coûteuses
- `parallelism` : threads parallèles

```python
# pip install argon2-cffi
from argon2 import PasswordHasher
ph = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
hash = ph.hash("mon_mot_de_passe")
ph.verify(hash, "mon_mot_de_passe")  # True
```

### PBKDF2 (Password-Based Key Derivation Function 2)

- Standard NIST (SP 800-132)
- Applique un HMAC des milliers de fois
- **Django l'utilise par défaut** depuis la version 1.4
- Recommandation NIST 2023 : **600 000 itérations avec SHA-256**

```
PBKDF2(password, salt, iterations, hash_func, key_length)
```

---

## Comment Django gère les mots de passe

### Le format de stockage Django

Django stocke le hash dans un format structuré :

```
pbkdf2_sha256$600000$sel_base64$hash_base64
     |           |       |          |
  algorithme  itérations  sel      hash
```

### Les fonctions clés

```python
from django.contrib.auth.hashers import (
    make_password,
    check_password,
    PBKDF2PasswordHasher,
)

# Créer un hash
hash = make_password("mon_secret")
# → "pbkdf2_sha256$600000$abc123...$/xyz789..."

# Vérifier
is_valid = check_password("mon_secret", hash)  # True
is_valid = check_password("mauvais", hash)      # False
```

### La hiérarchie des hashers Django

```python
# settings.py
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',   # préféré
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',   # défaut si Argon2 absent
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]
# Le premier est utilisé pour créer de nouveaux hashes.
# Les suivants permettent de vérifier d'anciens hashes (migration).
```

### Mise à niveau automatique

Django **rehash automatiquement** le mot de passe lors du prochain login si l'algorithme a changé. C'est transparent pour l'utilisateur.

---

## Attaques principales

### Brute force

L'attaquant teste des mots de passe systematiquement.

**Défenses** :
- Algorithme lent (bcrypt, Argon2, PBKDF2 avec beaucoup d'itérations)
- Rate limiting sur l'endpoint de login
- Lockout après N tentatives échouées

### Attaques par dictionnaire

L'attaquant teste des listes de mots de passe courants (`rockyou.txt` contient 14 millions de mots de passe réels).

**Défense** : vérification de force du mot de passe à la création + sel.

### Rainbow tables

Tables précalculées hash → mot de passe.

**Défense** : sel aléatoire — inutilisable avec un sel unique par utilisateur.

### Timing attacks

Si votre comparaison s'arrête dès le premier caractère différent, le temps de réponse révèle des informations sur le hash.

```python
# MAUVAIS — susceptible aux timing attacks
if hash_stocke == hash_calcule:
    ...

# BON — temps constant
import hmac
if hmac.compare_digest(hash_stocke, hash_calcule):
    ...
```

### Credential stuffing

L'attaquant utilise des paires login/mot de passe volées ailleurs (les gens réutilisent leurs mots de passe).

**Défenses** : MFA, détection d'IP suspectes, vérification contre HaveIBeenPwned.

---

## Recommandations de production

| Contexte | Algorithme | Paramètres |
|---|---|---|
| Nouveau projet | Argon2id | `time=2, mem=65536, p=2` |
| Django standard | PBKDF2-SHA256 | 600 000 itérations |
| Systèmes legacy | bcrypt | `cost=12` |
| **Jamais** | MD5, SHA-1, SHA-256 simple | — |

**Toujours** :
- Utiliser un sel aléatoire unique par mot de passe
- Utiliser `hmac.compare_digest()` pour la comparaison
- Mettre à jour le nombre d'itérations au fil du temps (le matériel devient plus rapide)
- Logger les tentatives de connexion échouées
