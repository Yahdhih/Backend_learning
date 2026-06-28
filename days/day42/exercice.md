# Exercice Jour 42 — Observer OAuth2 avec GitHub

## Prérequis
- Un compte GitHub
- Python + requests : `pip install requests`

---

## Étape 1 — Créer une OAuth App GitHub

1. Va sur GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
2. Remplis :
   - Application name : `backend-learning-test`
   - Homepage URL : `http://localhost:8000`
   - Authorization callback URL : `http://localhost:8888/callback`
3. Clique "Register application"
4. Note le `Client ID` et génère un `Client Secret`

---

## Étape 2 — Construire l'URL d'autorisation

```python
import urllib.parse

CLIENT_ID = "ton-client-id"  # remplace
REDIRECT_URI = "http://localhost:8888/callback"
SCOPE = "read:user user:email"
STATE = "random-string-anti-csrf-123"

params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "state": STATE,
}

auth_url = "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
print("Ouvre cette URL dans ton navigateur :")
print(auth_url)
```

Ouvre l'URL. GitHub te demande d'autoriser l'app. Après validation, il redirige vers :
`http://localhost:8888/callback?code=XXXXXX&state=random-string-anti-csrf-123`

Copie la valeur du paramètre `code`.

---

## Étape 3 — Échanger le code contre un token

```python
import requests

CLIENT_ID = "ton-client-id"
CLIENT_SECRET = "ton-client-secret"
CODE = "le-code-copié-à-l-étape-2"

response = requests.post(
    "https://github.com/login/oauth/access_token",
    headers={"Accept": "application/json"},
    json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": CODE,
    }
)
data = response.json()
print("Réponse GitHub :", data)
ACCESS_TOKEN = data.get("access_token")
print("Access Token :", ACCESS_TOKEN)
```

**Observation :** Que contient la réponse ? Y a-t-il un refresh_token ? (GitHub n'en donne pas pour les OAuth Apps classiques.)

---

## Étape 4 — Utiliser le token pour appeler l'API

```python
headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

# Profil de l'utilisateur
user = requests.get("https://api.github.com/user", headers=headers).json()
print("Utilisateur :", user.get("login"), user.get("name"))

# Email (scope user:email requis)
emails = requests.get("https://api.github.com/user/emails", headers=headers).json()
print("Emails :", emails)

# Repos
repos = requests.get("https://api.github.com/user/repos", headers=headers).json()
print("Nombre de repos :", len(repos))
```

---

## Étape 5 — Inspecter le token (optionnel)

```python
# GitHub permet de voir les infos d'un token
info = requests.get(
    "https://api.github.com/applications/CLIENT_ID/token",
    auth=(CLIENT_ID, CLIENT_SECRET),
    json={"access_token": ACCESS_TOKEN}
).json()
print("Infos token :", info)
```

---

## Questions dans `notes.md`

1. Pourquoi le `code` d'autorisation doit-il être échangé côté serveur (pas côté client) ?
2. À quoi sert le paramètre `state` dans l'URL d'autorisation ?
3. Quelle est la différence entre OAuth2 (autorisation) et OpenID Connect (authentification) ?
4. Dans quels cas utiliserais-tu "Client Credentials" plutôt que "Authorization Code" ?
5. Que se passe-t-il si l'utilisateur révoque l'accès sur GitHub ? Le token côté client est-il immédiatement invalidé ?
