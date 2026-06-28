# Jour 08 — HTTP : Méthodes avancées, Idempotence et Codes de Statut (4 juillet 2026)

> **Durée estimée :** 30 minutes de lecture  
> **Prérequis :** Jour 07 (bases HTTP, requête/réponse)  
> **Objectif :** Maîtriser toutes les méthodes HTTP, comprendre l'idempotence et la sécurité, et connaître les familles de codes de statut

---

## 1. Rappel : Le modèle Requête/Réponse HTTP

Une transaction HTTP suit toujours ce schéma :

```
Client                          Serveur
  |                               |
  |  --- Requête HTTP ----------> |
  |      Méthode + URL + Headers  |
  |      (+ Body optionnel)       |
  |                               |
  |  <-- Réponse HTTP ----------- |
  |      Status Code + Headers    |
  |      + Body                   |
  |                               |
```

La **méthode HTTP** (aussi appelée **verbe HTTP**) indique l'**intention** du client : que veut-il faire avec la ressource ciblée ?

---

## 2. Les 9 méthodes HTTP officielles

### 2.1 GET — Récupérer une ressource

```
GET /articles/42 HTTP/1.1
Host: api.exemple.com
```

- Demande la **représentation** d'une ressource
- **Pas de body** dans la requête (techniquement autorisé mais ignoré)
- La réponse a un body (la ressource demandée)
- Exemple : charger une page web, récupérer un utilisateur

```python
import urllib.request

with urllib.request.urlopen("https://httpbin.org/get") as response:
    print(response.read().decode())
```

### 2.2 POST — Créer / Soumettre des données

```
POST /articles HTTP/1.1
Host: api.exemple.com
Content-Type: application/json

{"titre": "Mon article", "contenu": "..."}
```

- Envoie des données au serveur pour **traitement**
- Crée une nouvelle ressource (l'URL de la nouvelle ressource est dans `Location`
- Peut aussi déclencher un traitement (envoyer un email, lancer un calcul)
- **A un body** dans la requête

### 2.3 PUT — Remplacer une ressource entière

```
PUT /articles/42 HTTP/1.1
Host: api.exemple.com
Content-Type: application/json

{"titre": "Nouveau titre", "contenu": "Nouveau contenu complet"}
```

- **Remplace entièrement** la ressource à l'URL donnée
- Si la ressource n'existe pas, la crée
- Doit envoyer la **représentation complète** (tous les champs)
- Différence clé avec PATCH : PUT = remplacement total

### 2.4 PATCH — Modifier partiellement une ressource

```
PATCH /articles/42 HTTP/1.1
Host: api.exemple.com
Content-Type: application/json

{"titre": "Juste le titre changé"}
```

- Applique une **modification partielle**
- Seuls les champs envoyés sont mis à jour
- Plus économique que PUT quand on modifie 1 champ sur 20
- Attention : PATCH n'est **pas nécessairement idempotent** (voir section 3)

### 2.5 DELETE — Supprimer une ressource

```
DELETE /articles/42 HTTP/1.1
Host: api.exemple.com
```

- Supprime la ressource identifiée par l'URL
- Généralement pas de body dans la requête
- Réponse : `204 No Content` (supprimé) ou `200 OK` avec confirmation

### 2.6 HEAD — Récupérer les en-têtes seulement

```
HEAD /gros-fichier.zip HTTP/1.1
Host: telechargements.exemple.com
```

- **Identique à GET** mais la réponse n'a **pas de body**
- Seuls les headers sont renvoyés
- Utilité :
  - Vérifier si une ressource existe (sans télécharger son contenu)
  - Connaître la taille d'un fichier (`Content-Length`) avant de le télécharger
  - Vérifier la date de modification (`Last-Modified`)

```python
import urllib.request

req = urllib.request.Request("https://httpbin.org/get", method="HEAD")
with urllib.request.urlopen(req) as response:
    print(dict(response.headers))  # Headers sans body
```

### 2.7 OPTIONS — Découvrir les capacités d'un serveur

```
OPTIONS /articles HTTP/1.1
Host: api.exemple.com
```

Réponse typique :
```
HTTP/1.1 200 OK
Allow: GET, POST, HEAD, OPTIONS
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
```

- Demande quelles méthodes sont disponibles pour une ressource
- Crucial pour **CORS** (Cross-Origin Resource Sharing) — le navigateur envoie d'abord une requête OPTIONS (preflight) avant une vraie requête cross-origin
- Pas de body dans la requête

### 2.8 CONNECT — Établir un tunnel

```
CONNECT api.exemple.com:443 HTTP/1.1
Host: api.exemple.com:443
```

- Demande au proxy d'établir un **tunnel TCP** vers la destination
- Utilisé par les proxies HTTP pour tunneliser du HTTPS
- En pratique : votre navigateur utilise CONNECT pour passer par un proxy vers un site HTTPS
- Pas d'utilisation directe en backend applicatif

### 2.9 TRACE — Écho de la requête (diagnostic)

```
TRACE /debug HTTP/1.1
Host: exemple.com
```

- Le serveur renvoie dans sa réponse la requête qu'il a reçue (à des fins de débogage)
- **Désactivé sur presque tous les serveurs** pour des raisons de sécurité (attaque XST — Cross-Site Tracing)
- Vous ne l'utiliserez jamais en production

---

## 3. Idempotence et Sécurité — Concepts fondamentaux

Ces deux propriétés définissent comment une méthode se comporte si elle est appelée plusieurs fois.

### 3.1 Sécurité (Safe Methods)

> Une méthode est **sûre** si elle ne modifie pas l'état du serveur.

En d'autres termes : appeler la méthode ne doit avoir aucun effet de bord sur les données du serveur.

**Analogie :** Regarder un tableau dans un musée (GET) vs peindre par-dessus (POST/PUT).

### 3.2 Idempotence

> Une méthode est **idempotente** si l'appeler une fois ou N fois produit le **même résultat sur le serveur**.

**Attention :** L'idempotence parle de l'**état final du serveur**, pas de la réponse HTTP elle-même.

**Analogie :**
- Appuyer sur le bouton "lumière ON" 5 fois → la lumière est allumée (même résultat qu'une seule fois) = **idempotent**
- Appuyer sur "ajouter 1€ au panier" 5 fois → 5€ ajoutés (résultat différent) = **non idempotent**

### 3.3 Tableau récapitulatif

| Méthode  | Sûre ? | Idempotente ? | A un body ? | Usage principal         |
|----------|--------|---------------|-------------|-------------------------|
| GET      | Oui    | Oui           | Non         | Lire une ressource      |
| HEAD     | Oui    | Oui           | Non         | Lire les headers        |
| OPTIONS  | Oui    | Oui           | Non         | Découvrir les capacités |
| TRACE    | Oui    | Oui           | Non         | Diagnostic (désactivé)  |
| POST     | Non    | Non           | Oui         | Créer / Soumettre       |
| PUT      | Non    | Oui           | Oui         | Remplacer entièrement   |
| PATCH    | Non    | Non*          | Oui         | Modifier partiellement  |
| DELETE   | Non    | Oui           | Rare        | Supprimer               |
| CONNECT  | Non    | Non           | Non         | Tunnel proxy            |

*PATCH peut être idempotent selon l'implémentation (ex: `SET titre = "X"` est idempotent, `APPEND "X" au titre` ne l'est pas)

### 3.4 Pourquoi l'idempotence est-elle importante ?

En pratique, l'idempotence permet la **résilience réseau** :

```
Client envoie PUT /articles/42  →  [perte réseau]  → réponse jamais reçue
Client réessaie PUT /articles/42  →  OK, l'article a le même état qu'après le 1er appel
```

Avec POST (non idempotent) :
```
Client envoie POST /articles  →  [perte réseau]  → réponse jamais reçue
Client réessaie POST /articles  →  PROBLÈME : 2 articles créés !
```

C'est pourquoi les navigateurs vous demandent "Voulez-vous renvoyer les données du formulaire ?" quand vous raffraîchissez après un POST.

---

## 4. Les codes de statut HTTP — Guide complet

Le code de statut est un **nombre à 3 chiffres** dans la réponse HTTP. Le premier chiffre indique la **famille** du code.

### 4.1 Famille 1xx — Informationnel (Réponses provisoires)

Le serveur a reçu la requête et continue le traitement.

| Code | Nom                | Description |
|------|--------------------|-------------|
| 100  | Continue           | Le serveur a reçu les headers de la requête, le client peut envoyer le body |
| 101  | Switching Protocols| Le serveur accepte de changer de protocole (ex: HTTP → WebSocket) |
| 102  | Processing         | Le serveur traite la requête (WebDAV, longues opérations) |

**Exemple pratique — 101 Switching Protocols :**
```
Client: GET /chat HTTP/1.1
        Upgrade: websocket
        Connection: Upgrade
        
Serveur: HTTP/1.1 101 Switching Protocols
         Upgrade: websocket
         Connection: Upgrade
```
Après ce 101, la connexion TCP devient un tunnel WebSocket.

### 4.2 Famille 2xx — Succès

La requête a été reçue, comprise et acceptée.

| Code | Nom                   | Description |
|------|-----------------------|-------------|
| 200  | OK                    | Succès standard pour GET, PUT, PATCH |
| 201  | Created               | Ressource créée (POST réussi) — inclure `Location` header |
| 202  | Accepted              | Requête acceptée mais traitement asynchrone (job en arrière-plan) |
| 204  | No Content            | Succès mais pas de body (DELETE réussi, PUT sans retour) |
| 206  | Partial Content       | Réponse partielle (téléchargement en morceaux, `Range` header) |

**Exemple — 201 Created :**
```
POST /api/users HTTP/1.1
Content-Type: application/json
{"nom": "Alice", "email": "alice@exemple.com"}

→ HTTP/1.1 201 Created
  Location: /api/users/456
  Content-Type: application/json
  {"id": 456, "nom": "Alice", "email": "alice@exemple.com"}
```

**Exemple — 202 Accepted (traitement asynchrone) :**
```
POST /api/rapports/generer HTTP/1.1
{"periode": "2026-Q1"}

→ HTTP/1.1 202 Accepted
  {"job_id": "abc123", "status_url": "/api/jobs/abc123"}
```

**Exemple — 204 No Content :**
```
DELETE /api/users/456 HTTP/1.1

→ HTTP/1.1 204 No Content
  (pas de body)
```

### 4.3 Famille 3xx — Redirection

Le client doit effectuer une action supplémentaire pour compléter la requête.

| Code | Nom                | Description |
|------|--------------------|-------------|
| 301  | Moved Permanently  | Redirection permanente — mettre à jour les bookmarks |
| 302  | Found              | Redirection temporaire — ne pas mettre à jour les bookmarks |
| 303  | See Other          | Rediriger vers une autre URL avec GET (après un POST) |
| 304  | Not Modified       | La ressource n'a pas changé — utiliser le cache |
| 307  | Temporary Redirect | Redirection temporaire en gardant la méthode originale |
| 308  | Permanent Redirect | Redirection permanente en gardant la méthode originale |

**301 vs 302 vs 307 vs 308 — le tableau des différences :**

| Code | Permanent ? | Méthode préservée ? |
|------|-------------|---------------------|
| 301  | Oui         | Non (POST→GET)      |
| 302  | Non         | Non (POST→GET)      |
| 307  | Non         | Oui (POST reste POST)|
| 308  | Oui         | Oui (POST reste POST)|

**Pattern Post/Redirect/Get avec 303 :**
```
1. Client: POST /formulaire (soumet un formulaire)
2. Serveur: 303 See Other → Location: /merci
3. Client: GET /merci
4. Serveur: 200 OK (page de confirmation)
```
Ce pattern évite la double soumission si l'utilisateur rafraîchit la page.

**304 Not Modified — le cache en action :**
```
Client: GET /logo.png HTTP/1.1
        If-None-Match: "etag-abc123"
        
Serveur: HTTP/1.1 304 Not Modified
         (pas de body — le client utilise sa copie en cache)
```

### 4.4 Famille 4xx — Erreurs client

Le client a fait quelque chose de mal.

| Code | Nom                   | Description |
|------|-----------------------|-------------|
| 400  | Bad Request           | Requête malformée, JSON invalide, paramètre manquant |
| 401  | Unauthorized          | Non authentifié (malgré le nom, c'est bien un problème d'auth) |
| 403  | Forbidden             | Authentifié mais pas autorisé |
| 404  | Not Found             | Ressource inexistante |
| 405  | Method Not Allowed    | Méthode non supportée pour cette URL |
| 406  | Not Acceptable        | Serveur ne peut pas produire le format demandé (Accept header) |
| 408  | Request Timeout       | Le client a mis trop de temps à envoyer la requête |
| 409  | Conflict              | Conflit avec l'état actuel (ex: username déjà pris) |
| 410  | Gone                  | Ressource définitivement supprimée (plus fort que 404) |
| 413  | Payload Too Large     | Body trop grand |
| 415  | Unsupported Media Type| Content-Type non supporté par le serveur |
| 422  | Unprocessable Entity  | Syntaxe OK mais sémantique incorrecte (validation échouée) |
| 429  | Too Many Requests     | Rate limiting — trop de requêtes |

**401 vs 403 — la distinction importante :**

```
401 Unauthorized = "Qui êtes-vous ?"
→ Vous n'êtes pas connecté (pas de token, token expiré)
→ La réponse inclut WWW-Authenticate pour indiquer comment s'authentifier

403 Forbidden = "Je vous connais, mais non."
→ Vous êtes connecté, mais vous n'avez pas les droits
→ Ex: un utilisateur normal qui essaie d'accéder à l'admin
```

**422 vs 400 — la nuance :**
```
400 Bad Request = JSON invalide, paramètre manquant, requête incompréhensible
422 Unprocessable Entity = La requête est bien formée, mais les données ne sont pas valides
    Ex: {"age": -5, "email": "pas-un-email"}
    → JSON valide, mais les valeurs sont sémantiquement incorrectes
```

**Exemple de réponse 429 avec Retry-After :**
```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1751670000

{"erreur": "Trop de requêtes. Réessayez dans 60 secondes."}
```

### 4.5 Famille 5xx — Erreurs serveur

Le serveur a échoué à traiter une requête valide.

| Code | Nom                      | Description |
|------|--------------------------|-------------|
| 500  | Internal Server Error    | Erreur générique côté serveur (bug, exception non gérée) |
| 501  | Not Implemented          | La méthode n'est pas implémentée par le serveur |
| 502  | Bad Gateway              | Le proxy/gateway a reçu une réponse invalide du serveur upstream |
| 503  | Service Unavailable      | Serveur temporairement indisponible (maintenance, surcharge) |
| 504  | Gateway Timeout          | Le proxy n'a pas reçu de réponse à temps du serveur upstream |
| 507  | Insufficient Storage     | Serveur ne peut pas stocker la représentation (WebDAV) |

**502 vs 504 — en contexte de microservices :**
```
Navigateur → Nginx (reverse proxy) → API Django

502 Bad Gateway :
  Nginx a contacté Django mais Django a renvoyé une réponse invalide
  (processus Django crashé, réponse tronquée)

504 Gateway Timeout :
  Nginx a contacté Django mais Django n'a pas répondu dans les délais
  (requête trop lente, deadlock en base de données)
```

**503 avec Retry-After :**
```
HTTP/1.1 503 Service Unavailable
Retry-After: 120
Content-Type: application/json

{"message": "Maintenance en cours jusqu'à 22h00"}
```

---

## 5. Exemples Python — Utiliser les méthodes HTTP

### 5.1 Avec `urllib.request` (bibliothèque standard)

```python
import urllib.request
import urllib.parse
import json

BASE_URL = "https://httpbin.org"

# GET
def faire_get(chemin):
    url = BASE_URL + chemin
    with urllib.request.urlopen(url) as reponse:
        return json.loads(reponse.read().decode())

# POST avec données JSON
def faire_post(chemin, donnees):
    url = BASE_URL + chemin
    body = json.dumps(donnees).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as reponse:
        return json.loads(reponse.read().decode())

# PUT
def faire_put(chemin, donnees):
    url = BASE_URL + chemin
    body = json.dumps(donnees).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="PUT",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as reponse:
        return json.loads(reponse.read().decode())

# DELETE
def faire_delete(chemin):
    url = BASE_URL + chemin
    req = urllib.request.Request(url, method="DELETE")
    with urllib.request.urlopen(req) as reponse:
        return json.loads(reponse.read().decode())

# HEAD — récupérer le code de statut et les headers sans body
def faire_head(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req) as reponse:
        return dict(reponse.headers), reponse.status
```

### 5.2 Vérifier l'idempotence de PUT

```python
import urllib.request
import json

def tester_idempotence_put():
    """
    PUT est idempotent : appeler PUT /anything 2 fois avec les mêmes données
    doit produire le même résultat côté serveur.
    """
    url = "https://httpbin.org/put"
    donnees = {"nom": "Alice", "age": 30}
    
    resultats = []
    for i in range(3):
        body = json.dumps(donnees).encode()
        req = urllib.request.Request(
            url, data=body, method="PUT",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            rep = json.loads(r.read().decode())
            # httpbin.org/put renvoie les données qu'on lui a envoyées
            resultats.append(rep["json"])
    
    # Tous les résultats doivent être identiques
    print(f"Appel 1: {resultats[0]}")
    print(f"Appel 2: {resultats[1]}")
    print(f"Appel 3: {resultats[2]}")
    print(f"Idempotent: {resultats[0] == resultats[1] == resultats[2]}")

tester_idempotence_put()
```

### 5.3 Récupérer le code de statut

```python
import urllib.request
import urllib.error

def verifier_code_statut(url):
    try:
        with urllib.request.urlopen(url) as reponse:
            print(f"Code: {reponse.status} - {reponse.reason}")
            return reponse.status
    except urllib.error.HTTPError as e:
        # Les erreurs 4xx et 5xx lèvent HTTPError
        print(f"Erreur HTTP: {e.code} - {e.reason}")
        return e.code

# httpbin.org permet de forcer n'importe quel code de statut
verifier_code_statut("https://httpbin.org/status/200")  # 200 OK
verifier_code_statut("https://httpbin.org/status/201")  # 201 Created
verifier_code_statut("https://httpbin.org/status/404")  # 404 Not Found
verifier_code_statut("https://httpbin.org/status/500")  # 500 Internal Server Error
```

### 5.4 Un mini-serveur HTTP qui répond avec différents codes

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class MonHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path == "/ok":
            self.envoyer_reponse(200, {"message": "Tout va bien"})
        elif self.path == "/cree":
            self.send_response(201)
            self.send_header("Location", "/ressources/42")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": 42}).encode())
        elif self.path == "/interdit":
            self.envoyer_reponse(403, {"erreur": "Accès refusé"})
        elif self.path == "/introuvable":
            self.envoyer_reponse(404, {"erreur": "Ressource non trouvée"})
        else:
            self.envoyer_reponse(200, {"chemin": self.path})
    
    def do_POST(self):
        longueur = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(longueur)
        try:
            donnees = json.loads(body)
            self.envoyer_reponse(201, {"cree": donnees, "id": 99})
        except json.JSONDecodeError:
            self.envoyer_reponse(400, {"erreur": "JSON invalide"})
    
    def do_DELETE(self):
        # 204 No Content — suppression réussie sans body
        self.send_response(204)
        self.end_headers()
    
    def envoyer_reponse(self, code, donnees):
        body = json.dumps(donnees).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    
    def log_message(self, format, *args):
        pass  # Silencieux pour l'exemple

if __name__ == "__main__":
    server = HTTPServer(("localhost", 8080), MonHandler)
    print("Serveur sur http://localhost:8080")
    server.serve_forever()
```

---

## 6. Anti-patterns courants à éviter

### 6.1 Utiliser GET pour modifier des données

```python
# MAUVAIS — GET ne doit pas avoir d'effets de bord
GET /supprimer-utilisateur?id=42

# CORRECT
DELETE /utilisateurs/42
```

### 6.2 Toujours retourner 200 même en cas d'erreur

```python
# MAUVAIS — beaucoup d'anciennes APIs font ça
HTTP/1.1 200 OK
{"succes": false, "erreur": "Utilisateur non trouvé"}

# CORRECT
HTTP/1.1 404 Not Found
{"erreur": "Utilisateur non trouvé"}
```

### 6.3 Utiliser 403 au lieu de 401

```python
# MAUVAIS — l'utilisateur n'est pas du tout connecté
HTTP/1.1 403 Forbidden

# CORRECT — l'utilisateur n'est pas authentifié
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="API"
```

### 6.4 Retourner 200 après un DELETE

```python
# ACCEPTABLE mais sous-optimal
HTTP/1.1 200 OK
{"message": "Supprimé"}

# PRÉFÉRÉ — pas de body nécessaire
HTTP/1.1 204 No Content
```

---

## 7. Résumé visuel

```
Méthode     Safe?   Idempotent?   Typique en REST API
─────────────────────────────────────────────────────
GET         ✓       ✓             Lire une ressource
POST        ✗       ✗             Créer une ressource
PUT         ✗       ✓             Remplacer une ressource
PATCH       ✗       ✗ (souvent)   Modifier partiellement
DELETE      ✗       ✓             Supprimer une ressource
HEAD        ✓       ✓             Vérifier existence/headers
OPTIONS     ✓       ✓             CORS preflight

Codes clés:
200 OK         → Succès standard
201 Created    → POST réussi (+ header Location)
204 No Content → DELETE réussi (pas de body)
301/302        → Redirections (permanent/temporaire)
304 Not Mod.   → Cache valide
400 Bad Req    → Requête malformée
401 Unauth     → Non connecté
403 Forbidden  → Connecté mais pas autorisé
404 Not Found  → Ressource inexistante
409 Conflict   → Conflit d'état
422 Unprocess. → Validation échouée
429 Too Many   → Rate limit
500 Int. Error → Bug serveur
503 Unavail.   → Serveur en maintenance
```

---

## 8. Points clés à retenir

1. **Les méthodes HTTP expriment une intention** — elles permettent aux serveurs et proxies de prendre des décisions intelligentes
2. **Safe = pas d'effets de bord** (GET, HEAD, OPTIONS) — les navigateurs peuvent les appeler librement
3. **Idempotent = même résultat après N appels** (GET, PUT, DELETE) — résistant aux réessais réseau
4. **1xx/2xx/3xx = succès ou info** — le client peut continuer
5. **4xx = faute du client** — inutile de réessayer sans modifier la requête
6. **5xx = faute du serveur** — peut être transitoire, le client peut réessayer après délai
7. **401 = non identifié, 403 = identifié mais interdit** — distinction fondamentale

---

*Prochain cours (Jour 09) : Les headers HTTP en profondeur — Content-Type, Authorization, CORS, Cookie*
