# Jour 41 — JWT : JSON Web Tokens
📅 6 août 2026 · Module : Auth

---

## Pourquoi JWT ?

Les sessions stockent l'état côté serveur (en DB ou Redis). JWT est **stateless** : toutes les informations sont dans le token lui-même.

```
Session :
  Client → envoie session_id=abc123
  Serveur → cherche "abc123" en DB → retrouve le user

JWT :
  Client → envoie le token (qui contient déjà user_id=42)
  Serveur → vérifie la signature → extrait user_id=42 (pas de DB !)
```

---

## Structure d'un JWT

Un JWT est `header.payload.signature`, encodé en base64url :

```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI0MiIsImV4cCI6MTc1NH0.xkHsaK2abc
      │                        │                              │
   header                  payload                       signature
```

**Header :**
```json
{"alg": "HS256", "typ": "JWT"}
```

**Payload (claims) :**
```json
{
  "sub": "42",        // subject = user_id
  "iat": 1753920000,  // issued at (timestamp)
  "exp": 1753920900,  // expiration (15 min après)
  "role": "admin"     // claim custom
}
```

**Signature :**
```
HMAC-SHA256(
  base64url(header) + "." + base64url(payload),
  SECRET_KEY
)
```

Le serveur peut **vérifier** la signature sans aller en DB. Si quelqu'un modifie le payload, la signature ne correspond plus.

---

## JWT à la main en Python

```python
import hmac, hashlib, base64, json, time

SECRET = b"mon-secret-tres-long-et-aleatoire"

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def base64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)

def creer_token(user_id: int, expiration_minutes: int = 15) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "iat": int(time.time()),
        "exp": int(time.time()) + expiration_minutes * 60,
    }

    h = base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    message = f"{h}.{p}".encode()
    sig = hmac.new(SECRET, message, hashlib.sha256).digest()
    s = base64url_encode(sig)

    return f"{h}.{p}.{s}"

def verifier_token(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Token malformé")

    h, p, s = parts
    message = f"{h}.{p}".encode()
    sig_attendue = hmac.new(SECRET, message, hashlib.sha256).digest()
    sig_recue = base64url_decode(s)

    if not hmac.compare_digest(sig_attendue, sig_recue):
        raise ValueError("Signature invalide")

    payload = json.loads(base64url_decode(p))

    if payload.get("exp", 0) < time.time():
        raise ValueError("Token expiré")

    return payload
```

---

## Avec PyJWT (en production)

```bash
pip install PyJWT
```

```python
import jwt
from datetime import datetime, timedelta, timezone

SECRET = "mon-secret-tres-long-et-aleatoire"

def creer_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=15),
        "iat": datetime.now(tz=timezone.utc),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def creer_refresh_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(tz=timezone.utc) + timedelta(days=7),
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def verifier_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expiré")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Token invalide : {e}")
```

---

## Access token + Refresh token

```
Client                                    Serveur
  │                                          │
  │── POST /login {user, password} ─────────→│
  │←── {access_token (15min), refresh_token (7j)} ──│
  │                                          │
  │── GET /api/me  Authorization: Bearer <access> ──→│
  │←── {user data} ─────────────────────────│
  │                                          │
  │  [access_token expiré]                   │
  │── POST /refresh {refresh_token} ────────→│
  │←── {nouveau access_token} ──────────────│
```

---

## Vulnérabilités JWT à connaître

**1. Algorithme `none` :** Un JWT avec `alg: none` n'a pas de signature. Toujours spécifier l'algorithme attendu.

```python
# Dangereux
jwt.decode(token, key, algorithms=["HS256", "none"])

# Correct
jwt.decode(token, key, algorithms=["HS256"])  # HS256 uniquement
```

**2. Pas de révocation :** Un JWT valide reste valide jusqu'à expiration, même si l'utilisateur change son mot de passe. Solution : garder une blacklist en Redis.

**3. Secret faible :** Avec un secret court ou prévisible, un attaquant peut brute-forcer la signature. Utilise au moins 32 bytes aléatoires.

```python
import secrets
SECRET = secrets.token_hex(32)  # 64 chars hexadécimaux
```
