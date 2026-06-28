# Jour 42 — OAuth2
📅 7 août 2026 · Module : Auth

---

## Le problème qu'OAuth2 résout

Sans OAuth2 : pour accéder à tes emails Google depuis une app tierce, tu donnes ton mot de passe Gmail à l'app. L'app a alors accès à tout ton compte pour toujours.

Avec OAuth2 : tu donnes à l'app tierce une permission **limitée** et **révocable**, sans partager ton mot de passe.

---

## Les acteurs

```
[Resource Owner]   Tu (l'utilisateur)
[Client]           L'application tierce (ex: une app qui lit tes emails)
[Authorization Server]  Google/GitHub/... — vérifie ton identité et délivre les tokens
[Resource Server]  L'API qui a tes données (Gmail API, GitHub API...)
```

---

## Le flow Authorization Code (le plus courant)

```
1. Tu cliques "Se connecter avec GitHub" dans l'app

2. L'app redirige vers GitHub :
   GET https://github.com/login/oauth/authorize
     ?client_id=abc123
     &redirect_uri=https://monapp.com/callback
     &scope=read:user,repo
     &state=xyz789    ← protection CSRF

3. Tu t'authentifies sur GitHub et approuves les permissions

4. GitHub redirige vers ton app :
   GET https://monapp.com/callback?code=CODE_AUTH&state=xyz789

5. Ton app échange le code contre des tokens (côté serveur) :
   POST https://github.com/login/oauth/access_token
     {client_id, client_secret, code}
   → {access_token, refresh_token, expires_in}

6. Ton app utilise le token pour appeler l'API :
   GET https://api.github.com/user
     Authorization: Bearer ACCESS_TOKEN
```

---

## Les 4 flows OAuth2

| Flow | Usage |
|------|-------|
| Authorization Code | Apps web/mobile avec backend |
| Authorization Code + PKCE | Apps mobiles/SPA sans backend secret |
| Client Credentials | Machine à machine (APIs entre serveurs) |
| Device Code | TV, IoT (pas de navigateur) |

**PKCE** (Proof Key for Code Exchange) : pour les apps où on ne peut pas garder un `client_secret` secret (apps mobiles, SPA).

---

## Access Token vs Refresh Token

```
Access Token  : courte durée (15min - 1h), utilisé pour appeler l'API
Refresh Token : longue durée (jours - semaines), utilisé pour renouveler l'access token

[App] → API avec access_token
  → 401 Unauthorized (token expiré)
[App] → Authorization Server avec refresh_token
  → nouveau access_token
[App] → API avec nouveau access_token
  → 200 OK
```

---

## Scopes : permissions granulaires

```
scope=read:user          → lire le profil
scope=repo               → accès complet aux repos
scope=repo:read          → lire les repos seulement
scope=user:email         → lire l'email uniquement
```

Le principe du **moindre privilège** : demander seulement les permissions dont tu as besoin.

---

## OpenID Connect (OIDC)

OIDC = OAuth2 + identité. En plus de l'access token, tu reçois un `id_token` (un JWT) qui contient les infos de l'utilisateur.

```json
// id_token décodé
{
  "sub": "12345",           // identifiant unique chez le provider
  "email": "alice@gmail.com",
  "name": "Alice Dupont",
  "picture": "https://...",
  "iss": "https://accounts.google.com",
  "aud": "ton-client-id",
  "exp": 1753920000
}
```

---

## Implémenter OAuth2 avec Django (social-auth-app-django)

```python
# Installation
pip install social-auth-app-django

# settings.py
INSTALLED_APPS += ["social_django"]
AUTHENTICATION_BACKENDS = [
    "social_core.backends.github.GithubOAuth2",
    "django.contrib.auth.backends.ModelBackend",
]
SOCIAL_AUTH_GITHUB_KEY = "ton-client-id"
SOCIAL_AUTH_GITHUB_SECRET = "ton-client-secret"
SOCIAL_AUTH_GITHUB_SCOPE = ["user:email"]

# urls.py
urlpatterns += [path("oauth/", include("social_django.urls", namespace="social"))]

# Template
<a href="{% url 'social:begin' 'github' %}">Se connecter avec GitHub</a>
```
