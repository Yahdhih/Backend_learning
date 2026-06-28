# Jour 09 — Exercice : Headers HTTP avec curl
📅 5 juillet 2026 · Module : HTTP en profondeur

> Prérequis : avoir `curl` installé (`curl --version`). Toutes les commandes utilisent `httpbin.org`, un service en ligne conçu pour tester des requêtes HTTP.

---

## Partie 1 — Content-Type et Accept

### 1.1 Observer le Content-Type d'une réponse JSON

```bash
curl -i https://httpbin.org/json
```

**Observez** la ligne `Content-Type` dans les headers de réponse. Elle devrait être `application/json`.

L'option `-i` affiche les headers de réponse en plus du body.

### 1.2 Envoyer du JSON dans une requête POST

```bash
curl -X POST https://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"nom": "Alice", "age": 30}' \
  -s | python3 -m json.tool
```

Dans la réponse de httpbin, cherchez la clé `"json"` — c'est ce que le serveur a reçu et parsé. Cherchez aussi `"headers"` → `"Content-Type"`.

### 1.3 Comparer JSON vs formulaire

```bash
# Avec JSON
curl -X POST https://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"prenom": "Bob"}' \
  -s | python3 -c "import json,sys; d=json.load(sys.stdin); print('json:', d['json']); print('form:', d['form'])"

# Avec formulaire URL-encodé
curl -X POST https://httpbin.org/post \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "prenom=Bob" \
  -s | python3 -c "import json,sys; d=json.load(sys.stdin); print('json:', d['json']); print('form:', d['form'])"
```

**Questions :**
- Dans quel cas `"json"` est-il rempli ? Dans quel cas `"form"` est-il rempli ?
- Que se passerait-il si vous envoyez du JSON mais avec `Content-Type: text/plain` ?

### 1.4 Négociation de contenu avec Accept

```bash
# Demander du JSON
curl https://httpbin.org/get \
  -H "Accept: application/json" \
  -s -o /dev/null -w "Content-Type reçu: %{content_type}\n"
```

---

## Partie 2 — Authorization

### 2.1 Basic Auth

```bash
# curl gère Basic Auth nativement avec -u user:password
curl -u alice:secret123 https://httpbin.org/basic-auth/alice/secret123 -v 2>&1 | head -30
```

Repérez dans la sortie la ligne `Authorization: Basic ...`. Décodez la valeur base64 :

```bash
echo "YWxpY2U6c2VjcmV0MTIz" | base64 --decode
```

Résultat attendu : `alice:secret123`

```bash
# Avec mauvais mot de passe → 401
curl -u alice:mauvais_mdp https://httpbin.org/basic-auth/alice/secret123 -i
```

**Questions :**
- Quel code HTTP obtenez-vous avec un mauvais mot de passe ?
- Quel header le serveur envoie-t-il pour indiquer la méthode d'auth ?

### 2.2 Bearer Token

```bash
curl https://httpbin.org/bearer \
  -H "Authorization: Bearer mon_token_fictif_abc123" \
  -i
```

```bash
# Sans Authorization → 401
curl https://httpbin.org/bearer -i
```

### 2.3 Encoder des credentials Basic Auth manuellement

```bash
# Encoder en base64
echo -n "user:password" | base64

# Utiliser le résultat dans un header
curl https://httpbin.org/basic-auth/user/password \
  -H "Authorization: Basic dXNlcjpwYXNzd29yZA==" \
  -i
```

---

## Partie 3 — CORS

### 3.1 Requête avec header Origin

```bash
curl https://httpbin.org/get \
  -H "Origin: https://monapp.com" \
  -v 2>&1 | grep -i "access-control"
```

Repérez les headers `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, etc.

### 3.2 Simuler un preflight CORS (requête OPTIONS)

```bash
curl -X OPTIONS https://httpbin.org/put \
  -H "Origin: https://monapp.com" \
  -H "Access-Control-Request-Method: PUT" \
  -H "Access-Control-Request-Headers: Authorization, Content-Type" \
  -v 2>&1 | grep -iE "(access-control|< HTTP)"
```

**Questions :**
- Quel code HTTP répond le serveur au preflight ?
- Quelles méthodes sont autorisées selon `Access-Control-Allow-Methods` ?
- Combien de temps le navigateur peut-il mettre en cache cette réponse preflight ?

### 3.3 Sans header Origin — pas de CORS

```bash
curl https://httpbin.org/get -v 2>&1 | grep -i "access-control"
```

**Question :** Y a-t-il des headers CORS dans la réponse si aucun `Origin` n'est envoyé ?

---

## Partie 4 — Cookies

### 4.1 Observer un Set-Cookie

```bash
# httpbin définit un cookie via redirection
curl -v "https://httpbin.org/cookies/set?session=abc123&lang=fr" 2>&1 | grep -i "set-cookie\|location"
```

### 4.2 Envoyer un cookie

```bash
curl https://httpbin.org/cookies \
  -H "Cookie: session=abc123; user=alice; theme=dark" \
  -s | python3 -m json.tool
```

**Questions :**
- Quels cookies le serveur a-t-il reçus ?
- Comment sont-ils séparés dans le header `Cookie` ?

### 4.3 Analyser les attributs d'un Set-Cookie

Voici un exemple de header `Set-Cookie` typique :
```
Set-Cookie: session_id=xyz789; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=3600
```

**Questions :**
- Que signifie `HttpOnly` ? Quel type d'attaque cela prévient-il ?
- Pourquoi mettre `Secure` ?
- Quelle est la différence entre `SameSite=Strict` et `SameSite=Lax` ?
- Quand le cookie expire-t-il si `Max-Age=3600` ?

---

## Partie 5 — Cache-Control et ETag

### 5.1 Observer Cache-Control

```bash
curl -I https://httpbin.org/cache/60
```

L'option `-I` fait une requête HEAD (headers seulement, pas de body).

**Questions :**
- Quelle est la valeur de `Cache-Control` ?
- Que signifie `max-age=60` ?

### 5.2 ETag et requête conditionnelle

```bash
# Première requête : récupérer l'ETag
curl -I https://httpbin.org/etag/test123
```

Notez la valeur du header `ETag`. Ensuite :

```bash
# Requête conditionnelle avec If-None-Match
curl -I https://httpbin.org/etag/test123 \
  -H 'If-None-Match: "test123"'
```

**Questions :**
- Quel code HTTP obtenez-vous ? Pourquoi ?
- Y a-t-il un body dans la réponse 304 ?
- Quelle économie de bande passante cela représente-t-il ?

```bash
# Avec un ETag différent → 200
curl -I https://httpbin.org/etag/test123 \
  -H 'If-None-Match: "mauvais_etag"'
```

---

## Partie 6 — Inspecter tous les headers avec -v

### 6.1 Voir la requête ET la réponse complètes

```bash
curl -v https://httpbin.org/get \
  -H "Accept: application/json" \
  -H "User-Agent: Backend-Learning/1.0" \
  2>&1 | head -50
```

Dans la sortie de `-v` :
- Les lignes `>` sont les headers de **requête** (envoyés par curl)
- Les lignes `<` sont les headers de **réponse** (reçus du serveur)
- Les lignes `*` sont des informations de connexion (TLS, DNS...)

### 6.2 Afficher uniquement certains headers de réponse

```bash
# Afficher tous les headers de réponse de httpbin.org
curl -sI https://httpbin.org/get | sort
```

---

## Questions de synthèse

1. Quelle est la différence entre `Content-Type` (dans une requête) et `Accept` ? Quand utilise-t-on chacun ?

2. Vous avez un token JWT. Comment construisez-vous le header `Authorization` correspondant ?

3. Un développeur frontend vous dit : "Je reçois une erreur CORS quand j'appelle votre API depuis `localhost:3000`". Quel header votre serveur doit-il ajouter à ses réponses pour régler le problème ?

4. Vous créez un cookie de session. Quels attributs devez-vous obligatoirement ajouter en production et pourquoi ?

5. Quelle est la différence entre `Cache-Control: no-cache` et `Cache-Control: no-store` ?

6. Pourquoi une réponse `304 Not Modified` n'a-t-elle pas de body ?

7. Un client vous envoie `Accept: text/html, application/json;q=0.5`. Vous pouvez répondre en JSON ou en HTML. Que devez-vous retourner selon les préférences du client ?
