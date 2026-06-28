# Jour 01 — DNS et le voyage d'une requête
📅 27 juin 2026 · Module : Comment le web fonctionne

---

## Ce que tu vas comprendre aujourd'hui

Quand tu tapes `https://google.com` et appuies sur Entrée, il se passe 8 étapes avant que tu voies quoi que ce soit. Aujourd'hui tu vas les comprendre une par une.

---

## Étape 1 — Le navigateur analyse l'URL

L'URL `https://google.com/search?q=python` se décompose ainsi :

```
https       ://    google.com    /search      ?q=python
  │                    │            │              │
protocole           domaine       chemin      paramètres
(HTTP sécurisé)
```

Le navigateur sait qu'il doit :
- Utiliser HTTPS (port 443 par défaut)
- Contacter la machine `google.com`
- Lui demander la ressource `/search?q=python`

**Mais il ne sait pas encore où est `google.com` sur internet.**

---

## Étape 2 — DNS : traduire un nom en adresse IP

Le DNS (Domain Name System) est l'annuaire téléphonique d'internet. Il traduit `google.com` en `142.250.74.46` (une adresse IP).

**Comment ça marche :**

```
Navigateur
    │
    ├─→ Cache local ? "Est-ce que j'ai déjà cherché google.com ?"
    │       └─→ Oui → utilise l'IP en cache
    │
    ├─→ Non → demande au résolveur DNS (souvent ton routeur ou 8.8.8.8)
    │
    └─→ Le résolveur remonte la chaîne :
            . (root)  →  .com  →  google.com  →  IP : 142.250.74.46
```

**Les acteurs DNS :**
- **Résolveur** : ton FAI ou Google (8.8.8.8) — fait le travail pour toi
- **Root servers** : savent où sont les serveurs `.com`, `.fr`, etc.
- **TLD servers** : savent où est le serveur DNS de `google.com`
- **Authoritative server** : le serveur de Google qui connaît l'IP finale

**TTL (Time To Live)** : chaque réponse DNS a une durée de vie. Après, il faut redemander.

---

## Étape 3 — TCP : établir la connexion

Une fois l'IP connue (`142.250.74.46`), le navigateur ouvre une connexion TCP.

TCP (Transmission Control Protocol) est un protocole **fiable** : il garantit que les paquets arrivent dans l'ordre et sans perte.

**Le three-way handshake TCP :**

```
Navigateur                          Serveur
    │                                  │
    │──── SYN ──────────────────────→  │   "Je veux me connecter"
    │                                  │
    │  ←──────────────────── SYN-ACK ──│   "OK, j'entends"
    │                                  │
    │──── ACK ──────────────────────→  │   "Confirmé, on est connectés"
    │                                  │
    │         [Connexion établie]       │
```

- **SYN** = SYNchronize
- **ACK** = ACKnowledge

Après ce handshake, les deux machines peuvent s'envoyer des données. Pour HTTPS, il y a aussi un handshake TLS supplémentaire (chiffrement).

---

## Étape 4 — HTTP : la vraie requête

Maintenant que la connexion est ouverte, le navigateur envoie une **requête HTTP** :

```
GET /search?q=python HTTP/1.1
Host: google.com
User-Agent: Mozilla/5.0 ...
Accept: text/html
Accept-Language: fr-FR

```

Et le serveur répond :

```
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 48293

<!DOCTYPE html>
<html>...
```

---

## Schéma complet

```
[Toi]  →  DNS lookup  →  TCP handshake  →  HTTP Request  →  [Serveur]
                                                                  │
[Toi]  ←  HTML/CSS/JS  ←  HTTP Response  ←─────────────────────┘
  │
  └→ [Navigateur parse le HTML, télécharge CSS/JS/images (nouvelles requêtes)]
```

---

## À retenir

| Concept | Rôle |
|---------|------|
| DNS | Traduit le nom de domaine en IP |
| TCP | Connexion fiable (handshake avant d'envoyer) |
| HTTP | Le protocole de la requête/réponse |
| IP | L'adresse de la machine sur internet |
| Port | Le "guichet" sur la machine (80=HTTP, 443=HTTPS) |
