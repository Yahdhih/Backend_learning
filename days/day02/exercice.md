# Exercice Jour 02 — HTTP avec curl

`curl` fait des requêtes HTTP en ligne de commande. C'est l'outil de debug numéro 1 pour les APIs.

---

## Partie 1 — Voir une requête/réponse complète

```bash
# -v = verbose : montre tout (headers envoyés ET reçus)
curl -v https://httpbin.org/get
```

Repère dans la sortie :
- Les lignes `>` = ce que curl envoie
- Les lignes `<` = ce que le serveur répond
- La ligne vide qui sépare headers et body

**Question :** Quel header indique le format du body reçu ?

---

## Partie 2 — Les méthodes HTTP

```bash
# GET (défaut)
curl https://httpbin.org/get

# POST avec un body JSON
curl -X POST https://httpbin.org/post \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "age": 30}'

# PUT
curl -X PUT https://httpbin.org/put \
  -H "Content-Type: application/json" \
  -d '{"name": "Bob"}'

# DELETE
curl -X DELETE https://httpbin.org/delete

# PATCH
curl -X PATCH https://httpbin.org/patch \
  -d '{"status": "active"}'
```

**Question :** Dans la réponse de httpbin, que contient le champ `json` ?

---

## Partie 3 — Les codes de statut

```bash
# 200 OK
curl -s -o /dev/null -w "%{http_code}" https://httpbin.org/status/200

# 404 Not Found
curl -s -o /dev/null -w "%{http_code}" https://httpbin.org/status/404

# 500 Server Error
curl -s -o /dev/null -w "%{http_code}" https://httpbin.org/status/500

# Observer une redirection (301)
curl -v http://github.com
```

**Question :** Que fait curl face à une redirection ? Suit-il automatiquement ?
(Indice : essaie avec `-L` pour voir la différence)

---

## Partie 4 — Headers personnalisés

```bash
# Envoyer des headers custom
curl https://httpbin.org/headers \
  -H "X-Mon-Header: valeur-test" \
  -H "Accept: application/json"
```

**Question :** Dans la réponse, où vois-tu le header que tu as envoyé ?

---

## Partie 5 — Réflexion dans `notes.md`

Réponds dans tes propres mots :

1. Quelle est la différence entre `401 Unauthorized` et `403 Forbidden` ?
2. Pourquoi dit-on qu'HTTP est "stateless" ?
3. À quoi sert le header `Content-Type` et pourquoi est-il important ?
