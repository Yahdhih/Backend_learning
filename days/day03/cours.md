# Jour 03 — Les sockets : HTTP à la main
📅 29 juin 2026 · Module : Comment le web fonctionne

---

## Qu'est-ce qu'un socket ?

Un socket est une **prise réseau** dans ton programme. C'est l'objet que ton OS te donne pour envoyer et recevoir des bytes sur le réseau.

Analogie : un socket, c'est comme un téléphone.
- Tu l'ouvres (créer le socket)
- Tu composes un numéro (te connecter à une IP:port)
- Vous parlez (envoyer/recevoir des bytes)
- Tu raccroches (fermer le socket)

---

## Les types de sockets

```
socket.AF_INET      → IPv4 (adresses comme 192.168.1.1)
socket.AF_INET6     → IPv6

socket.SOCK_STREAM  → TCP (connexion fiable, ordonnée)
socket.SOCK_DGRAM   → UDP (pas de connexion, plus rapide, peut perdre des paquets)
```

Pour le web, on utilise toujours `AF_INET + SOCK_STREAM` (TCP sur IPv4).

---

## Un serveur socket en Python, étape par étape

```python
import socket

# 1. Créer le socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. Éviter l'erreur "Address already in use" au restart
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 3. Associer le socket à une adresse et un port
server.bind(("127.0.0.1", 8888))

# 4. Commencer à écouter (5 = taille de la file d'attente)
server.listen(5)

# 5. Boucle d'attente
while True:
    # accept() bloque jusqu'à ce qu'un client se connecte
    client_socket, client_address = server.accept()
    # client_socket = nouveau socket dédié à CE client
    # server socket continue d'écouter les autres

    # 6. Lire les données du client
    data = client_socket.recv(4096)   # lire jusqu'à 4096 bytes

    # 7. Envoyer une réponse
    client_socket.sendall(b"Bonjour !\n")

    # 8. Fermer la connexion avec CE client
    client_socket.close()
```

**Pourquoi deux sockets ?**
- `server` : écoute sur le port, attend des connexions
- `client_socket` : connexion privée avec UN client spécifique

---

## Ce que HTTP ajoute par-dessus TCP

TCP transporte des bytes bruts. HTTP est juste une **convention sur le format** de ces bytes :

```
# Requête HTTP = texte envoyé via TCP
GET /hello HTTP/1.1\r\n
Host: localhost:8888\r\n
\r\n

# Réponse HTTP = texte envoyé via TCP
HTTP/1.1 200 OK\r\n
Content-Type: text/plain\r\n
Content-Length: 6\r\n
\r\n
Hello!
```

`\r\n` = CRLF (Carriage Return + Line Feed) — obligatoire dans HTTP.

---

## Parser une requête HTTP à la main

```python
def parse_request(raw_bytes):
    text = raw_bytes.decode("utf-8")

    # Séparer les headers du body
    headers_part, _, body = text.partition("\r\n\r\n")
    lines = headers_part.split("\r\n")

    # Première ligne : "GET /path HTTP/1.1"
    method, path, version = lines[0].split(" ")

    # Headers suivants : "Clé: valeur"
    headers = {}
    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key.lower()] = value

    return {"method": method, "path": path, "headers": headers, "body": body}
```

---

## Construire une réponse HTTP à la main

```python
def make_response(status_code, status_text, body, content_type="text/plain"):
    body_bytes = body.encode("utf-8")
    response = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
        f"{body}"
    )
    return response.encode("utf-8")
```

---

## Ce que Django fait à ta place

Tout ce que tu vas coder aujourd'hui, Django le fait pour toi invisiblement :
- Ouvrir et gérer le socket → Gunicorn
- Parser la requête HTTP → Django's `WSGIRequest`
- Router vers la bonne fonction → Django's `URLconf`
- Construire la réponse → Django's `HttpResponse`

Comprendre les sockets, c'est comprendre ce que cache l'abstraction.
