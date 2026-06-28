# Jour 02 — HTTP : le protocole du web
📅 28 juin 2026 · Module : Comment le web fonctionne

---

## HTTP en une phrase

HTTP (HyperText Transfer Protocol) est un protocole **texte** : une requête et une réponse sont juste du texte structuré envoyé via TCP.

---

## Structure d'une requête HTTP

```
GET /users/42 HTTP/1.1          ← ligne de requête : méthode + chemin + version
Host: api.exemple.com           ┐
Accept: application/json        │  headers : métadonnées
Authorization: Bearer abc123    ┘
                                ← ligne vide obligatoire (séparateur)
                                ← body (vide pour GET, présent pour POST/PUT)
```

**Chaque partie :**
- **Méthode** : ce que tu veux faire (GET, POST, PUT, DELETE…)
- **Chemin** : la ressource demandée (`/users/42`)
- **Version** : `HTTP/1.1` ou `HTTP/2`
- **Headers** : informations sur la requête
- **Body** : données envoyées (pour POST, PUT, PATCH)

---

## Les méthodes HTTP

| Méthode | Usage | Body ? | Idempotent ? |
|---------|-------|--------|--------------|
| GET | Lire une ressource | Non | Oui |
| POST | Créer une ressource | Oui | Non |
| PUT | Remplacer entièrement | Oui | Oui |
| PATCH | Modifier partiellement | Oui | Non |
| DELETE | Supprimer | Non | Oui |

**Idempotent** = faire la même action plusieurs fois donne le même résultat.
- `GET /users/1` 10 fois → toujours le même user ✓
- `POST /users` 10 fois → 10 users créés ✗

---

## Structure d'une réponse HTTP

```
HTTP/1.1 200 OK                 ← ligne de statut : version + code + message
Content-Type: application/json  ┐
Content-Length: 85              │  headers de réponse
Date: Fri, 27 Jun 2026 10:00   ┘
                                ← ligne vide
{"id": 42, "name": "Alice"}    ← body
```

---

## Les codes de statut

| Plage | Signification | Exemples |
|-------|--------------|---------|
| 2xx | Succès | 200 OK, 201 Created, 204 No Content |
| 3xx | Redirection | 301 Moved Permanently, 302 Found |
| 4xx | Erreur client | 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found |
| 5xx | Erreur serveur | 500 Internal Server Error, 503 Service Unavailable |

**À mémoriser absolument :**
- `200` OK
- `201` Créé (après POST)
- `400` Mauvaise requête (données invalides)
- `401` Non authentifié (tu n'es pas connecté)
- `403` Interdit (tu es connecté mais pas autorisé)
- `404` Introuvable
- `500` Le serveur a planté

---

## Les headers importants

**Requête :**
```
Content-Type: application/json     # format du body que j'envoie
Accept: application/json           # format que je veux recevoir
Authorization: Bearer <token>      # mon jeton d'authentification
User-Agent: curl/7.64              # qui fait la requête
```

**Réponse :**
```
Content-Type: application/json     # format du body de la réponse
Content-Length: 85                 # taille en bytes
Cache-Control: max-age=3600        # durée de mise en cache
Set-Cookie: session=abc123         # créer un cookie côté client
```

---

## HTTP est stateless (sans état)

Chaque requête est **indépendante**. Le serveur ne se souvient pas de la requête précédente.

```
Requête 1 : GET /users/1  → Serveur retourne Alice
Requête 2 : GET /users/1  → Serveur retourne Alice (il a "oublié" la requête 1)
```

C'est pour ça qu'on a besoin de cookies ou de tokens pour maintenir une session.

---

## HTTP/1.1 vs HTTP/2 vs HTTP/3

| Version | Innovation principale |
|---------|----------------------|
| HTTP/1.0 | Une connexion TCP par requête |
| HTTP/1.1 | Connexions persistantes (keep-alive) |
| HTTP/2 | Multiplexage (plusieurs requêtes en parallèle sur une connexion) |
| HTTP/3 | UDP au lieu de TCP (plus rapide, moins de latence) |
